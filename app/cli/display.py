"""CLI display helpers."""

from __future__ import annotations

import subprocess
import sys
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
        click.echo(f"  \033[32m✓\033[0m {display_path}")
    elif status == "appended":
        click.echo(f"  \033[32m+\033[0m {display_path} (已追加 export)")
    elif status == "exists":
        click.echo(f"  \033[33m⚠\033[0m {display_path} (已存在，用 --force 覆盖)")
    elif status == "skipped":
        click.echo(f"  \033[90m-\033[0m {display_path} (跳过)")
    elif status == "not-found":
        click.echo(f"  \033[31m✗\033[0m {display_path} (文件不存在，请手动处理)")
    else:
        click.echo(f"  \033[90m?\033[0m {display_path} ({status})")


def run_just_format(target: str) -> bool:
    """Run the project-level formatter for a target."""
    label = f"just fmt {target}"
    try:
        result = subprocess.run(
            ["just", "fmt", target],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        click.echo(f"\n  \033[33m⚠\033[0m just 未安装，跳过 {label}")
        return False

    if result.returncode == 0:
        click.echo(f"\n  \033[32m✓\033[0m {label} 完成")
        return True

    output = (result.stderr or result.stdout).strip()
    click.echo(f"\n  \033[33m⚠\033[0m {label} 失败")
    if output:
        click.echo(f"  \033[90m{output[:600]}\033[0m")
    return False
