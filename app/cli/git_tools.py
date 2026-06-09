"""Git safety helpers for code generation commands."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import click

from app.cli.display import format_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKUP_DIR = "codegen_backups"
CODEGEN_PATH_PREFIXES = (
    "app/business/",
    "web/src/service/api/",
    "web/src/router/elegant/",
    "web/src/typings/api/",
    "web/src/views/",
    "web/src/locales/langs/_generated/",
)
CODEGEN_PATHS = {
    "web/src/typings/components.d.ts",
}


@dataclass(frozen=True)
class GitChange:
    status: str
    path: str

    @property
    def is_untracked(self) -> bool:
        return self.status == "??"


def _run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise click.ClickException("未找到 git，代码生成需要在可用的 Git 工作区中执行。") from exc

    if check and result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip() or "git 命令执行失败"
        raise click.ClickException(message)
    return result


def _ensure_git_repo() -> None:
    result = _run_git(["rev-parse", "--show-toplevel"])
    root = Path(result.stdout.strip()).resolve()
    if root != PROJECT_ROOT.resolve():
        raise click.ClickException(f"当前 CLI 只能在项目根 Git 工作区执行，检测到: {format_path(root)}")

    head = _run_git(["rev-parse", "--verify", "HEAD"], check=False)
    if head.returncode != 0:
        raise click.ClickException("当前仓库还没有提交记录。请先提交 models.py 等准备工作，再运行代码生成。")


def _status_output() -> str:
    return _run_git(["status", "--porcelain=v1", "--untracked-files=all"]).stdout


def parse_git_status(output: str) -> list[GitChange]:
    changes: list[GitChange] = []
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        status = raw_line[:2]
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        changes.append(GitChange(status=status, path=path.replace("\\", "/")))
    return changes


def ensure_committed_worktree() -> None:
    """Require a committed, clean Git worktree before writing generated files."""
    _ensure_git_repo()
    changes = parse_git_status(_status_output())
    if not changes:
        return

    preview = "\n".join(f"    {change.status} {change.path}" for change in changes[:12])
    more = "" if len(changes) <= 12 else f"\n    ... 还有 {len(changes) - 12} 项"
    raise click.ClickException(
        "代码生成前需要一个已提交且干净的工作区，方便用 git 精准撤销生成结果。\n"
        "请先提交或暂存当前改动，再重新运行生成命令。\n\n"
        f"当前未提交改动:\n{preview}{more}\n\n"
        "可用命令:\n"
        "  git status --short\n"
        '  git add <files> && git commit -m "prepare codegen"'
    )


def is_codegen_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized in CODEGEN_PATHS or any(normalized.startswith(prefix) for prefix in CODEGEN_PATH_PREFIXES)


def collect_codegen_changes() -> tuple[list[GitChange], list[GitChange]]:
    _ensure_git_repo()
    changes = parse_git_status(_status_output())
    selected = [change for change in changes if is_codegen_path(change.path)]
    skipped = [change for change in changes if not is_codegen_path(change.path)]
    return selected, skipped


def backup_codegen_changes(changes: list[GitChange], backup_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_root / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "created_at": timestamp,
        "changes": [asdict(change) for change in changes],
        "note": "Files are backed up before git restore / git clean undo generated code.",
    }
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    for change in changes:
        source = PROJECT_ROOT / change.path
        if not source.exists() or source.is_dir():
            continue
        target = backup_dir / change.path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    return backup_dir


def undo_codegen_changes(changes: list[GitChange]) -> None:
    tracked_paths = [change.path for change in changes if not change.is_untracked]
    untracked_paths = [change.path for change in changes if change.is_untracked]

    if tracked_paths:
        _run_git(["restore", "--staged", "--worktree", "--", *tracked_paths])
    if untracked_paths:
        _run_git(["clean", "-fd", "--", *untracked_paths])


def format_change_lines(changes: list[GitChange]) -> list[str]:
    return [f"  {change.status} {change.path}" for change in changes]


def project_backup_root(name: str = DEFAULT_BACKUP_DIR) -> Path:
    return PROJECT_ROOT / name
