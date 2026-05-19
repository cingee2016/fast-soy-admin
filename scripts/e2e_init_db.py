"""E2E 用：直接从当前模型生成 schema，不走迁移、不污染 migrations/ 目录。"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_E2E_DB = "app_system_e2e.sqlite3"

os.environ.setdefault("DB_URL", f"sqlite://{DEFAULT_E2E_DB}?busy_timeout=5000")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault("GUARD_ENABLED", "false")

from tortoise import Tortoise  # noqa: E402

from app.core.config import APP_SETTINGS  # noqa: E402


async def main() -> None:
    db_url = APP_SETTINGS.DB_URL
    if "e2e" not in db_url:
        sys.exit(f"[e2e_init_db] 拒绝执行：DB_URL 未包含 'e2e' 标记，当前={db_url!r}")

    if db_url.startswith("sqlite://") and DEFAULT_E2E_DB in db_url:
        Path(DEFAULT_E2E_DB).unlink(missing_ok=True)

    await Tortoise.init(config=APP_SETTINGS.TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
