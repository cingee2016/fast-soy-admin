from __future__ import annotations

import click

from app.core.autodiscover import discover_business_modules, get_disabled_business_modules


@click.command("module-list")
def module_list() -> None:
    """List business modules discovered by the backend."""

    disabled = get_disabled_business_modules()
    modules = discover_business_modules(include_disabled=True)
    if not modules:
        click.echo("No business modules discovered.")
        return

    for module in modules:
        status = "disabled" if module.name in disabled else "enabled"
        deps = ",".join(module.depends_on) if module.depends_on else "-"
        click.echo(
            f"{module.name}\t{status}\t{module.source}\tversion={module.version}\t"
            f"deps={deps}\trouters={len(module.routers)}\tevents={len(module.events)}\t"
            f"policies={len(module.data_policies)}\ttasks={len(module.tasks)}"
        )
