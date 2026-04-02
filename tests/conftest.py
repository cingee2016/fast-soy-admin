from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

TEST_TORTOISE_ORM = {
    "connections": {
        "conn_system": "sqlite://:memory:",
    },
    "apps": {
        "app_system": {
            "models": ["app.models.system", "app.radar.models"],
            "default_connection": "conn_system",
        }
    },
    "use_tz": False,
    "timezone": "Asia/Shanghai",
}


def _create_test_app():
    """Create a FastAPI app for testing, bypassing Redis and migrations."""
    from app.settings import APP_SETTINGS

    APP_SETTINGS.TORTOISE_ORM = TEST_TORTOISE_ORM

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

    from app.radar.api import router as radar_router

    _app.include_router(radar_router)

    return _app


@pytest.fixture(scope="session")
async def app():
    await Tortoise.init(config=TEST_TORTOISE_ORM)
    await Tortoise.generate_schemas()

    _app = _create_test_app()

    yield _app

    await Tortoise.close_connections()


@pytest.fixture(scope="session")
async def seed_data(app):
    """Seed roles and users for testing. Depends on app to ensure DB is initialized."""
    from tests.helpers import seed_roles, seed_super_admin

    await seed_roles()
    user = await seed_super_admin()
    return user


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.fixture
async def auth_client(app, seed_data):
    """Client with valid JWT Authorization header (super admin)."""
    from datetime import UTC, datetime, timedelta

    from app.schemas.login import JWTPayload
    from app.settings import APP_SETTINGS
    from app.utils.security import create_access_token

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
