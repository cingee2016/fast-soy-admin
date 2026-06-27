"""
Business module autodiscovery.

Legacy modules are still discovered by file convention:
- models.py or models/
- api.py or api/
- init_data.py
- config.py with a DB_URL settings object

New modules may additionally expose `app/business/<name>/module.py` with
`module = BusinessModule(...)`. The manifest is preferred for runtime concerns
such as router mounting, init ordering, data policies, and future tasks/events.
Model and DB discovery deliberately stay file-convention based to avoid
environment-dependent migration drift.
"""

from __future__ import annotations

import importlib
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.core.business import BusinessModule, BusinessRouter, DataPolicy, PeriodicTask, PermissionSpec

BUSINESS_ROOT = Path(__file__).resolve().parent.parent / "business"
_ROUTE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


def _discover_modules() -> list[str]:
    """Return all enabled-by-filesystem business module directory names."""

    if not BUSINESS_ROOT.exists():
        return []
    return sorted(p.name for p in BUSINESS_ROOT.iterdir() if p.is_dir() and not p.name.startswith("_") and (p / "__init__.py").exists())


def get_disabled_business_modules() -> set[str]:
    """Return runtime-disabled modules from BUSINESS_MODULES_DISABLED.

    Runtime disable does not affect model discovery or migrations.
    """

    raw = os.getenv("BUSINESS_MODULES_DISABLED", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _load_manifest(name: str) -> BusinessModule | None:
    module_path = BUSINESS_ROOT / name / "module.py"
    if not module_path.exists():
        return None

    try:
        manifest_module = importlib.import_module(f"app.business.{name}.module")
    except Exception as exc:
        raise RuntimeError(f"Business: module '{name}' failed to import module.py: {exc}") from exc

    module = getattr(manifest_module, "module", None)
    if not isinstance(module, BusinessModule):
        raise RuntimeError(f"Business: module '{name}' module.py must export `module = BusinessModule(...)`")
    if module.name != name:
        raise RuntimeError(f"Business: module '{name}' manifest name must equal directory name, got '{module.name}'")
    return module


def _runtime_module_names(*, include_disabled: bool = False) -> list[str]:
    names = _discover_modules()
    name_set = set(names)
    disabled = get_disabled_business_modules()
    manifests = {name: _load_manifest(name) for name in names}

    for name, module in manifests.items():
        if module is None:
            continue
        for dep in module.depends_on:
            if dep not in name_set:
                raise RuntimeError(f"Business: module '{name}' depends on missing module '{dep}'")
            if dep in disabled and name not in disabled and not include_disabled:
                raise RuntimeError(f"Business: module '{name}' depends on disabled module '{dep}'")

    candidates = names if include_disabled else [name for name in names if name not in disabled]
    candidate_set = set(candidates)
    state: dict[str, str] = {}
    result: list[str] = []

    def visit(name: str, stack: list[str]) -> None:
        current = state.get(name)
        if current == "done":
            return
        if current == "visiting":
            cycle = " -> ".join([*stack, name])
            raise RuntimeError(f"Business: circular module dependency detected: {cycle}")

        state[name] = "visiting"
        module = manifests.get(name)
        for dep in module.depends_on if module else []:
            if dep in candidate_set:
                visit(dep, [*stack, name])
        state[name] = "done"
        result.append(name)

    for name in candidates:
        visit(name, [])

    return result


def discover_business_module_names() -> list[str]:
    """Return all business module names, regardless of runtime disable."""

    return _discover_modules()


def discover_business_modules(*, include_disabled: bool = False) -> list[BusinessModule]:
    """Return manifest-backed descriptors for runtime-enabled modules.

    Legacy modules are represented by a minimal BusinessModule descriptor so
    commands can list them alongside new manifest modules.
    """

    modules: list[BusinessModule] = []
    for name in _runtime_module_names(include_disabled=include_disabled):
        module = _load_manifest(name)
        if module is not None:
            modules.append(module)
            continue
        legacy = BusinessModule(name=name, title=name)
        legacy.source = "legacy"
        modules.append(legacy)
    return modules


def discover_business_models() -> list[str]:
    """Return Tortoise model module paths using the default connection."""

    model_modules = []
    for name in _discover_modules():
        if (BUSINESS_ROOT / name / "models.py").exists() or (BUSINESS_ROOT / name / "models" / "__init__.py").exists():
            model_modules.append(f"app.business.{name}.models")
    return model_modules


def discover_business_db_configs() -> dict[str, dict]:
    """Discover business modules that declare standalone database settings."""

    configs: dict[str, dict] = {}
    for name in _discover_modules():
        config_path = BUSINESS_ROOT / name / "config.py"
        if not config_path.exists():
            continue
        has_models = (BUSINESS_ROOT / name / "models.py").exists() or (BUSINESS_ROOT / name / "models" / "__init__.py").exists()
        if not has_models:
            continue

        try:
            module = importlib.import_module(f"app.business.{name}.config")
        except ImportError:
            continue

        for attr_name in dir(module):
            obj = getattr(module, attr_name, None)
            if obj is not None and hasattr(obj, "DB_URL"):
                db_url = getattr(obj, "DB_URL", None)
                if db_url:
                    configs[name] = {"db_url": db_url, "models": f"app.business.{name}.models"}
                break
    return configs


def _auth_dependencies(auth: str) -> list[Any] | None:
    if auth == "public":
        return None
    from app.core.dependency import DependAuth, DependPermission

    return [DependAuth] if auth == "auth" else [DependPermission]


def _ensure_router_has_no_module_prefix(name: str, business_router: BusinessRouter) -> None:
    module_prefix = f"/{name}"
    for route in business_router.router.routes:
        if isinstance(route, APIRoute) and (route.path == module_prefix or route.path.startswith(f"{module_prefix}/")):
            raise RuntimeError(
                f"Business: module '{name}' uses manifest mode, but router path '{route.path}' already contains the module prefix. "
                "Remove the module prefix from the business router; autodiscover adds it."
            )


def _validate_route_keys(name: str, business_router: BusinessRouter, seen: set[str]) -> None:
    if business_router.auth != "permission":
        return
    for route in business_router.router.routes:
        if not isinstance(route, APIRoute):
            continue
        route_key = route.name
        if not route_key or not _ROUTE_KEY_RE.match(route_key) or not route_key.startswith(f"{name}."):
            raise RuntimeError(f"Business: permission route '{route.path}' in module '{name}' must define APIRoute.name as '<module>.<resource>.<action>'")
        if route_key in seen:
            raise RuntimeError(f"Business: duplicate route key detected: {route_key}")
        seen.add(route_key)


def _manifest_router(name: str, module: BusinessModule, seen_route_keys: set[str]) -> APIRouter:
    parent = APIRouter()
    for business_router in module.routers:
        _ensure_router_has_no_module_prefix(name, business_router)
        _validate_route_keys(name, business_router, seen_route_keys)
        prefix = f"/{name}{business_router.prefix}"
        tags = list(business_router.tags) if business_router.tags is not None else None
        parent.include_router(
            business_router.router,
            prefix=prefix,
            tags=tags,
            dependencies=_auth_dependencies(business_router.auth),
        )
    return parent


def discover_business_routers() -> tuple[APIRouter, list[str]]:
    """Discover and aggregate business routers."""

    from app.core.log import log

    parent_router = APIRouter()
    names: list[str] = []
    seen_route_keys: set[str] = set()
    for name in _runtime_module_names():
        module = _load_manifest(name)
        if module is not None:
            router = _manifest_router(name, module, seen_route_keys)
            if router.routes:
                parent_router.include_router(router)
                names.append(name)
            continue

        module_path = BUSINESS_ROOT / name
        has_api_file = (module_path / "api.py").exists()
        has_api_pkg = (module_path / "api" / "__init__.py").exists()

        if not has_api_file and not has_api_pkg:
            log.warning(f"Business: module '{name}' discovered but has no api.py or api/ package — routes will not be registered")
            continue

        try:
            api_module = importlib.import_module(f"app.business.{name}.api")
        except ImportError:
            log.warning(f"Business: module '{name}' has api module but failed to import", exc_info=True)
            continue

        router = getattr(api_module, "router", None)
        if isinstance(router, APIRouter):
            parent_router.include_router(router)
            names.append(name)
        else:
            log.warning(f"Business: module '{name}' api module does not export a valid 'router' (APIRouter) object")
    return parent_router, names


def _init_from_permissions(spec: dict[str, Any]) -> Callable:
    async def _init() -> None:
        from app.system.services import apply_init_data

        await apply_init_data(spec)

    return _init


def discover_business_init_data() -> list[Callable]:
    """Discover business init functions in dependency order."""

    from app.core.log import log

    init_funcs: list[Callable] = []
    for name in _runtime_module_names():
        module = _load_manifest(name)
        if module is not None:
            if module.init is not None:
                init_funcs.append(module.init)
                log.debug(f"Business: found manifest init for '{name}'")
            elif module.permissions and module.permissions.init_data:
                init_funcs.append(_init_from_permissions(module.permissions.init_data))
                log.debug(f"Business: found manifest permission init for '{name}'")
            continue

        init_data_path = BUSINESS_ROOT / name / "init_data.py"
        if not init_data_path.exists():
            continue

        module_name = f"app.business.{name}.init_data"
        try:
            init_module = importlib.import_module(module_name)
        except ImportError as exc:
            message = f"Business: module '{name}' has init_data.py but failed to import: {exc}"
            log.exception(message)
            raise RuntimeError(message) from exc
        init_fn = getattr(init_module, "init", None)
        if callable(init_fn):
            init_funcs.append(init_fn)
            log.debug(f"Business: found init_data for '{name}'")
    return init_funcs


def discover_business_init_specs() -> dict[str, dict[str, Any]]:
    """Return declarative init specs exposed by manifests or legacy INIT_DATA."""

    specs: dict[str, dict[str, Any]] = {}
    for name in _runtime_module_names():
        module = _load_manifest(name)
        if module is not None:
            if module.permissions and module.permissions.init_data:
                specs[name] = module.permissions.init_data
            continue

        init_data_path = BUSINESS_ROOT / name / "init_data.py"
        if not init_data_path.exists():
            continue
        try:
            init_module = importlib.import_module(f"app.business.{name}.init_data")
        except ImportError:
            continue
        spec = getattr(init_module, "INIT_DATA", None)
        if isinstance(spec, dict):
            specs[name] = spec
    return specs


def discover_business_data_policies() -> list[DataPolicy]:
    policies: list[DataPolicy] = []
    for name in _runtime_module_names():
        module = _load_manifest(name)
        if module is not None:
            policies.extend(module.data_policies)
    return policies


def discover_business_tasks() -> list[PeriodicTask]:
    tasks: list[PeriodicTask] = []
    for name in _runtime_module_names():
        module = _load_manifest(name)
        if module is not None:
            tasks.extend(module.tasks)
    return tasks


def discover_business_permissions() -> dict[str, PermissionSpec]:
    permissions: dict[str, PermissionSpec] = {}
    for name in _runtime_module_names():
        module = _load_manifest(name)
        if module is not None and module.permissions is not None:
            permissions[name] = module.permissions
    return permissions


def discover_business_endpoint_rate_limits() -> dict[str, tuple[int, int]]:
    """Discover fastapi-guard endpoint rate limit declarations."""

    from app.core.log import log

    limits: dict[str, tuple[int, int]] = {}
    for name in _runtime_module_names():
        module_names: list[str] = []
        module_path = BUSINESS_ROOT / name
        if (module_path / "api.py").exists():
            module_names.append(f"app.business.{name}.api")
        if (module_path / "api" / "manage.py").exists():
            module_names.append(f"app.business.{name}.api.manage")
        if (module_path / "module.py").exists():
            module_names.append(f"app.business.{name}.module")

        for module_name in module_names:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                log.warning(f"Business: module '{module_name}' failed to import while collecting endpoint rate limits", exc_info=True)
                continue

            raw_limits = getattr(module, "ENDPOINT_RATE_LIMITS", None)
            if not isinstance(raw_limits, dict):
                continue
            for path, value in raw_limits.items():
                if not isinstance(path, str) or not isinstance(value, (tuple, list)) or len(value) != 2:
                    log.warning(f"Business: ignore invalid ENDPOINT_RATE_LIMITS item from '{module_name}': {path!r} -> {value!r}")
                    continue
                requests, window = value
                limits[path] = (int(requests), int(window))
    return limits
