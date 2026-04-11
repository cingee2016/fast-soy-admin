"""
Auto-discovery mechanism for business modules.

Scans app/business/*/ for self-contained business modules. Each module can provide:
- models.py (or models/)    → Tortoise ORM registration
- api.py (or api/)          → FastAPI routers (must export `router`)
- init_data.py              → Startup data init (must export `async def init()`)

Convention:
- Each subdirectory under app/business/ with __init__.py is a business module
- Directories starting with `_` are skipped

Example structure:
    app/business/hr/
    ├── __init__.py
    ├── config.py, ctx.py, dependency.py
    ├── models.py, schemas.py, controllers.py, services.py
    ├── init_data.py
    └── api/
        ├── __init__.py  (exports router)
        ├── manage.py
        └── my.py
"""

import importlib
from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter

# NOTE: ``app.core.log`` is imported lazily inside ``discover_business_init_data``
# to avoid a circular import (``config.py`` calls ``discover_business_models()``
# during ``Settings()`` construction, and ``log.py`` depends on ``config.py``).

BUSINESS_ROOT = Path(__file__).resolve().parent.parent / "business"


def _discover_modules() -> list[str]:
    """Find all business module names under app/business/."""
    if not BUSINESS_ROOT.exists():
        return []
    return sorted(p.name for p in BUSINESS_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "__init__.py").exists())


def discover_business_models() -> list[str]:
    """Return model module paths for Tortoise ORM registration."""
    model_modules = []
    for name in _discover_modules():
        # Support both models.py and models/ package
        if (BUSINESS_ROOT / name / "models.py").exists() or (BUSINESS_ROOT / name / "models" / "__init__.py").exists():
            model_modules.append(f"app.business.{name}.models")
    return model_modules


def discover_business_routers() -> tuple[APIRouter, list[str]]:
    """Auto-discover routers from each business module's api module.

    Returns the aggregated router and the list of discovered module names.
    """
    parent_router = APIRouter()
    names: list[str] = []
    for name in _discover_modules():
        try:
            module = importlib.import_module(f"app.business.{name}.api")
        except ImportError:
            continue
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            parent_router.include_router(router)
            names.append(name)
    return parent_router, names


def discover_business_init_data() -> list[Callable]:
    """Auto-discover init() functions from each business module's init_data module."""
    from app.core.log import log  # lazy import — see module docstring note

    init_funcs: list[Callable] = []
    for name in _discover_modules():
        try:
            module = importlib.import_module(f"app.business.{name}.init_data")
        except ImportError:
            continue
        init_fn = getattr(module, "init", None)
        if callable(init_fn):
            init_funcs.append(init_fn)
            log.debug(f"Business: found init_data for '{name}'")
    return init_funcs
