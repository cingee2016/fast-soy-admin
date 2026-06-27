from __future__ import annotations

from typing import Any

import click
from fastapi.routing import APIRoute

from app.core.autodiscover import discover_business_init_specs, discover_business_module_names, discover_business_routers, get_disabled_business_modules


def _collect_menu_routes(menus: list[dict[str, Any]]) -> set[str]:
    routes: set[str] = set()
    for menu in menus:
        route_name = menu.get("route_name")
        if route_name:
            routes.add(route_name)
        routes.update(_collect_menu_routes(menu.get("children") or []))
    return routes


def _collect_button_codes(menus: list[dict[str, Any]]) -> set[str]:
    codes: set[str] = set()
    for menu in menus:
        for button in menu.get("buttons") or []:
            button_code = button.get("button_code")
            if button_code:
                codes.add(button_code)
        codes.update(_collect_button_codes(menu.get("children") or []))
    return codes


def _route_keys() -> set[str]:
    router, _ = discover_business_routers()
    return {route.name for route in router.routes if isinstance(route, APIRoute) and route.name}


def _role_route_key_refs(roles: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for role in roles:
        for api in role.get("apis") or []:
            if isinstance(api, str):
                refs.add(api)
    return refs


@click.command("init-plan")
@click.option("--strict", is_flag=True, help="发现无法解析的 route key 时返回失败")
@click.option("--apply", "apply_changes", is_flag=True, help="执行声明式 init_data upsert/reconcile")
def init_plan(strict: bool, apply_changes: bool) -> None:
    """Print a dry-run summary of business init declarations."""

    disabled = get_disabled_business_modules()
    all_modules = discover_business_module_names()
    specs = discover_business_init_specs()
    route_keys = _route_keys()
    missing_route_keys: dict[str, set[str]] = {}

    click.echo("Business init plan")
    if disabled:
        click.echo(f"Disabled modules: {', '.join(sorted(disabled))}")
    if not all_modules:
        click.echo("No business modules discovered.")
        return

    for module_name in all_modules:
        if module_name in disabled:
            click.echo(f"\n{module_name}: disabled")
            continue

        spec = specs.get(module_name)
        if not spec:
            click.echo(f"\n{module_name}: no declarative init spec")
            continue

        menus = spec.get("menus") or []
        roles = spec.get("roles") or []
        users = spec.get("users") or []
        dictionaries = spec.get("dictionaries") or []
        menu_routes = _collect_menu_routes(menus)
        button_codes = _collect_button_codes(menus)
        route_refs = _role_route_key_refs(roles)
        unresolved = route_refs - route_keys
        if unresolved:
            missing_route_keys[module_name] = unresolved

        click.echo(f"\n{module_name}:")
        click.echo(f"  menus: {len(menu_routes)}")
        click.echo(f"  buttons: {len(button_codes)}")
        click.echo(f"  roles: {len(roles)}")
        click.echo(f"  users: {len(users)}")
        click.echo(f"  dictionaries: {len(dictionaries)}")
        for route_key in sorted(unresolved):
            click.echo(f"  missing route key: {route_key}")

    if strict and missing_route_keys:
        raise click.ClickException("init-plan strict failed: unresolved route keys found")

    if apply_changes:
        import asyncio

        from tortoise import Tortoise

        from app.core.config import APP_SETTINGS
        from app.system.services import apply_init_data

        async def _apply() -> None:
            await Tortoise.init(config=APP_SETTINGS.TORTOISE_ORM)
            try:
                for module_name, spec in specs.items():
                    if module_name in disabled:
                        continue
                    await apply_init_data(spec)
            finally:
                await Tortoise.close_connections()

        asyncio.run(_apply())
        click.echo("\nApplied declarative init data.")
