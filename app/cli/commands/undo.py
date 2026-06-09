"""undo 命令 — 备份并撤销 CLI 代码生成结果。"""

from __future__ import annotations

from pathlib import Path

import click

from app.cli.display import echo_lines, relative_path
from app.cli.git_tools import (
    DEFAULT_BACKUP_DIR,
    backup_codegen_changes,
    collect_codegen_changes,
    format_change_lines,
    project_backup_root,
    undo_codegen_changes,
)

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 120}


@click.command("undo", context_settings=CONTEXT_SETTINGS)
@click.option("--dry-run", is_flag=True, help="只预览将撤销的文件，不备份、不执行 git restore/clean")
@click.option("-y", "--yes", "assume_yes", is_flag=True, help="跳过确认，直接备份并撤销")
@click.option("--backup-dir", default=DEFAULT_BACKUP_DIR, show_default=True, help="项目根目录下的备份文件夹")
def undo(dry_run: bool, assume_yes: bool, backup_dir: str):
    """撤销最近一次 CLI 生成造成的前后端改动。

    仅处理 app/business 与 web/src 下的生成器相关路径。撤销前会把当前文件内容
    备份到项目根目录的 codegen_backups/<timestamp>/，再用 git restore / git clean
    恢复工作区。
    """
    selected, skipped = collect_codegen_changes()

    click.echo("")
    if not selected:
        click.echo("  ✅ 没有发现可由代码生成器撤销的前后端改动。")
        if skipped:
            click.echo("")
            click.echo("  仍有其他未提交改动，undo 不会触碰它们：")
            echo_lines(format_change_lines(skipped))
        return

    click.echo("  将撤销这些生成器相关改动：")
    echo_lines(format_change_lines(selected))

    if skipped:
        click.echo("")
        click.echo("  这些非生成器路径会保留：")
        echo_lines(format_change_lines(skipped))

    root = project_backup_root(backup_dir)
    click.echo("")
    click.echo(f"  备份位置: {relative_path(root)}")

    if dry_run:
        click.echo("")
        click.echo("  🧭 dry-run 完成，没有修改文件。")
        return

    if not assume_yes:
        click.echo("")
        click.confirm("  确认备份并用 git 撤销这些生成结果？", abort=True)

    backup_path = backup_codegen_changes(selected, root)
    undo_codegen_changes(selected)

    click.echo("")
    click.echo(f"  ✅ 已备份到 {relative_path(Path(backup_path))}")
    click.echo("  ✅ 已用 git restore / git clean 撤销生成结果")
