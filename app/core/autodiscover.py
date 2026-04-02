"""
Auto-discovery mechanism for business modules.

Automatically discovers and registers:
- Business models (for Tortoise ORM)
- Business API routers (for FastAPI)

Convention:
- Business models go in app/business/models/
- Business API routes go in app/business/api/
- Each API module should export a `router` variable (FastAPI APIRouter)
- Files starting with `_` are skipped (e.g., _example.py)
"""

import importlib
import pkgutil
from pathlib import Path

from fastapi import APIRouter

BUSINESS_ROOT = Path(__file__).resolve().parent.parent / "business"


def discover_business_models() -> list[str]:
    """Return model module paths for Tortoise ORM registration."""
    models_path = BUSINESS_ROOT / "models"
    if not models_path.exists():
        return []
    # Check if there are any non-underscore .py files besides __init__.py
    py_files = [f for f in models_path.glob("*.py") if f.stem != "__init__" and not f.stem.startswith("_")]
    if not py_files:
        return []
    return ["app.business.models"]


def discover_business_routers() -> APIRouter:
    """Auto-discover all routers in app/business/api/ and merge into one."""
    parent_router = APIRouter()
    api_path = BUSINESS_ROOT / "api"
    if not api_path.exists():
        return parent_router

    package = "app.business.api"
    for _, modname, _ in pkgutil.iter_modules([str(api_path)]):
        if modname.startswith("_"):
            continue
        module = importlib.import_module(f"{package}.{modname}")
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            parent_router.include_router(router)
    return parent_router
