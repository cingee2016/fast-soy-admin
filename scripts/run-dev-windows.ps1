param(
    [Parameter(Mandatory = $true)]
    [string]$Root,

    [Parameter(Mandatory = $true)]
    [ValidateSet("all", "backend", "frontend")]
    [string]$Target
)

$ErrorActionPreference = "Stop"

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
        [int]$ProcessId
    )

    foreach ($childId in Get-ChildProcessIds -ParentId $ProcessId) {
        Stop-ProcessTree -ProcessId $childId
    }

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Write-NewLogContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [ref]$Position
    )

    if (!(Test-Path $Path)) {
        return
    }

    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $reader = $null

    try {
        [void]$stream.Seek($Position.Value, [System.IO.SeekOrigin]::Begin)
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8, $true, 4096, $true)
        $text = $reader.ReadToEnd()
        $Position.Value = $stream.Position

        if ($text.Length -gt 0) {
            Write-Host -NoNewline $text
        }
    }
    finally {
        if ($reader) {
            $reader.Dispose()
        }

        $stream.Dispose()
    }
}

function Test-CancelKeyPressed {
    try {
        while ([System.Console]::KeyAvailable) {
            $key = [System.Console]::ReadKey($true)
            $isCtrlC = (($key.Modifiers -band [System.ConsoleModifiers]::Control) -and $key.Key -eq [System.ConsoleKey]::C)
            $isEtx = ([int][char]$key.KeyChar -eq 3)

            if ($isCtrlC -or $isEtx) {
                return $true
            }
        }
    }
    catch [System.InvalidOperationException] {
        return $false
    }
    catch [System.IO.IOException] {
        return $false
    }

    return $false
}

function Format-Elapsed {
    param(
        [Parameter(Mandatory = $true)]
        [datetime]$StartTime
    )

    $elapsed = (Get-Date) - $StartTime

    if ($elapsed.Days -gt 0) {
        return "{0}d {1}" -f $elapsed.Days, $elapsed.ToString("hh\:mm\:ss")
    }

    return $elapsed.ToString("hh\:mm\:ss")
}

function Start-DevProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,

        [Parameter(Mandatory = $true)]
        [string]$Command,

        [Parameter(Mandatory = $true)]
        [string]$StdoutPath,

        [Parameter(Mandatory = $true)]
        [string]$StderrPath
    )

    $redirectedCommand = "$Command 1> `"$StdoutPath`" 2> `"$StderrPath`""

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = "cmd.exe"
    $startInfo.Arguments = "/d /s /c `"$redirectedCommand`""
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.Environment["FORCE_COLOR"] = "1"

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    [void]$process.Start()

    [PSCustomObject]@{
        Name = $Name
        Process = $process
        StdoutPath = $StdoutPath
        StderrPath = $StderrPath
        StdoutPosition = 0L
        StderrPosition = 0L
    }
}

$logPath = Join-Path $Root "tmp"
$processes = @()
$exitCode = 0
$script:cancelRequested = $false
$previousTreatControlCAsInput = $false
$supportsConsoleInput = -not [System.Console]::IsInputRedirected
$cancelHandlerRegistered = $false

$cancelHandler = [System.ConsoleCancelEventHandler]{
    param($sender, $eventArgs)

    $eventArgs.Cancel = $true
    $script:cancelRequested = $true
}

try {
    if ($supportsConsoleInput) {
        try {
            $previousTreatControlCAsInput = [System.Console]::TreatControlCAsInput
            [System.Console]::TreatControlCAsInput = $true
            [System.Console]::add_CancelKeyPress($cancelHandler)
            $cancelHandlerRegistered = $true
        }
        catch [System.IO.IOException] {
            $supportsConsoleInput = $false
        }
    }

    New-Item -ItemType Directory -Force -Path $logPath | Out-Null

    $services = @()
    if ($Target -eq "all" -or $Target -eq "backend") {
        $services += [PSCustomObject]@{
            Name = "backend"
            WorkingDirectory = $Root
            Command = "uv run python run.py"
        }
    }
    if ($Target -eq "all" -or $Target -eq "frontend") {
        $services += [PSCustomObject]@{
            Name = "frontend"
            WorkingDirectory = Join-Path $Root "web"
            Command = "pnpm dev"
        }
    }

    $startedAt = Get-Date
    foreach ($service in $services) {
        $stdoutPath = Join-Path $logPath "run-$($service.Name).out.log"
        $stderrPath = Join-Path $logPath "run-$($service.Name).err.log"
        Set-Content -Path $stdoutPath -Value "" -Encoding UTF8
        Set-Content -Path $stderrPath -Value "" -Encoding UTF8

        Write-Host "[dev] starting $($service.Name): $($service.Command)"
        $processes += Start-DevProcess -Name $service.Name -WorkingDirectory $service.WorkingDirectory -Command $service.Command -StdoutPath $stdoutPath -StderrPath $stderrPath
    }

    while ($true) {
        if ($supportsConsoleInput -and (Test-CancelKeyPressed)) {
            $script:cancelRequested = $true
        }

        foreach ($entry in $processes) {
            $stdoutPosition = $entry.StdoutPosition
            $stderrPosition = $entry.StderrPosition
            Write-NewLogContent -Path $entry.StdoutPath -Position ([ref]$stdoutPosition)
            Write-NewLogContent -Path $entry.StderrPath -Position ([ref]$stderrPosition)
            $entry.StdoutPosition = $stdoutPosition
            $entry.StderrPosition = $stderrPosition
        }

        if ($script:cancelRequested) {
            Write-Host "stopping dev server(s)... runtime: $(Format-Elapsed -StartTime $startedAt)"
            $exitCode = 0
            break
        }

        Start-Sleep -Milliseconds 200

        foreach ($entry in $processes) {
            $entry.Process.Refresh()
            if ($entry.Process.HasExited) {
                $exitCode = $entry.Process.ExitCode
                if ($exitCode -in @(130, 512, -1073741510)) {
                    $exitCode = 0
                }
                Write-Host "$($entry.Name) exited with code $($entry.Process.ExitCode) after $(Format-Elapsed -StartTime $startedAt)"
                break
            }
        }

        if ($exitCode -ne 0 -or ($processes | Where-Object { $_.Process.HasExited } | Select-Object -First 1)) {
            break
        }
    }
}
finally {
    foreach ($entry in $processes) {
        $stdoutPosition = $entry.StdoutPosition
        $stderrPosition = $entry.StderrPosition
        Write-NewLogContent -Path $entry.StdoutPath -Position ([ref]$stdoutPosition)
        Write-NewLogContent -Path $entry.StderrPath -Position ([ref]$stderrPosition)
        $entry.StdoutPosition = $stdoutPosition
        $entry.StderrPosition = $stderrPosition
    }

    foreach ($entry in $processes) {
        if ($entry.Process) {
            Stop-ProcessTree -ProcessId $entry.Process.Id
            $entry.Process.Dispose()
        }
    }

    if ($cancelHandlerRegistered) {
        [System.Console]::remove_CancelKeyPress($cancelHandler)
    }

    if ($supportsConsoleInput) {
        [System.Console]::TreatControlCAsInput = $previousTreatControlCAsInput
    }
}

exit $exitCode
