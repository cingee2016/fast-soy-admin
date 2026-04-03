from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

TEST_TORTOISE_ORM = {
    "connections": {
        "conn_system": "sqlite://:memory:",
    },
    "apps": {
        "app_system": {
            "models": ["app.system.models", "app.system.radar.models", "app.business.hr.models"],
            "default_connection": "conn_system",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}


# ===================== Mock Redis =====================


class MockRedis:
    """Minimal async Redis mock for testing (no real Redis required)."""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value, *args, **kwargs):
        self._store[key] = str(value) if not isinstance(value, str) else value

    async def delete(self, *keys: str):
        for k in keys:
            self._store.pop(k, None)

    async def keys(self, pattern: str = "*") -> list[str]:
        import fnmatch

        return [k for k in self._store if fnmatch.fnmatch(k, pattern)]

    async def scan(self, cursor: int = 0, match: str | None = None, count: int | None = None) -> tuple[int, list[str]]:
        import fnmatch

        keys = [k for k in self._store if not match or fnmatch.fnmatch(k, match)]
        return (0, keys)

    def pipeline(self):
        return _MockPipeline(self)


class _MockPipeline:
    """Minimal pipeline mock — buffers set/get, executes in order."""

    def __init__(self, redis: MockRedis):
        self._redis = redis
        self._ops: list[tuple[str, tuple]] = []

    def set(self, key: str, value, *args, **kwargs):
        self._ops.append(("set", (key, str(value) if not isinstance(value, str) else value)))
        return self

    def get(self, key: str):
        self._ops.append(("get", (key,)))
        return self

    def delete(self, *keys: str):
        self._ops.append(("delete", keys))
        return self

    async def execute(self) -> list:
        results = []
        for op, args in self._ops:
            if op == "set":
                self._redis._store[args[0]] = args[1]
                results.append(True)
            elif op == "get":
                results.append(self._redis._store.get(args[0]))
            elif op == "delete":
                for k in args:
                    self._redis._store.pop(k, None)
                results.append(len(args))
        self._ops.clear()
        return results


# ===================== App Factory =====================


def _create_test_app():
    """Create a FastAPI app for testing, bypassing Redis and migrations."""
    from app.core.config import APP_SETTINGS

    APP_SETTINGS.TORTOISE_ORM = TEST_TORTOISE_ORM
    APP_SETTINGS.GUARD_ENABLED = False
    APP_SETTINGS.RADAR_ENABLED = False

    @asynccontextmanager
    async def test_lifespan(_app):
        yield

    from fastapi import FastAPI

    from app.core.init_app import make_middlewares, register_exceptions, register_routers

    _app = FastAPI(
        title=APP_SETTINGS.APP_TITLE,
        description=APP_SETTINGS.APP_DESCRIPTION,
        version=APP_SETTINGS.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=test_lifespan,
    )
    register_exceptions(_app)
    register_routers(_app, prefix="/api")

    # Business module routes
    from app.core.autodiscover import discover_business_routers

    business_router = discover_business_routers()
    if business_router.routes:
        _app.include_router(business_router, prefix="/api/v1/business")

    # Radar API routes
    from app.system.radar.api import router as radar_router

    _app.include_router(radar_router)

    return _app


# ===================== Core Fixtures =====================
# All fixtures use loop_scope="session" to share the same event loop and in-memory DB.


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def app():
    await Tortoise.init(config=TEST_TORTOISE_ORM)
    await Tortoise.generate_schemas()

    _app = _create_test_app()
    _app.state.redis = MockRedis()

    yield _app

    await Tortoise.close_connections()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def seed_data(app):
    """Seed roles and users, then populate Redis cache."""
    from app.core.cache import load_role_permissions, refresh_user_roles
    from tests.helpers import seed_roles, seed_super_admin

    await seed_roles()
    user = await seed_super_admin()

    redis = app.state.redis
    await refresh_user_roles(redis, user.id)
    await load_role_permissions(redis)

    return user


@pytest_asyncio.fixture(loop_scope="session")
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def auth_client(app, seed_data):
    """Client with valid JWT Authorization header (super admin)."""
    from datetime import UTC, datetime, timedelta

    from app.core.config import APP_SETTINGS
    from app.system.schemas.login import JWTPayload
    from app.system.security import create_access_token

    user = seed_data
    payload = JWTPayload(
        data={"userId": user.id, "userName": user.user_name, "tokenType": "accessToken"},
        iat=datetime.now(UTC),
        exp=datetime.now(UTC) + timedelta(minutes=APP_SETTINGS.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    token = create_access_token(data=payload)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


# ===================== HR Fixtures =====================


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def hr_data(app, seed_data):
    """Seed HR test data: department, skills, employee (linked to super admin)."""
    from app.business.hr.models import Department, Employee, Skill

    user = seed_data

    dept = await Department.create(name="Engineering", code="ENG", description="Engineering Department")
    skill_py = await Skill.create(name="Python", category="Language")
    skill_js = await Skill.create(name="JavaScript", category="Language")

    emp = await Employee.create(
        name=user.nick_name or "Soybean",
        employee_no="EMP0001",
        email="admin@admin.com",
        department=dept,
        user_id=user.id,
    )
    await emp.skills.add(skill_py)

    # Set employee as department manager
    await Department.filter(id=dept.id).update(manager_id=emp.id)

    return {"department": dept, "skills": [skill_py, skill_js], "employee": emp, "user": user}
