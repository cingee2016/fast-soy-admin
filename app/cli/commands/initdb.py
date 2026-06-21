"""initdb 命令 — 初始化数据库：生成迁移并应用。"""

from __future__ import annotations

import asyncio
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from tortoise import Tortoise, connections

from app.cli.display import format_path, relative_path
from app.core.config import APP_SETTINGS

BASE_DIR = APP_SETTINGS.BASE_DIR
MIGRATIONS_DIR = BASE_DIR / "migrations"


def _parse_sqlite_path(db_url: str) -> Path | None:
    """从 DB_URL 中提取 SQLite 文件路径，非 SQLite 引擎返回 None。"""
    if not db_url.startswith("sqlite://"):
        return None
    # sqlite://relative.sqlite3?params  或  sqlite:///absolute/path.sqlite3?params
    raw = db_url[len("sqlite://") :]
    # 去掉 query string
    path_str = raw.split("?", 1)[0]
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = BASE_DIR / p
    return p


def _check_migrations_dir() -> str | None:
    """检查 migrations/app_system 是否存在且含迁移文件。返回描述或 None。"""
    app_system_dir = MIGRATIONS_DIR / "app_system"
    if not app_system_dir.is_dir():
        return None
    migration_files = [f for f in app_system_dir.iterdir() if f.suffix == ".py" and f.name != "__init__.py"]
    if not migration_files:
        return None
    return f"迁移目录 migrations/app_system/ 已存在（{len(migration_files)} 个迁移文件）"


def _check_sqlite_file(db_url: str) -> str | None:
    """检查 SQLite 数据库文件是否存在。返回描述或 None。"""
    sqlite_path = _parse_sqlite_path(db_url)
    if sqlite_path is None:
        return None
    if not sqlite_path.exists():
        return None
    return f"SQLite 数据库文件已存在: {relative_path(sqlite_path, BASE_DIR)}"


def _check_migration_table(db_url: str) -> str | None:
    """检查数据库中 tortoise_migrations 表是否存在且有记录。返回描述或 None。"""
    sqlite_path = _parse_sqlite_path(db_url)
    if sqlite_path is None:
        # 非 SQLite：通过 DB_URL 连接检查
        return _check_migration_table_generic(db_url)
    if not sqlite_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(sqlite_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tortoise_migrations'")
        if not cursor.fetchone():
            conn.close()
            return None
        count = conn.execute("SELECT COUNT(*) FROM tortoise_migrations").fetchone()[0]
        conn.close()
        if count == 0:
            return None
        return f"数据库已有 {count} 条迁移记录（tortoise_migrations 表）"
    except Exception:
        return None


def _check_migration_table_generic(_db_url: str) -> str | None:
    """非 SQLite 数据库：通过 tortoise history 检查数据库中的已应用迁移记录。

    tortoise history 的输出形如::

        Connection: conn_system
          app_system:
            - app_system 0001_initial

    无迁移时最后一行是 ``(no applied migrations)`` 提示。只有以 ``- `` 开头的行
    才是真正的迁移记录，元信息行（Connection / app 标题 / 提示行）不能计入。
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "tortoise", "history"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        # 仅统计真正的迁移行（以 "- " 开头），忽略 Connection/应用名/(no applied migrations) 等元信息
        migration_lines = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("- ")]
        if migration_lines:
            return f"数据库已有 {len(migration_lines)} 条迁移记录"
    except Exception:
        pass
    return None


def _configured_migration_dirs() -> list[Path]:
    dirs: list[Path] = []
    apps = APP_SETTINGS.TORTOISE_ORM.get("apps", {})
    for app_config in apps.values():
        migration_module = app_config.get("migrations")
        if not migration_module:
            continue
        path = BASE_DIR / Path(str(migration_module).replace(".", "/"))
        if path not in dirs:
            dirs.append(path)
    return dirs


def _reset_migration_files() -> None:
    """清空本地自动生成的迁移文件，保留迁移包目录本身。"""
    migrations_root = MIGRATIONS_DIR.resolve()
    for migration_dir in _configured_migration_dirs():
        resolved = migration_dir.resolve()
        if not (resolved == migrations_root or resolved.is_relative_to(migrations_root)):
            raise click.ClickException(f"拒绝清理 migrations 目录外的路径: {format_path(migration_dir)}")

        migration_dir.mkdir(parents=True, exist_ok=True)
        for child in migration_dir.iterdir():
            if child.name == "__init__.py":
                continue
            if child.is_dir() and child.name == "__pycache__":
                shutil.rmtree(child)
                continue
            if child.is_file() and child.suffix == ".py":
                child.unlink()

        (migration_dir / "__init__.py").touch()

    tortoise_last = BASE_DIR / "tortoise_last.txt"
    if tortoise_last.exists():
        tortoise_last.unlink()


def _reset_sqlite_file(db_url: str) -> bool:
    sqlite_path = _parse_sqlite_path(db_url)
    if sqlite_path is None:
        return False

    for candidate in (sqlite_path, sqlite_path.with_name(f"{sqlite_path.name}-wal"), sqlite_path.with_name(f"{sqlite_path.name}-shm")):
        if candidate.exists():
            candidate.unlink()
    return True


async def _reset_database(db_url: str) -> None:
    """清空 --force 指向的数据库对象，用于重新生成并应用初始迁移。"""
    if _reset_sqlite_file(db_url):
        return

    scheme = urlparse(db_url).scheme
    await Tortoise.init(config=APP_SETTINGS.TORTOISE_ORM)
    try:
        conn = connections.get("conn_system")
        if scheme in {"postgres", "asyncpg", "psycopg"}:
            await conn.execute_script("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public;")
            return

        if scheme in {"mysql", "asyncmy"}:
            rows = await conn.execute_query_dict("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
            table_names = [str(next(iter(row.values()))) for row in rows]
            if table_names:
                drops = " ".join(f"DROP TABLE IF EXISTS `{name}`;" for name in table_names)
                await conn.execute_script(f"SET FOREIGN_KEY_CHECKS=0; {drops} SET FOREIGN_KEY_CHECKS=1;")
            return

        raise click.ClickException(f"--force 暂不支持清空当前数据库类型: {scheme or '(unknown)'}")
    finally:
        await connections.close_all()


def _run_tortoise_cmd(args: list[str], *, label: str) -> None:
    """运行 tortoise 子命令，失败时抛出 ClickException。"""
    cmd = [sys.executable, "-m", "tortoise", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        click.echo(result.stdout.rstrip())
    if result.returncode != 0:
        err = result.stderr.strip() or "(无错误输出)"
        raise click.ClickException(f"{label}失败:\n{err}")


GUIDE_TEXT = """\

\033[1;32m✅ 数据库初始化完成！\033[0m

\033[1;33m📋 下一步：\033[0m

  启动服务验证：

     \033[36mjust run\033[0m

  首次启动时会自动创建默认用户、菜单、角色等初始化数据。
"""


@click.command()
@click.option("--force", is_flag=True, help="清空当前开发库和本地迁移基线，重新生成并应用初始迁移")
def initdb(force: bool):
    """初始化数据库 — 生成迁移并应用。

    首次使用时运行，会依次执行:
    1. tortoise init（创建迁移包目录）
    2. tortoise makemigrations（生成迁移文件）
    3. tortoise migrate（应用迁移到数据库）
    """
    db_url = APP_SETTINGS.DB_URL

    # ── 三级检查：任一命中即终止 ──
    if not force:
        checks = [
            _check_migrations_dir(),
            _check_sqlite_file(db_url),
            _check_migration_table(db_url),
        ]
        hits = [msg for msg in checks if msg is not None]

        if hits:
            click.echo("\n\033[1;31m⛔ 数据库已经初始化过，终止操作。\033[0m\n")
            click.echo("  检测到以下痕迹:\n")
            for msg in hits:
                click.echo(f"    • {msg}")
            click.echo("\n  如需重新初始化，请使用 \033[36m--force\033[0m 选项。")
            click.echo("  如需应用新的模型变更，请直接运行:\n")
            click.echo("    \033[36mjust mm\033[0m\n")
            raise SystemExit(1)

    if force:
        click.echo("\n\033[1;33m⚠️  --force 将清空当前 DB_URL 指向的数据库对象，并重建本地迁移基线。\033[0m")
        click.echo("  \033[1m[0/3]\033[0m 清理旧数据库状态和本地迁移文件...")
        _reset_migration_files()
        asyncio.run(_reset_database(db_url))

    # ── 执行初始化 ──
    click.echo("\n\033[1m🔧 开始初始化数据库...\033[0m\n")

    # 1. tortoise init — 创建 migrations 包目录结构
    click.echo("  \033[1m[1/3]\033[0m 初始化迁移目录...")
    _run_tortoise_cmd(["init"], label="tortoise init")

    # 2. tortoise makemigrations — 生成迁移文件
    click.echo("\n  \033[1m[2/3]\033[0m 生成迁移文件...")
    _run_tortoise_cmd(["makemigrations"], label="tortoise makemigrations")

    # 3. tortoise migrate — 应用迁移
    click.echo("\n  \033[1m[3/3]\033[0m 应用迁移...")
    _run_tortoise_cmd(["migrate"], label="tortoise migrate")

    click.echo(GUIDE_TEXT)
