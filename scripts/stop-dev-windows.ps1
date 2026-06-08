param(
    [Parameter(Mandatory = $true)]
    [string]$Root,

    [Parameter(Mandatory = $true)]
    [ValidateSet("all", "backend", "frontend")]
    [string]$Target
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function ConvertTo-MatchPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $trimChars = [char[]]@([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd($trimChars).ToLowerInvariant().Replace("/", "\")
}

function ConvertTo-MatchText {
    param(
        [string]$Text
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }

    return $Text.ToLowerInvariant().Replace("/", "\")
}

function Get-ChildProcessIds {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ParentId
    )

    @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentId" -ErrorAction SilentlyContinue |
        ForEach-Object { [int]$_.ProcessId })
}

function Stop-ProcessTree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,

        [Parameter(Mandatory = $true)]
        [hashtable]$Visited
    )

    if ($ProcessId -eq $PID -or $Visited.ContainsKey($ProcessId)) {
        return
    }

    $Visited[$ProcessId] = $true

    foreach ($childId in Get-ChildProcessIds -ParentId $ProcessId) {
        Stop-ProcessTree -ProcessId $childId -Visited $Visited
    }

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Read-PidFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    if (!(Test-Path $Path)) {
        return $null
    }

    try {
        $raw = (Get-Content -LiteralPath $Path -Raw -ErrorAction Stop).Trim()
        if ($raw.Length -eq 0) {
            return $null
        }

        try {
            $data = $raw | ConvertFrom-Json -ErrorAction Stop
            if ($data.name -and $data.name -ne $ServiceName) {
                return $null
            }
            if ($data.root -and (ConvertTo-MatchPath -Path $data.root) -ne $script:rootMatch) {
                return $null
            }
            if ($data.pid) {
                return [int]$data.pid
            }
        }
        catch {
            return [int]$raw
        }
    }
    catch {
        return $null
    }

    return $null
}

function Get-CimProcessById {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId
    )

    Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
}

function Test-ServiceProcess {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Process,

        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    $commandLine = ConvertTo-MatchText -Text $Process.CommandLine
    if ($commandLine.Length -eq 0) {
        return $false
    }

    if ($commandLine.Contains($script:rootMatch) -and $commandLine.Contains("run-$ServiceName.")) {
        return $true
    }

    if ($ServiceName -eq "backend") {
        return $commandLine.Contains($script:rootMatch) -and (
            $commandLine.Contains("uv run python run.py") -or
            $commandLine.Contains("python run.py") -or
            $commandLine.Contains("\python.exe run.py") -or
            $commandLine.Contains("run.py")
        )
    }

    $webMatch = "$($script:rootMatch)\web"
    return $commandLine.Contains($webMatch) -and (
        $commandLine.Contains("pnpm dev") -or
        $commandLine.Contains("\vite\") -or
        $commandLine.Contains("vite.js") -or
        $commandLine.Contains("vite ")
    )
}

function Test-DevLockerProcess {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Process,

        [Parameter(Mandatory = $true)]
        [string]$ServiceName
    )

    $commandLine = ConvertTo-MatchText -Text $Process.CommandLine
    if ($commandLine.Contains("stop-dev-windows.ps1") -or $commandLine.Contains("run-dev-windows.ps1")) {
        return $false
    }

    if (Test-ServiceProcess -Process $Process -ServiceName $ServiceName) {
        return $true
    }

    $processName = [System.IO.Path]::GetFileNameWithoutExtension([string]$Process.Name).ToLowerInvariant()
    return $processName -in @("cmd", "uv", "python", "pythonw", "node", "pnpm")
}

function Register-RestartManagerType {
    if (([System.Management.Automation.PSTypeName]"FastSoyAdminRestartManager").Type) {
        return
    }

    Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;

public static class FastSoyAdminRestartManager
{
    private const int ErrorMoreData = 234;

    [StructLayout(LayoutKind.Sequential)]
    private struct RmUniqueProcess
    {
        public int ProcessId;
        public long ProcessStartTime;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct RmProcessInfo
    {
        public RmUniqueProcess Process;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
        public string AppName;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
        public string ServiceShortName;

        public int ApplicationType;
        public uint AppStatus;
        public uint TSSessionId;

        [MarshalAs(UnmanagedType.Bool)]
        public bool Restartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    private static extern int RmStartSession(out uint sessionHandle, int sessionFlags, string sessionKey);

    [DllImport("rstrtmgr.dll")]
    private static extern int RmEndSession(uint sessionHandle);

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    private static extern int RmRegisterResources(
        uint sessionHandle,
        uint fileCount,
        string[] fileNames,
        uint applicationCount,
        IntPtr applications,
        uint serviceCount,
        string[] serviceNames);

    [DllImport("rstrtmgr.dll")]
    private static extern int RmGetList(
        uint sessionHandle,
        out uint processInfoNeeded,
        ref uint processInfoCount,
        [In, Out] RmProcessInfo[] affectedApps,
        ref uint rebootReasons);

    public static int[] GetLockingProcessIds(string[] paths)
    {
        if (paths == null || paths.Length == 0)
        {
            return Array.Empty<int>();
        }

        uint sessionHandle;
        var result = RmStartSession(out sessionHandle, 0, Guid.NewGuid().ToString("N"));
        if (result != 0)
        {
            return Array.Empty<int>();
        }

        try
        {
            result = RmRegisterResources(sessionHandle, (uint)paths.Length, paths, 0, IntPtr.Zero, 0, null);
            if (result != 0)
            {
                return Array.Empty<int>();
            }

            uint processInfoNeeded = 0;
            uint processInfoCount = 0;
            uint rebootReasons = 0;
            result = RmGetList(sessionHandle, out processInfoNeeded, ref processInfoCount, null, ref rebootReasons);

            if (result != ErrorMoreData || processInfoNeeded == 0)
            {
                return Array.Empty<int>();
            }

            var affectedApps = new RmProcessInfo[processInfoNeeded];
            processInfoCount = processInfoNeeded;
            result = RmGetList(sessionHandle, out processInfoNeeded, ref processInfoCount, affectedApps, ref rebootReasons);

            if (result != 0)
            {
                return Array.Empty<int>();
            }

            return affectedApps
                .Take((int)processInfoCount)
                .Select(app => app.Process.ProcessId)
                .Where(pid => pid > 0)
                .Distinct()
                .ToArray();
        }
        finally
        {
            RmEndSession(sessionHandle);
        }
    }
}
"@
}

function Get-LockingProcessIds {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Paths
    )

    try {
        Register-RestartManagerType
        return [FastSoyAdminRestartManager]::GetLockingProcessIds($Paths)
    }
    catch {
        return @()
    }
}

function Add-Candidate {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,

        [Parameter(Mandatory = $true)]
        [string]$Reason
    )

    if ($ProcessId -le 0 -or $ProcessId -eq $PID) {
        return
    }

    $key = [string]$ProcessId
    if (!$script:candidates.ContainsKey($key)) {
        $script:candidates[$key] = [PSCustomObject]@{
            ProcessId = $ProcessId
            Reasons = [System.Collections.Generic.List[string]]::new()
        }
    }

    $script:candidates[$key].Reasons.Add($Reason)
}

function Test-FileUnlocked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (!(Test-Path $Path)) {
        return $true
    }

    $stream = $null
    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        return $true
    }
    catch [System.IO.IOException] {
        return $false
    }
    finally {
        if ($stream) {
            $stream.Dispose()
        }
    }
}

function Wait-LogsUnlocked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Paths
    )

    $deadline = (Get-Date).AddSeconds(5)
    do {
        $locked = @($Paths | Where-Object { !(Test-FileUnlocked -Path $_) })
        if ($locked.Count -eq 0) {
            return $true
        }

        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)

    return $false
}

$rootPath = [System.IO.Path]::GetFullPath($Root)
$script:rootMatch = ConvertTo-MatchPath -Path $rootPath
$logPath = Join-Path $rootPath "tmp"
$serviceNames = @()

if ($Target -eq "all") {
    $serviceNames = @("backend", "frontend")
}
else {
    $serviceNames = @($Target)
}

$script:candidates = @{}
$logFiles = @()
$pidFiles = @()

foreach ($serviceName in $serviceNames) {
    $pidPath = Join-Path $logPath "run-$serviceName.pid"
    $stdoutPath = Join-Path $logPath "run-$serviceName.out.log"
    $stderrPath = Join-Path $logPath "run-$serviceName.err.log"
    $pidFiles += $pidPath
    $logFiles += @($stdoutPath, $stderrPath)

    $servicePid = Read-PidFile -Path $pidPath -ServiceName $serviceName
    if ($servicePid) {
        $process = Get-CimProcessById -ProcessId $servicePid
        if ($process -and (Test-ServiceProcess -Process $process -ServiceName $serviceName)) {
            Add-Candidate -ProcessId $servicePid -Reason "$serviceName pid file"
        }
    }

    $existingLogs = @(@($stdoutPath, $stderrPath) | Where-Object { Test-Path $_ })
    if ($existingLogs.Count -gt 0) {
        foreach ($lockingPid in Get-LockingProcessIds -Paths $existingLogs) {
            $process = Get-CimProcessById -ProcessId $lockingPid
            if ($process -and (Test-DevLockerProcess -Process $process -ServiceName $serviceName)) {
                Add-Candidate -ProcessId $lockingPid -Reason "$serviceName log lock"
            }
        }
    }
}

$allProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
foreach ($process in $allProcesses) {
    foreach ($serviceName in $serviceNames) {
        if (Test-ServiceProcess -Process $process -ServiceName $serviceName) {
            Add-Candidate -ProcessId ([int]$process.ProcessId) -Reason "$serviceName command line"
        }
    }
}

if ($script:candidates.Count -eq 0) {
    Write-Host "[dev] no matching dev server process found for target: $Target"
}
else {
    $visited = @{}
    foreach ($candidate in $script:candidates.Values | Sort-Object ProcessId) {
        $process = Get-Process -Id $candidate.ProcessId -ErrorAction SilentlyContinue
        if (!$process -or $process.HasExited) {
            continue
        }

        $reasons = [string]::Join(", ", $candidate.Reasons)
        Write-Host "[dev] stopping $($process.ProcessName) ($($candidate.ProcessId)): $reasons"
        Stop-ProcessTree -ProcessId $candidate.ProcessId -Visited $visited
    }
}

foreach ($pidFile in $pidFiles) {
    if (Test-Path $pidFile) {
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    }
}

if (!(Wait-LogsUnlocked -Paths $logFiles)) {
    Write-Warning "[dev] one or more dev log files are still locked; close the owning process and retry."
    exit 1
}

Write-Host "[dev] stop complete for target: $Target"
