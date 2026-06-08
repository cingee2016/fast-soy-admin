"""CLI display helpers."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import click

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WRITTEN_STATUSES = {"created", "appended"}


def configure_output_encoding() -> None:
    """Use UTF-8 streams so CLI icons do not crash on legacy Windows codepages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


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
        click.echo(f"  [ok] {display_path}")
    elif status == "appended":
        click.echo(f"  [+] {display_path} (已追加 export)")
    elif status == "exists":
        click.echo(f"  [skip] {display_path} (已存在，用 --force 覆盖)")
    elif status == "skipped":
        click.echo(f"  [-] {display_path} (跳过)")
    elif status == "not-found":
        click.echo(f"  [missing] {display_path} (文件不存在，请手动处理)")
    else:
        click.echo(f"  [?] {display_path} ({status})")


def run_just_format(target: str) -> bool:
    """Run the project-level formatter for a target."""
    label = f"just fmt {target}"
    click.echo("")
    click.echo(f"  [run] {label}")
    try:
        result = subprocess.run(
            ["just", "fmt", target],
            cwd=PROJECT_ROOT,
            check=False,
        )
    except FileNotFoundError:
        click.echo(f"  [warn] just 未安装，跳过 {label}")
        return False

    if result.returncode == 0:
        click.echo(f"  [ok] {label} 完成")
        return True

    click.echo(f"  [warn] {label} 失败")
    return False
