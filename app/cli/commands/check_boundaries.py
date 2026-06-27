from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import click

PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = PROJECT_ROOT / "app"
BUSINESS_ROOT = APP_ROOT / "business"

BUSINESS_SYSTEM_ALLOWLIST = {
    "app.system.services",
    "app.system.services.init_helper",
}


@dataclass(slots=True)
class BoundaryViolation:
    path: Path
    line: int
    message: str


def _module_name_from_path(path: Path) -> str | None:
    try:
        rel = path.relative_to(BUSINESS_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    return parts[0]


def _import_roots(node: ast.AST) -> list[tuple[str, int]]:
    if isinstance(node, ast.Import):
        return [(alias.name, node.lineno) for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [(node.module, node.lineno)]
    return []


def _violations_for_file(path: Path, *, include_core: bool) -> list[BoundaryViolation]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [BoundaryViolation(path, exc.lineno or 1, f"cannot parse Python file: {exc.msg}")]

    violations: list[BoundaryViolation] = []
    business_module = _module_name_from_path(path)
    is_core = path.is_relative_to(APP_ROOT / "core")
    is_system = path.is_relative_to(APP_ROOT / "system")

    for node in ast.walk(tree):
        for imported, line in _import_roots(node):
            if is_system and imported.startswith("app.business"):
                violations.append(BoundaryViolation(path, line, "app/system must not import app.business"))

            if business_module:
                sibling_prefix = "app.business."
                if imported.startswith(sibling_prefix):
                    parts = imported.split(".")
                    if len(parts) >= 3 and parts[2] != business_module:
                        violations.append(BoundaryViolation(path, line, "business modules must not import sibling business modules"))
                if imported.startswith("app.system") and imported not in BUSINESS_SYSTEM_ALLOWLIST:
                    violations.append(BoundaryViolation(path, line, "business modules should use app.utils or approved init services instead of app.system"))

            if include_core and is_core and (imported.startswith("app.system") or imported.startswith("app.business")):
                violations.append(BoundaryViolation(path, line, "app/core should not depend on app.system or app.business"))

    return violations


def collect_boundary_violations(*, include_core: bool = False) -> list[BoundaryViolation]:
    violations: list[BoundaryViolation] = []
    for path in APP_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        violations.extend(_violations_for_file(path, include_core=include_core))
    return violations


@click.command("check-boundaries")
@click.option("--include-core", is_flag=True, help="also report historical app/core -> app/system dependencies")
def check_boundaries(include_core: bool) -> None:
    """Check import boundaries for business modules."""

    violations = collect_boundary_violations(include_core=include_core)
    if not violations:
        click.echo("Boundary check passed.")
        return

    for item in violations:
        rel = item.path.relative_to(PROJECT_ROOT).as_posix()
        click.echo(f"{rel}:{item.line}: {item.message}")
    raise click.ClickException(f"Boundary check failed: {len(violations)} violation(s)")
