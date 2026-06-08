"""代码生成器 — 根据解析后的 ModelInfo 生成业务模块文件。"""

from __future__ import annotations

from pathlib import Path
from pprint import pformat

from app.cli.options import BackendFeatureOptions
from app.cli.parser import FieldInfo, ModelInfo, RelationInfo, collect_extra_imports

# Tortoise 整型字段 → 约束类型别名（来自 app.utils.types）
INT_FIELD_CONSTRAINT: dict[str, str] = {
    "SmallIntField": "Int16",
    "IntField": "Int32",
    "BigIntField": "Int64",
}
BUSINESS_MENU_ICON = "mdi:application-cog-outline"
BUSINESS_MODEL_ICON = "mdi:table"
UTILS_SCHEMA_ENUM_TYPES = {"DataScopeType", "StatusType"}


def _py_list(values: list[str]) -> str:
    return repr(values)


def _py_set(values: set[str]) -> str:
    if not values:
        return "set()"
    return "{" + ", ".join(repr(value) for value in sorted(values)) + "}"


def _field_type_hint(f: FieldInfo) -> str:
    """根据 Tortoise 字段类型返回带约束的 Python 类型注解字符串。

    - SmallIntField / IntField / BigIntField → Int16 / Int32 / Int64
    - CharField(max_length=N) → Annotated[str, Field(max_length=N)]
    - CharEnumField / IntEnumField → 枚举类型名（由 parser 填入 python_type）
    - 其他字段沿用 python_type
    """
    if f.enum_type:
        return f.enum_type

    constrained_int = INT_FIELD_CONSTRAINT.get(f.field_type)
    if constrained_int:
        return constrained_int

    if f.field_type == "CharField" and f.python_type == "str" and f.max_length:
        return f"Annotated[str, Field(max_length={f.max_length})]"

    return f.python_type


def _schema_field_line(f: FieldInfo, *, optional: bool = False) -> str:
    """生成单个 schema 字段行。"""
    type_hint = _field_type_hint(f)
    title = f.description or f.name

    if optional or not f.required:
        return f'{f.name}: {type_hint} | None = Field(None, title="{title}")'
    return f'{f.name}: {type_hint} = Field(title="{title}")'


def _collect_constrained_types(models: list[ModelInfo]) -> tuple[set[str], bool]:
    """扫描所有字段，返回 (需要从 app.utils 导入的整型别名集合, 是否使用 Annotated)。"""
    int_types: set[str] = set()
    needs_annotated = False
    for model in models:
        for f in model.schema_fields:
            if f.enum_type:
                continue
            if f.field_type in INT_FIELD_CONSTRAINT:
                int_types.add(INT_FIELD_CONSTRAINT[f.field_type])
            elif f.field_type == "CharField" and f.python_type == "str" and f.max_length:
                needs_annotated = True
    return int_types, needs_annotated


def _fk_schema_field(r: RelationInfo, *, optional: bool = False) -> str:
    """外键在 schema 中表示为 xxx_id: SqidId（项目统一约定，对外 ID 都是 sqid）。"""
    title = r.description or r.name
    if optional or r.nullable:
        return f'{r.name}_id: SqidId | None = Field(None, title="{title}")'
    return f'{r.name}_id: SqidId = Field(title="{title}")'


# ─── schemas.py ───


def gen_schemas(module_name: str, models: list[ModelInfo]) -> str:
    """生成 schemas.py 内容。"""
    extra_imports = collect_extra_imports(models)
    import_lines = sorted(extra_imports)

    int_types, needs_annotated = _collect_constrained_types(models)
    # 收集被引用的 enum 类型：框架内置枚举从 app.utils 导入，业务自定义枚举从本模块 models 导入。
    enum_types = {f.enum_type for m in models for f in m.schema_fields if f.enum_type}
    utils_enum_types = enum_types & UTILS_SCHEMA_ENUM_TYPES
    model_enum_types = enum_types - utils_enum_types

    lines = [
        "# pyright: reportIncompatibleVariableOverride=false",
        '"""',
        f"{module_name} — 请求/响应 Schema。",
        '"""',
        "",
    ]
    if needs_annotated:
        lines.append("from typing import Annotated")
        lines.append("")
    if import_lines:
        lines.extend(import_lines)
        lines.append("")

    utils_symbols = {"PageQueryBase", "SchemaBase"} | utils_enum_types | int_types
    has_fk = any(r.relation_type in ("ForeignKeyField", "OneToOneField") for m in models for r in m.relations)
    if has_fk:
        utils_symbols.add("SqidId")
    utils_imports = ", ".join(sorted(utils_symbols))

    lines.extend([
        "from pydantic import Field",
        "",
    ])
    if model_enum_types:
        model_enum_imports = ", ".join(sorted(model_enum_types))
        lines.append(f"from app.business.{module_name}.models import {model_enum_imports}")
    lines.extend([
        f"from app.utils import {utils_imports}",
        "",
    ])

    for model in models:
        schema_fields = model.schema_fields
        fk_relations = [r for r in model.relations if r.relation_type in ("ForeignKeyField", "OneToOneField")]

        # ---- Base ----
        lines.append(f"# {'=' * 60}")
        lines.append(f"# {model.cn_name}")
        lines.append(f"# {'=' * 60}")
        lines.append("")
        lines.append("")
        lines.append(f"class {model.name}Base(SchemaBase):")
        if schema_fields or fk_relations:
            for f in schema_fields:
                lines.append(f"    {_schema_field_line(f, optional=True)}")
            for r in fk_relations:
                lines.append(f"    {_fk_schema_field(r, optional=True)}")
        else:
            lines.append("    pass")
        lines.append("")
        lines.append("")

        # ---- Create ----
        # Create: 必填字段不再是 optional
        create_required_fields = [f for f in schema_fields if f.required]
        create_required_fks = [r for r in fk_relations if not r.nullable]
        if create_required_fields or create_required_fks:
            lines.append(f"class {model.name}Create({model.name}Base):")
            for f in create_required_fields:
                lines.append(f"    {_schema_field_line(f, optional=False)}")
            for r in create_required_fks:
                lines.append(f"    {_fk_schema_field(r, optional=False)}")
        else:
            lines.append(f"class {model.name}Create({model.name}Base):")
            lines.append("    pass")
        lines.append("")
        lines.append("")

        # ---- Update ----
        lines.append(f"class {model.name}Update({model.name}Base): ...")
        lines.append("")
        lines.append("")

        # ---- Search ----
        lines.append(f"class {model.name}Search({model.name}Base, PageQueryBase):")
        lines.append("    pass")
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ─── controllers.py ───


def gen_controllers(module_name: str, models: list[ModelInfo]) -> str:
    model_names = ", ".join(m.name for m in models)
    controller_lines = [f"{m.snake_name}_controller = CRUDBase(model={m.name})" for m in models]

    lines = [
        '"""',
        f"{module_name} controllers — 基于 CRUDBase 的控制器。",
        '"""',
        "",
        f"from app.business.{module_name}.models import {model_names}",
        "from app.utils import CRUDBase",
        "",
        *controller_lines,
        "",
    ]
    return "\n".join(lines)


# ─── services.py ───


def gen_services(module_name: str, models: list[ModelInfo]) -> str:
    controller_imports = ", ".join(f"{m.snake_name}_controller" for m in models)

    lines = [
        '"""',
        f"{module_name} services — 业务逻辑层。",
        '"""',
        "",
        f"from app.business.{module_name}.controllers import {controller_imports}  # noqa: F401",
        "",
        "",
        "# ---- 在此编写业务逻辑 ----",
        "",
    ]
    return "\n".join(lines)


# ─── api/manage.py ───


def _button_code(module_name: str, model: ModelInfo, action: str) -> str:
    module_part = module_name.replace("-", "_").upper()
    model_part = model.snake_name.upper()
    return f"B_{module_part}_{model_part}_{action}"


def _button_action_dependencies(module_name: str, model: ModelInfo) -> list[str]:
    return [
        "    action_dependencies={",
        f'        "create": [require_buttons("{_button_code(module_name, model, "CREATE")}")],',
        f'        "update": [require_buttons("{_button_code(module_name, model, "EDIT")}")],',
        f'        "delete": [require_buttons("{_button_code(module_name, model, "DELETE")}")],',
        f'        "batch_delete": [require_buttons("{_button_code(module_name, model, "DELETE")}")],',
        "    },",
    ]


def _search_config_parts(contains: list[str], exact: list[str]) -> list[str]:
    parts: list[str] = []
    if contains:
        parts.append(f"contains_fields={_py_list(contains)}")
    if exact:
        parts.append(f"exact_fields={_py_list(exact)}")
    return parts


def _append_rate_limit_hints(lines: list[str], module_name: str, models: list[ModelInfo], options: BackendFeatureOptions) -> None:
    if not options.rate_limits:
        return

    lines.append("# 启动时由 app.core.autodiscover.discover_business_endpoint_rate_limits() 自动合并到 fastapi-guard")
    lines.append("ENDPOINT_RATE_LIMITS = {")
    for model in models:
        rate = options.rate_limits.get(model.name)
        if not rate:
            continue
        requests, window = rate
        lines.append(f'    "/api/v1/business/{module_name}/{model.plural_snake}/search": ({requests}, {window}),')
    lines.append("}")
    lines.append("")


def _append_scope_id_hook(lines: list[str], options: BackendFeatureOptions) -> None:
    if not options.data_scope:
        return
    lines.extend([
        "",
        "def _get_scope_id() -> int | None:",
        '    """返回当前用户所属业务范围 ID；需要范围级数据权限时在本模块替换实现。"""',
        "    return None",
        "",
    ])


def _append_list_override(
    lines: list[str],
    module_name: str,
    model: ModelInfo,
    contains: list[str],
    exact: list[str],
    options: BackendFeatureOptions,
) -> None:
    if not options.needs_list_override(model.name):
        return

    list_order = options.list_order.get(model.name, ["id"])
    scope = options.data_scope.get(model.name)
    cache_ttl = options.list_cache_ttl.get(model.name)

    lines.append(f'@{model.snake_name}_crud.override("list")')
    if cache_ttl:
        lines.append(f'@cache(expire={cache_ttl}, namespace="{module_name}_{model.snake_name}_list")')
        if scope:
            lines.append("# 注意：该列表同时启用了 data_scope；生产前请确认缓存 key 不会跨用户复用。")
    lines.append(f"async def _list_{model.snake_name}_items(obj_in: {model.name}Search, request: Request):")
    lines.append(f"    q = {model.snake_name}_controller.build_search(")
    lines.append("        obj_in,")
    if contains:
        lines.append(f"        contains_fields={_py_list(contains)},")
    if exact:
        lines.append(f"        exact_fields={_py_list(exact)},")
    lines.append("    )")
    if scope:
        lines.extend([
            "    scope = await get_current_data_scope(request.app.state.redis)",
            "    scope_q = build_scope_filter(",
            "        scope=scope,",
            "        user_id=CTX_USER_ID.get(),",
            "        scope_id=_get_scope_id(),",
            f'        user_id_field="{scope.user_id_field}",',
            f'        scope_id_field="{scope.scope_id_field}",',
            "    )",
            "    q &= scope_q",
        ])
    lines.extend([
        '    current = getattr(obj_in, "current", 1)',
        '    size = getattr(obj_in, "size", 10)',
        f'    order = getattr(obj_in, "order_by", None) or {_py_list(list_order)}',
        f"    total, objs = await {model.snake_name}_controller.list(page=current, page_size=size, search=q, order=order)",
        "    records = [await obj.to_dict() for obj in objs]",
        '    return SuccessExtra(data={"records": records}, total=total, current=current, size=size)',
        "",
    ])


def gen_api_manage(
    module_name: str,
    models: list[ModelInfo],
    contains_map: dict[str, list[str]],
    exact_map: dict[str, list[str]] | None = None,
    *,
    backend_options: BackendFeatureOptions | None = None,
) -> str:
    backend_options = backend_options or BackendFeatureOptions()
    needs_request = any(backend_options.needs_list_override(model.name) for model in models)
    needs_scope = bool(backend_options.data_scope)
    needs_cache = bool(backend_options.list_cache_ttl)
    needs_buttons = bool(backend_options.button_auth_models)
    needs_search_config = any(contains_map.get(model.name) for model in models)
    if exact_map is None:
        needs_search_config = needs_search_config or any(any(f.enum_type or f.name == "status" for f in model.schema_fields) for model in models)
    else:
        needs_search_config = needs_search_config or any(exact_map.get(model.name) for model in models)

    fastapi_imports = ["APIRouter"]
    if needs_request:
        fastapi_imports.append("Request")

    utils_imports = ["CRUDRouter", "DependPermission"]
    if needs_search_config:
        utils_imports.append("SearchFieldConfig")
    if needs_scope:
        utils_imports.extend(["CTX_USER_ID", "SuccessExtra", "build_scope_filter"])
    if needs_buttons:
        utils_imports.append("require_buttons")

    lines = [
        '"""',
        f"{module_name} 管理接口 — CRUD。",
        '"""',
        "",
        f"from fastapi import {', '.join(fastapi_imports)}",
        "",
    ]
    if needs_cache:
        lines.extend([
            "from fastapi_cache.decorator import cache",
            "",
        ])
    if needs_scope:
        lines.extend([
            "from app.core.data_scope import get_current_data_scope",
            "",
        ])
    lines.append(f"from app.utils import {', '.join(sorted(utils_imports))}")

    # controller imports
    controller_imports = ", ".join(f"{m.snake_name}_controller" for m in models)
    lines.append(f"from app.business.{module_name}.controllers import {controller_imports}")

    # schema imports
    schema_names = []
    for m in models:
        schema_names.extend([f"{m.name}Create", f"{m.name}Update", f"{m.name}Search"])
    lines.append(f"from app.business.{module_name}.schemas import (")
    for sn in schema_names:
        lines.append(f"    {sn},")
    lines.append(")")
    lines.append("")
    _append_rate_limit_hints(lines, module_name, models, backend_options)
    _append_scope_id_hook(lines, backend_options)

    # CRUDRouter per model
    for m in models:
        contains = contains_map.get(m.name, [])
        if exact_map is None:
            # exact_fields: 有 enum_type 或 status 字段
            exact = [f.name for f in m.schema_fields if f.enum_type or f.name == "status"]
        else:
            exact = exact_map.get(m.name, [])

        search_parts = _search_config_parts(contains, exact)

        lines.append(f"{m.snake_name}_crud = CRUDRouter(")
        lines.append(f'    prefix="/{m.plural_snake}",')
        lines.append(f"    controller={m.snake_name}_controller,")
        lines.append(f"    create_schema={m.name}Create,")
        lines.append(f"    update_schema={m.name}Update,")
        lines.append(f"    list_schema={m.name}Search,")
        if search_parts:
            lines.append(f"    search_fields=SearchFieldConfig({', '.join(search_parts)}),")
        if m.name in backend_options.list_order:
            lines.append(f"    list_order={_py_list(backend_options.list_order[m.name])},")
        if m.name in backend_options.exclude_fields:
            lines.append(f"    exclude_fields={_py_list(backend_options.exclude_fields[m.name])},")
        if m.name in backend_options.enable_routes:
            lines.append(f"    enable_routes={_py_set(backend_options.enable_routes[m.name])},")
        if m.name in backend_options.soft_delete_models:
            lines.append("    soft_delete=True,")
        if m.name in backend_options.tree_models:
            lines.append("    tree_endpoint=True,")
        if m.name in backend_options.button_auth_models:
            lines.extend(_button_action_dependencies(module_name, m))
        lines.append(f'    summary_prefix="{m.cn_name}",')
        lines.append(")")
        lines.append("")
        _append_list_override(lines, module_name, m, contains, exact, backend_options)

    # router
    lines.append(f'router = APIRouter(prefix="/{module_name}", tags=["{module_name}"], dependencies=[DependPermission])')
    for m in models:
        lines.append(f"router.include_router({m.snake_name}_crud.router)")
    lines.append("")

    return "\n".join(lines)


# ─── api/__init__.py ───


def gen_api_init(module_name: str) -> str:
    lines = [
        "from fastapi import APIRouter",
        "",
        f"from app.business.{module_name}.api.manage import router as manage_router",
        "",
        "router = APIRouter()",
        "router.include_router(manage_router)",
        "",
    ]
    return "\n".join(lines)


# ─── init_data.py ───


def _route_segment(name: str) -> str:
    """Return the URL/path segment for a module or entity name."""
    return name.replace("_", "-")


def _module_route_name(module_name: str) -> str:
    """Return the Elegant Router route key for a generated module root."""
    return module_name.replace("_", "-")


def _model_route_name(module_name: str, model: ModelInfo) -> str:
    """Return the Elegant Router route key for a generated CRUD view."""
    return f"{_module_route_name(module_name)}_{_route_segment(model.snake_name)}"


def _model_route_path(module_name: str, model: ModelInfo) -> str:
    """Return the URL path for a generated CRUD view."""
    return f"/{_module_route_name(module_name)}/{_route_segment(model.snake_name)}"


def _model_button_defs(module_name: str, model: ModelInfo) -> list[dict[str, str]]:
    return [
        {"button_code": _button_code(module_name, model, "CREATE"), "button_desc": f"创建{model.cn_name}"},
        {"button_code": _button_code(module_name, model, "EDIT"), "button_desc": f"编辑{model.cn_name}"},
        {"button_code": _button_code(module_name, model, "DELETE"), "button_desc": f"删除{model.cn_name}"},
    ]


def _model_menu_children(
    module_name: str,
    models: list[ModelInfo],
    *,
    button_auth_models: set[str] | None = None,
) -> list[dict]:
    children: list[dict] = []
    button_auth_models = button_auth_models or set()
    for index, model in enumerate(models, start=1):
        route_name = _model_route_name(module_name, model)
        item = {
            "menu_name": model.cn_name,
            "route_name": route_name,
            "route_path": _model_route_path(module_name, model),
            "component": f"view.{route_name}",
            "order": index,
            "icon": BUSINESS_MODEL_ICON,
            "i18n_key": f"route.{route_name}",
        }
        if model.name in button_auth_models:
            item["buttons"] = _model_button_defs(module_name, model)
        children.append(item)
    return children


def _module_menu_tree(module_name: str, module_title: str, children: list[dict], *, reconcile_buttons: bool) -> dict:
    route_name = _module_route_name(module_name)
    return {
        "menu_name": module_title,
        "route_name": route_name,
        "route_path": f"/{route_name}",
        "order": 8,
        "icon": BUSINESS_MENU_ICON,
        "i18n_key": f"route.{route_name}",
        "reconcile": {
            "menus": True,
            # 启用 CLI --button-auth 时会同步按钮；否则保留 Web UI 中手工维护的按钮权限。
            "buttons": reconcile_buttons,
        },
        "children": children,
    }


def gen_init_data(
    module_name: str,
    models: list[ModelInfo],
    *,
    module_title: str | None = None,
    button_auth_models: set[str] | None = None,
) -> str:
    """生成 init_data.py 内容，内置业务菜单声明。"""
    button_auth_models = button_auth_models or set()
    resolved_module_title = module_title or module_name
    init_data = {
        "menus": [
            _module_menu_tree(
                module_name,
                resolved_module_title,
                _model_menu_children(module_name, models, button_auth_models=button_auth_models),
                reconcile_buttons=bool(button_auth_models),
            )
        ],
        "roles": [],
        "users": [],
        "dictionaries": [],
    }
    init_data_literal = pformat(init_data, width=120, sort_dicts=False)

    lines = [
        '"""',
        f"{module_name} 初始化数据 — 菜单、角色、种子数据。",
        "",
        "启动时由 autodiscover 自动发现并执行 init()。",
        "所有操作幂等，重复启动不会重复创建。",
        '"""',
        "",
        "from app.system.services import apply_init_data",
        "",
        f"INIT_DATA = {init_data_literal}",
        "",
        "",
        "async def init() -> None:",
        '    """模块初始化入口 — 由 autodiscover 调用。"""',
        "    await apply_init_data(INIT_DATA)",
        "    # 普通角色要看到该菜单，请在角色管理中授权，或在这里补充 _init_role_data()。",
        "    # await _init_role_data()",
        "",
    ]
    return "\n".join(lines)


# ─── __init__.py ───


def gen_module_init() -> str:
    return ""


# ─── 汇总写入 ───


ALL_FILES: dict[str, str] = {
    "schemas.py": "schemas",
    "controllers.py": "controllers",
    "services.py": "services",
    "init_data.py": "init_data",
    "api/__init__.py": "api_init",
    "api/manage.py": "api_manage",
}


def generate_all(
    module_dir: Path,
    module_name: str,
    models: list[ModelInfo],
    contains_map: dict[str, list[str]],
    *,
    exact_map: dict[str, list[str]] | None = None,
    module_title: str | None = None,
    backend_options: BackendFeatureOptions | None = None,
    skip: set[str] | None = None,
    force: bool = False,
) -> list[tuple[str, str]]:
    """生成所有文件，返回 [(相对路径, 状态)] 列表。

    状态: "created" / "skipped" (已存在)
    """
    skip = skip or set()
    backend_options = backend_options or BackendFeatureOptions()
    results: list[tuple[str, str]] = []

    generators = {
        "schemas.py": lambda: gen_schemas(module_name, models),
        "controllers.py": lambda: gen_controllers(module_name, models),
        "services.py": lambda: gen_services(module_name, models),
        "init_data.py": lambda: gen_init_data(
            module_name,
            models,
            module_title=module_title,
            button_auth_models=backend_options.button_auth_models,
        ),
        "api/__init__.py": lambda: gen_api_init(module_name),
        "api/manage.py": lambda: gen_api_manage(module_name, models, contains_map, exact_map, backend_options=backend_options),
    }

    for rel_path, gen_fn in generators.items():
        if rel_path in skip:
            results.append((rel_path, "skipped"))
            continue

        target = module_dir / rel_path
        if target.exists() and not force:
            results.append((rel_path, "exists"))
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(gen_fn(), encoding="utf-8")
        results.append((rel_path, "created"))

    return results
