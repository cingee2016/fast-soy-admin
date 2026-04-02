from typing import Any

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.core.cache import get_role_apis
from app.core.code import Code
from app.core.config import APP_SETTINGS
from app.core.ctx import CTX_USER_ID, CTX_X_REQUEST_ID
from app.core.exceptions import (
    HTTPException,
)
from app.core.log import log
from app.core.tools import check_url
from app.system.models import StatusType, User
from app.system.radar.ctx import CTX_RADAR
from app.system.radar.developer import radar_log

oauth2_schema = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def check_token(token: str) -> tuple[bool, str, Any]:
    try:
        options = {"verify_signature": True, "verify_aud": False, "exp": True}
        decode_data = jwt.decode(token, APP_SETTINGS.SECRET_KEY, algorithms=[APP_SETTINGS.JWT_ALGORITHM], options=options)  # type: ignore[arg-type]
        return True, Code.SUCCESS, decode_data
    except jwt.DecodeError:
        return False, Code.INVALID_TOKEN, "无效的Token"
    except jwt.ExpiredSignatureError:
        return False, Code.TOKEN_EXPIRED, "登录已过期"
    except Exception as e:
        return False, Code.INVALID_TOKEN, f"{repr(e)}"


class AuthControl:
    @classmethod
    async def is_authed(cls, request: Request, token: str = Depends(oauth2_schema)) -> User | None:
        if not token:
            raise HTTPException(code=Code.INVALID_TOKEN, msg="Authentication failed, token does not exists in the request.")
        user_id = CTX_USER_ID.get()
        if user_id == 0:
            status, code, decode_data = check_token(token)
            if not status:
                raise HTTPException(code=code, msg=decode_data)

            if decode_data["data"]["tokenType"] != "accessToken":
                raise HTTPException(code=Code.INVALID_SESSION, msg="The token is not an access token")

            user_id = decode_data["data"]["userId"]

            # 校验 token 版本号
            redis = request.app.state.redis
            token_version_in_jwt = decode_data["data"].get("tokenVersion", 0)
            current_version = int(await redis.get(f"token_version:{user_id}") or 0)
            if token_version_in_jwt < current_version:
                raise HTTPException(code=Code.INVALID_TOKEN, msg="Token已失效，请重新登录")

        user = await User.filter(id=user_id).first()
        if not user:
            raise HTTPException(code=Code.INVALID_SESSION, msg=f"Authentication failed, the user_id: {user_id} does not exists in the system.")
        CTX_USER_ID.set(int(user_id))
        # 写入 radar 上下文，记录操作人信息
        radar_ctx = CTX_RADAR.get()
        if radar_ctx is not None:
            radar_ctx.user_id = int(user_id)
            radar_ctx.user_name = user.user_name
        return user


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        await current_user.fetch_related("by_user_roles")
        user_roles_codes: list[str] = [r.role_code for r in current_user.by_user_roles]
        if "R_SUPER" in user_roles_codes:  # 超级管理员
            return

        if not current_user.by_user_roles:
            raise HTTPException(code=Code.PERMISSION_DENIED, msg="The user is not bound to a role")

        method = request.method.lower()
        path = request.url.path
        redis = request.app.state.redis

        # 从 Redis 汇总所有角色的 API 权限
        permission_apis: set[tuple[str, str, str]] = set()
        for role_code in user_roles_codes:
            apis = await get_role_apis(redis, role_code)
            for api in apis:
                permission_apis.add((api["method"], api["path"], api["status"]))

        for api_method, api_path, api_status in permission_apis:
            if api_method == method and check_url(api_path, path):
                if api_status == StatusType.disable.value:
                    raise HTTPException(code=Code.API_DISABLED, msg=f"The API has been disabled, method: {method} path: {path}")
                return

        log.error(f"Permission denied, method: {method.upper()} path: {path}, x-request-id: {CTX_X_REQUEST_ID.get()}")
        radar_log("权限拒绝", level="ERROR", data={"method": method.upper(), "path": path, "xRequestId": CTX_X_REQUEST_ID.get()})
        raise HTTPException(code=Code.PERMISSION_DENIED, msg=f"Permission denied, method: {method} path: {path}")


DependAuth = Depends(AuthControl.is_authed)
DependPermission = Depends(PermissionControl.has_permission)
