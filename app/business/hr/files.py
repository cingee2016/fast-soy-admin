from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.utils import APP_SETTINGS, BizError, Code

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024


async def save_avatar(file: UploadFile) -> str:
    """Validate and save an avatar image, returning its public URL."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise BizError(code=Code.FAIL, msg="仅支持 JPEG/PNG/GIF/WebP 格式的图片")

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise BizError(code=Code.FAIL, msg="图片大小不能超过 2MB")

    # 头像放入公开 static 目录，数据库只保存可访问 URL。
    ext = Path(file.filename or "avatar.png").suffix or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = APP_SETTINGS.STATIC_ROOT / "avatars"
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / filename).write_bytes(content)

    return f"/static/avatars/{filename}"
