from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request
from fastapi_cache import JsonCoder
from fastapi_cache.decorator import cache

from app.controllers.user import user_controller
from app.core.code import Code
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth, check_token
from app.log import log
from app.models.system import Button, Role, StatusType, User
from app.radar.developer import radar_log
from app.schemas.base import Fail, Success
from app.schemas.login import CaptchaRequest, CodeLoginSchema, CredentialsSchema, JWTOut, JWTPayload, RegisterSchema
from app.services.captcha import send_captcha, verify_captcha
from app.settings import APP_SETTINGS
from app.utils.security import create_access_token, get_password_hash

router = APIRouter()


def _build_tokens(user_obj: User, token_version: int) -> JWTOut:
    """构建 access_token + refresh_token"""
    payload = JWTPayload(data={"userId": user_obj.id, "userName": user_obj.user_name, "tokenType": "accessToken", "tokenVersion": token_version}, iat=datetime.now(UTC), exp=datetime.now(UTC))

    access_token_payload = payload.model_copy(deep=True)
    access_token_payload.exp += timedelta(minutes=APP_SETTINGS.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_payload = payload.model_copy(deep=True)
    refresh_token_payload.data["tokenType"] = "refreshToken"
    refresh_token_payload.exp += timedelta(minutes=APP_SETTINGS.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)

    return JWTOut(
        access_token=create_access_token(data=access_token_payload),
        refresh_token=create_access_token(data=refresh_token_payload),
    )


@router.post("/login", summary="登录")
async def _(credentials: CredentialsSchema, request: Request):
    user_obj: User | None = await user_controller.authenticate(credentials)

    await user_controller.update_last_login(user_obj.id)

    redis = request.app.state.redis
    token_version = int(await redis.get(f"token_version:{user_obj.id}") or 0)
    data = _build_tokens(user_obj, token_version)

    log.info(f"用户登录成功, 用户名: {user_obj.user_name}")
    radar_log("用户登录成功", data={"userName": user_obj.user_name, "userId": user_obj.id})
    return Success(data=data.model_dump(by_alias=True))


@router.post("/captcha", summary="获取验证码")
async def _(captcha_in: CaptchaRequest, request: Request):
    redis = request.app.state.redis
    success = await send_captcha(redis, captcha_in.phone)
    if not success:
        return Fail(msg="验证码发送失败，请稍后重试")
    return Success(msg="验证码已发送")


@router.post("/code-login", summary="验证码登录")
async def _(login_in: CodeLoginSchema, request: Request):
    redis = request.app.state.redis

    # 验证验证码
    if not await verify_captcha(redis, login_in.phone, login_in.code):
        return Fail(code=Code.FAIL, msg="验证码错误或已过期")

    # 通过手机号查找用户
    user_obj = await User.filter(user_phone=login_in.phone).first()
    if not user_obj:
        return Fail(code=Code.FAIL, msg="该手机号未注册")

    if user_obj.status_type == StatusType.disable:
        return Fail(code=Code.ACCOUNT_DISABLED, msg="该账号已被禁用")

    await user_controller.update_last_login(user_obj.id)

    token_version = int(await redis.get(f"token_version:{user_obj.id}") or 0)
    data = _build_tokens(user_obj, token_version)

    log.info(f"验证码登录成功, 手机号: {login_in.phone}")
    radar_log("验证码登录成功", data={"phone": login_in.phone, "userId": user_obj.id})
    return Success(data=data.model_dump(by_alias=True))


@router.post("/register", summary="注册")
async def _(register_in: RegisterSchema, request: Request):
    redis = request.app.state.redis

    # 验证验证码
    if not await verify_captcha(redis, register_in.phone, register_in.code):
        return Fail(code=Code.FAIL, msg="验证码错误或已过期")

    # 检查手机号是否已注册
    if await User.filter(user_phone=register_in.phone).exists():
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="该手机号已注册")

    # 用户名：优先使用指定的，否则用手机号
    user_name = register_in.user_name or register_in.phone
    if await User.filter(user_name=user_name).exists():
        return Fail(code=Code.DUPLICATE_RESOURCE, msg="该用户名已存在")

    # 创建用户
    from app.models.system import Role

    default_role = await Role.filter(role_code="R_USER").first()
    user_obj = await User.create(
        user_name=user_name,
        password=get_password_hash(register_in.password),
        nick_name=user_name,
        user_phone=register_in.phone,
    )

    if default_role:
        await user_obj.by_user_roles.add(default_role)

    log.info(f"用户注册成功, 手机号: {register_in.phone}, 用户名: {user_name}")
    radar_log("用户注册成功", data={"phone": register_in.phone, "userName": user_name, "userId": user_obj.id})
    return Success(msg="注册成功")


@router.post("/refresh-token", summary="刷新认证")
async def _(jwt_token: JWTOut, request: Request):
    if not jwt_token.refresh_token:
        return Fail(code=Code.INVALID_TOKEN, msg="The refreshToken is not valid.")
    status, code, data = check_token(jwt_token.refresh_token)
    if not status:
        return Fail(code=code, msg=data)

    user_id = data["data"]["userId"]
    user_obj = await user_controller.get(id=user_id)

    if data["data"]["tokenType"] != "refreshToken":
        return Fail(code=Code.INVALID_SESSION, msg="The token is not an refresh token.")

    if user_obj.status_type == StatusType.disable:
        radar_log("刷新令牌失败: 账号已禁用", level="WARNING", data={"userId": user_id})
        return Fail(code=Code.ACCOUNT_DISABLED, msg="This user has been disabled.")

    redis = request.app.state.redis
    token_version_in_jwt = data["data"].get("tokenVersion", 0)
    current_version = int(await redis.get(f"token_version:{user_id}") or 0)
    if token_version_in_jwt < current_version:
        return Fail(code=Code.INVALID_TOKEN, msg="Token已失效，请重新登录")

    await user_controller.update_last_login(user_id)
    token_version = int(await redis.get(f"token_version:{user_obj.id}") or 0)
    data = _build_tokens(user_obj, token_version)

    radar_log("刷新令牌成功", data={"userId": user_obj.id})
    return Success(data=data.model_dump(by_alias=True))


@cache(expire=60, coder=JsonCoder)
@router.get("/user-info", summary="查看用户信息", dependencies=[DependAuth])
async def _():
    user_id = CTX_USER_ID.get()
    user_obj: User = await user_controller.get(id=user_id)
    data = await user_obj.to_dict(exclude_fields=["id", "password", "create_time", "update_time"])

    user_roles: list[Role] = await user_obj.by_user_roles
    user_role_codes = [user_role.role_code for user_role in user_roles]

    user_role_button_codes = [b.button_code for b in await Button.all()] if "R_SUPER" in user_role_codes else [b.button_code for user_role in user_roles for b in await user_role.by_role_buttons]

    user_role_button_codes = list(set(user_role_button_codes))

    data.update({"userId": user_id, "roles": user_role_codes, "buttons": user_role_button_codes})
    radar_log("获取用户信息", data={"userId": user_obj.id})
    return Success(data=data)
