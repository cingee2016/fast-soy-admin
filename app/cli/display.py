"""CLI display helpers."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import click

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRITTEN_STATUSES = {"created", "appended"}


def restore_console_modes() -> None:
    """Restore Windows console control-character and line-input handling."""
    if os.name != "nt":
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    std_input_handle = -10
    std_output_handle = -11
    std_error_handle = -12
    enable_processed_input = 0x0001
    enable_line_input = 0x0002
    enable_echo_input = 0x0004
    enable_processed_output = 0x0001
    enable_wrap_at_eol_output = 0x0002

    def enable_flags(std_handle: int, flags: int) -> None:
        handle = kernel32.GetStdHandle(std_handle)
        if handle in (0, -1):
            return

        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return

        new_mode = mode.value | flags
        if new_mode != mode.value:
            kernel32.SetConsoleMode(handle, new_mode)

    enable_flags(std_input_handle, enable_processed_input | enable_line_input | enable_echo_input)
    enable_flags(std_output_handle, enable_processed_output | enable_wrap_at_eol_output)
    enable_flags(std_error_handle, enable_processed_output | enable_wrap_at_eol_output)


def configure_output_encoding() -> None:
    """Use UTF-8 streams so CLI icons do not crash on legacy Windows codepages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    restore_console_modes()


def echo_lines(lines: Iterable[str]) -> None:
    """Print multi-line CLI output one line at a time."""
    for line in lines:
        click.echo(line)


def format_path(path: Path | str) -> str:
    """Format paths for CLI output with POSIX separators on every platform."""
    if isinstance(path, Path):
        return path.as_posix()
    return path.replace("\\", "/")


def relative_path(path: Path, base: Path = PROJECT_ROOT) -> str:
    """Return a project-relative POSIX path for CLI output."""
    return path.relative_to(base).as_posix()


def has_written_files(results: list[tuple[str, str]]) -> bool:
    """Whether a generator result contains newly written or appended files."""
    return any(status in WRITTEN_STATUSES for _, status in results)


def echo_file_result(path: str | Path, status: str) -> None:
    """Print a generated file result with a consistent icon and message."""
    display_path = format_path(path)
    if status == "created":
        click.echo(f"  ✅ {display_path}")
    elif status == "appended":
        click.echo(f"  ➕ {display_path} (已追加 export)")
    elif status == "exists":
        click.echo(f"  ⚠️  {display_path} (已存在，用 --force 覆盖)")
    elif status == "skipped":
        click.echo(f"  ➖ {display_path} (跳过)")
    elif status == "not-found":
        click.echo(f"  ❌ {display_path} (文件不存在，请手动处理)")
    else:
        click.echo(f"  ❔ {display_path} ({status})")


def _echo_captured_output(output: str | None, *, err: bool = False) -> None:
    """Print captured child-process output only when it has useful content."""
    if not output:
        return

    output = output.rstrip()
    if not output:
        return

    for line in output.splitlines():
        click.echo(line, err=err)


def run_just_format(target: str) -> bool:
    """Run the project-level formatter for a target."""
    label = f"just fmt {target}"
    click.echo("")
    click.echo(f"  🔧 {label}")
    try:
        result = subprocess.run(
            ["just", "fmt", target],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        click.echo(f"  ⚠️  just 未安装，跳过 {label}")
        return False
    finally:
        restore_console_modes()

    if result.returncode == 0:
        click.echo(f"  ✅ {label} 完成")
        return True

    click.echo(f"  ⚠️  {label} 失败")
    _echo_captured_output(result.stdout)
    _echo_captured_output(result.stderr, err=True)
    return False
