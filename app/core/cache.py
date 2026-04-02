"""
Redis 缓存服务：常量路由、角色权限（菜单/API/按钮）的读写。

Key 设计:
    constant_routes              — 常量路由 JSON
    role:{role_code}:menus       — 角色菜单 ID JSON 列表
    role:{role_code}:apis        — 角色 API JSON 列表 [{method, path, status}]
    role:{role_code}:buttons     — 角色按钮 ID JSON 列表
    token_version:{user_id}      — 用户 token 版本号（已有）
"""

import json

from redis.asyncio import Redis

from app.core.log import log

# ===================== 常量路由 =====================


async def load_constant_routes(redis: Redis) -> None:
    """从数据库加载常量路由到 Redis"""
    from app.system.models.admin import Menu

    menu_objs = await Menu.filter(constant=True, hide_in_menu=True)
    routes = []
    for m in menu_objs:
        route = {
            "name": m.route_name,
            "path": m.route_path,
            "component": m.component,
            "meta": {"title": m.menu_name, "i18nKey": m.i18n_key, "constant": m.constant, "hideInMenu": m.hide_in_menu},
        }
        if m.props:
            route["props"] = True
        routes.append(route)
    await redis.set("constant_routes", json.dumps(routes, ensure_ascii=False))
    log.info(f"Cached {len(routes)} constant routes to Redis")


async def get_constant_routes(redis: Redis) -> list[dict]:
    """从 Redis 获取常量路由"""
    data = await redis.get("constant_routes")
    if data:
        return json.loads(data)
    return []


# ===================== 角色权限 =====================


async def load_role_permissions(redis: Redis, role_code: str | None = None) -> None:
    """
    将角色权限数据加载到 Redis。

    Args:
        redis: Redis 实例
        role_code: 指定角色编码，为 None 时加载所有角色
    """
    from app.system.models.admin import Role

    if role_code:
        roles = await Role.filter(role_code=role_code)
    else:
        roles = await Role.all()

    pipe = redis.pipeline()
    for role in roles:
        code = role.role_code

        # 菜单 ID 列表
        await role.fetch_related("by_role_menus")
        menu_ids = [m.id for m in role.by_role_menus]
        pipe.set(f"role:{code}:menus", json.dumps(menu_ids))

        # API 列表 (method, path, status)
        await role.fetch_related("by_role_apis")
        apis = [{"method": api.api_method.value, "path": api.api_path, "status": api.status_type.value} for api in role.by_role_apis]
        pipe.set(f"role:{code}:apis", json.dumps(apis))

        # 按钮 code 列表
        await role.fetch_related("by_role_buttons")
        button_codes = [b.button_code for b in role.by_role_buttons]
        pipe.set(f"role:{code}:buttons", json.dumps(button_codes))

    await pipe.execute()
    count = len(roles)
    if role_code:
        log.info(f"Cached permissions for role: {role_code}")
    else:
        log.info(f"Cached permissions for {count} roles to Redis")


async def get_role_menu_ids(redis: Redis, role_code: str) -> list[int]:
    """从 Redis 获取角色菜单 ID 列表"""
    data = await redis.get(f"role:{role_code}:menus")
    if data:
        return json.loads(data)
    return []


async def get_role_apis(redis: Redis, role_code: str) -> list[dict]:
    """从 Redis 获取角色 API 权限列表"""
    data = await redis.get(f"role:{role_code}:apis")
    if data:
        return json.loads(data)
    return []


async def get_role_button_codes(redis: Redis, role_code: str) -> list[str]:
    """从 Redis 获取角色按钮 code 列表"""
    data = await redis.get(f"role:{role_code}:buttons")
    if data:
        return json.loads(data)
    return []


# ===================== 用户角色映射 =====================


async def load_user_roles(redis: Redis) -> None:
    """启动时将所有用户的角色编码加载到 Redis: user:{user_id}:roles → [role_code, ...]"""
    from app.system.models.admin import User

    users = await User.all().prefetch_related("by_user_roles")
    pipe = redis.pipeline()
    for user in users:
        role_codes = [r.role_code for r in user.by_user_roles]
        pipe.set(f"user:{user.id}:roles", json.dumps(role_codes))
    await pipe.execute()
    log.info(f"Loaded role mappings for {len(users)} users into Redis")


async def get_user_role_codes(redis: Redis, user_id: int) -> list[str]:
    """从 Redis 获取用户的角色 code 列表"""
    data = await redis.get(f"user:{user_id}:roles")
    if data:
        return json.loads(data)
    return []


async def get_user_button_codes(redis: Redis, user_id: int) -> list[str]:
    """从 Redis 汇总用户所有角色的按钮 code 列表"""
    role_codes = await get_user_role_codes(redis, user_id)
    button_codes: set[str] = set()
    for role_code in role_codes:
        codes = await get_role_button_codes(redis, role_code)
        button_codes.update(codes)
    return list(button_codes)


async def refresh_user_roles(redis: Redis, user_id: int) -> None:
    """刷新单个用户的角色缓存（用户角色变更时调用）"""
    from app.system.models.admin import User

    user = await User.get(id=user_id).prefetch_related("by_user_roles")
    role_codes = [r.role_code for r in user.by_user_roles]
    await redis.set(f"user:{user.id}:roles", json.dumps(role_codes))


# ===================== Token 版本号 =====================


async def load_token_versions(redis: Redis) -> None:
    """启动时将数据库中所有用户的 token_version 加载到 Redis"""
    from app.system.models.admin import User

    users = await User.all().values_list("id", "token_version")
    pipe = redis.pipeline()
    for user_id, token_version in users:
        pipe.set(f"token_version:{user_id}", token_version)
    await pipe.execute()
    log.info(f"Loaded token_version for {len(users)} users into Redis")


# ===================== 全量刷新 & 清除 =====================


async def refresh_all_cache(redis: Redis) -> None:
    """启动时刷新所有缓存数据：常量路由 + 角色权限 + token 版本号"""
    await clear_fastapi_cache(redis)
    await load_constant_routes(redis)
    await load_role_permissions(redis)
    await load_user_roles(redis)
    await load_token_versions(redis)


async def clear_fastapi_cache(redis: Redis) -> None:
    """清除 fastapi-cache2 的所有缓存"""
    cursor: int = 0
    deleted = 0
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match="fastapi-cache:*", count=200)
        if keys:
            await redis.delete(*keys)
            deleted += len(keys)
        if cursor == 0:
            break
    if deleted:
        log.info(f"Cleared {deleted} fastapi-cache2 keys from Redis")
