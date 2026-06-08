"""Non-interactive option parsing for CLI code generators."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import click

from app.cli.parser import FieldInfo, ModelInfo, RelationInfo
from app.cli.prompts import ChoiceInput, PromptChoice

ROUTE_NAMES = {"list", "get", "create", "update", "delete", "batch_delete"}


@dataclass(frozen=True)
class DataScopeOption:
    user_id_field: str = "user_id"
    scope_id_field: str = "scope_id"


@dataclass(frozen=True)
class BackendFeatureOptions:
    """Advanced backend features selected from CLI flags."""

    list_order: dict[str, list[str]] = field(default_factory=dict)
    enable_routes: dict[str, set[str]] = field(default_factory=dict)
    exclude_fields: dict[str, list[str]] = field(default_factory=dict)
    soft_delete_models: set[str] = field(default_factory=set)
    tree_models: set[str] = field(default_factory=set)
    button_auth_models: set[str] = field(default_factory=set)
    data_scope: dict[str, DataScopeOption] = field(default_factory=dict)
    list_cache_ttl: dict[str, int] = field(default_factory=dict)
    rate_limits: dict[str, tuple[int, int]] = field(default_factory=dict)

    def needs_list_override(self, model_name: str) -> bool:
        return model_name in self.data_scope or model_name in self.list_cache_ttl


def split_csv(raw: str) -> list[str]:
    """Split comma-like user input while accepting Chinese punctuation."""
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


def split_specs(values: Sequence[str] | None) -> list[str]:
    """Split repeated click options and semicolon-separated specs."""
    specs: list[str] = []
    for raw in values or []:
        for item in raw.replace("；", ";").split(";"):
            item = item.strip()
            if item:
                specs.append(item)
    return specs


def all_choice_names(_: ModelInfo, choices: list[PromptChoice]) -> list[str]:
    return [choice.name for choice in choices]


def _normalize_choice(choice: ChoiceInput) -> PromptChoice:
    if isinstance(choice, PromptChoice):
        return choice
    if isinstance(choice, FieldInfo):
        return PromptChoice(choice.name, choice.description or choice.name)
    if isinstance(choice, RelationInfo):
        return PromptChoice(f"{choice.name}_id", choice.description or choice.name)
    return PromptChoice(choice, choice)


def _model_lookup(models: Sequence[ModelInfo]) -> dict[str, ModelInfo]:
    lookup: dict[str, ModelInfo] = {}
    for model in models:
        aliases = {
            model.name,
            model.name.lower(),
            model.snake_name,
            model.plural_snake,
        }
        if model.table:
            aliases.add(model.table)
        for alias in aliases:
            lookup[alias] = model
    return lookup


def _resolve_model_name(token: str, models: Sequence[ModelInfo], *, option_name: str) -> str:
    lookup = _model_lookup(models)
    model = lookup.get(token) or lookup.get(token.lower())
    if model:
        return model.name
    valid = ", ".join(model.name for model in models)
    raise click.ClickException(f"{option_name}: 未找到模型 {token!r}。可选值: {valid}")


def _split_target_value(spec: str) -> tuple[str | None, str]:
    for separator in (":", "="):
        if separator in spec:
            target, value = spec.split(separator, 1)
            return target.strip() or None, value.strip()
    return None, spec.strip()


def resolve_model_set(models: Sequence[ModelInfo], values: Sequence[str] | None, *, option_name: str) -> set[str]:
    """Resolve --tree/--soft-delete style model selections."""
    tokens: list[str] = []
    for spec in split_specs(values):
        tokens.extend(split_csv(spec))

    if not tokens:
        return set()
    if any(token.lower() in {"*", "all"} for token in tokens):
        return {model.name for model in models}

    resolved: set[str] = set()
    for token in tokens:
        resolved.add(_resolve_model_name(token, models, option_name=option_name))
    return resolved


def _candidate_names(model: ModelInfo) -> set[str]:
    names = {"id", "created_at", "updated_at"}
    names.update(field.name for field in model.fields)
    names.update(f"{relation.name}_id" for relation in model.relations if relation.relation_type in ("ForeignKeyField", "OneToOneField"))
    return names


def _resolve_field_names(raw: str, choices: Sequence[PromptChoice], *, option_name: str) -> list[str]:
    if raw.strip().lower() in {"", "-", "none", "null"}:
        return []
    if raw.strip().lower() in {"*", "all"}:
        return [choice.name for choice in choices]

    aliases: dict[str, str] = {}
    for index, choice in enumerate(choices, start=1):
        aliases[str(index)] = choice.name
        aliases[choice.name] = choice.name
        aliases[choice.name.lower()] = choice.name

    result: list[str] = []
    invalid: list[str] = []
    for token in split_csv(raw):
        name = aliases.get(token) or aliases.get(token.lower())
        if not name:
            invalid.append(token)
            continue
        if name not in result:
            result.append(name)

    if invalid:
        valid = ", ".join(choice.name for choice in choices)
        raise click.ClickException(f"{option_name}: 无效字段 {', '.join(invalid)}。可选值: {valid}")
    return result


def resolve_field_map(
    models: Sequence[ModelInfo],
    values: Sequence[str] | None,
    candidates_fn: Callable[[ModelInfo], Sequence[ChoiceInput]],
    *,
    default_names_fn: Callable[[ModelInfo, list[PromptChoice]], Sequence[str]] | None = None,
    defaults_when_missing: bool = False,
    option_name: str,
) -> dict[str, list[str]]:
    """Resolve model-aware field specs such as ``Model:a,b;Other:*``."""
    result: dict[str, list[str]] = {}
    choices_by_model: dict[str, list[PromptChoice]] = {}
    model_by_name = {model.name: model for model in models}

    for model in models:
        choices = [_normalize_choice(choice) for choice in candidates_fn(model)]
        choices_by_model[model.name] = choices
        if defaults_when_missing:
            defaults = default_names_fn(model, choices) if default_names_fn else [choice.name for choice in choices]
            result[model.name] = [name for name in defaults if any(choice.name == name for choice in choices)]
        else:
            result[model.name] = []

    for spec in split_specs(values):
        target, raw_fields = _split_target_value(spec)
        if target is None:
            if len(models) == 1:
                target_names = [models[0].name]
            elif raw_fields.lower() in {"*", "all", "-", "none", "null"}:
                target_names = [model.name for model in models]
            else:
                raise click.ClickException(f"{option_name}: 多模型生成时请使用 Model:field1,field2 格式")
        elif target in {"*", "all"}:
            target_names = [model.name for model in models]
        else:
            target_names = [_resolve_model_name(target, models, option_name=option_name)]

        for model_name in target_names:
            model = model_by_name[model_name]
            result[model_name] = _resolve_field_names(raw_fields, choices_by_model[model.name], option_name=option_name)

    return result


def resolve_text_field_map(
    models: Sequence[ModelInfo],
    values: Sequence[str] | None,
    *,
    option_name: str,
    allow_route_names: bool = False,
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    model_by_name = {model.name: model for model in models}

    for spec in split_specs(values):
        target, raw_fields = _split_target_value(spec)
        if target is None:
            if len(models) != 1:
                raise click.ClickException(f"{option_name}: 多模型生成时请使用 Model:value1,value2 格式")
            target_names = [models[0].name]
        elif target in {"*", "all"}:
            target_names = [model.name for model in models]
        else:
            target_names = [_resolve_model_name(target, models, option_name=option_name)]

        for model_name in target_names:
            model = model_by_name[model_name]
            names = split_csv(raw_fields)
            if allow_route_names:
                invalid = [name for name in names if name not in ROUTE_NAMES]
                if invalid:
                    valid = ", ".join(sorted(ROUTE_NAMES))
                    raise click.ClickException(f"{option_name}: 无效路由 {', '.join(invalid)}。可选值: {valid}")
            else:
                valid_fields = _candidate_names(model)
                invalid = [name.lstrip("-") for name in names if name.lstrip("-") not in valid_fields]
                if invalid:
                    valid = ", ".join(sorted(valid_fields))
                    raise click.ClickException(f"{option_name}: {model.name} 无效字段 {', '.join(invalid)}。可选值: {valid}")
            result[model_name] = names
    return result


def resolve_data_scope_map(models: Sequence[ModelInfo], values: Sequence[str] | None) -> dict[str, DataScopeOption]:
    result: dict[str, DataScopeOption] = {}
    model_by_name = {model.name: model for model in models}
    for spec in split_specs(values):
        target, raw_fields = _split_target_value(spec)
        if target is None:
            if len(models) != 1:
                raise click.ClickException("--data-scope: 多模型生成时请使用 Model:user_id,scope_id 格式")
            target_names = [models[0].name]
        elif target in {"*", "all"}:
            target_names = [model.name for model in models]
        else:
            target_names = [_resolve_model_name(target, models, option_name="--data-scope")]

        parts = split_csv(raw_fields)
        user_id_field = parts[0] if parts else "user_id"
        scope_id_field = parts[1] if len(parts) > 1 else "scope_id"
        if len(parts) > 2:
            raise click.ClickException("--data-scope: 每个模型最多指定 user_id_field,scope_id_field 两个字段")

        for model_name in target_names:
            valid_fields = _candidate_names(model_by_name[model_name])
            invalid = [name for name in (user_id_field, scope_id_field) if name and name not in valid_fields]
            if invalid:
                valid = ", ".join(sorted(valid_fields))
                raise click.ClickException(f"--data-scope: {model_name} 无效字段 {', '.join(invalid)}。可选值: {valid}")
            result[model_name] = DataScopeOption(user_id_field=user_id_field, scope_id_field=scope_id_field)
    return result


def resolve_ttl_map(models: Sequence[ModelInfo], values: Sequence[str] | None) -> dict[str, int]:
    result: dict[str, int] = {}
    for spec in split_specs(values):
        target, raw_ttl = _split_target_value(spec)
        if target is None:
            if len(models) != 1:
                raise click.ClickException("--list-cache: 多模型生成时请使用 Model:ttl_seconds 格式")
            target_names = [models[0].name]
        elif target in {"*", "all"}:
            target_names = [model.name for model in models]
        else:
            target_names = [_resolve_model_name(target, models, option_name="--list-cache")]
        try:
            ttl = int(raw_ttl)
        except ValueError as exc:
            raise click.ClickException("--list-cache: ttl_seconds 必须是正整数") from exc
        if ttl <= 0:
            raise click.ClickException("--list-cache: ttl_seconds 必须大于 0")
        for model_name in target_names:
            result[model_name] = ttl
    return result


def resolve_rate_limit_map(models: Sequence[ModelInfo], values: Sequence[str] | None) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    for spec in split_specs(values):
        target, raw_limit = _split_target_value(spec)
        if target is None:
            if len(models) != 1:
                raise click.ClickException("--rate-limit: 多模型生成时请使用 Model:requests/window_seconds 格式")
            target_names = [models[0].name]
        elif target in {"*", "all"}:
            target_names = [model.name for model in models]
        else:
            target_names = [_resolve_model_name(target, models, option_name="--rate-limit")]

        if "/" not in raw_limit:
            raise click.ClickException("--rate-limit: 格式应为 requests/window_seconds，例如 UtilityBill:30/60")
        raw_requests, raw_window = raw_limit.split("/", 1)
        try:
            requests = int(raw_requests)
            window = int(raw_window)
        except ValueError as exc:
            raise click.ClickException("--rate-limit: requests/window_seconds 必须是正整数") from exc
        if requests <= 0 or window <= 0:
            raise click.ClickException("--rate-limit: requests/window_seconds 必须大于 0")
        for model_name in target_names:
            result[model_name] = (requests, window)
    return result


def build_backend_feature_options(
    models: Sequence[ModelInfo],
    *,
    list_order_specs: Sequence[str] | None = None,
    enable_route_specs: Sequence[str] | None = None,
    exclude_field_specs: Sequence[str] | None = None,
    soft_delete_specs: Sequence[str] | None = None,
    tree_specs: Sequence[str] | None = None,
    button_auth: bool = False,
    data_scope_specs: Sequence[str] | None = None,
    list_cache_specs: Sequence[str] | None = None,
    rate_limit_specs: Sequence[str] | None = None,
) -> BackendFeatureOptions:
    options = BackendFeatureOptions(
        list_order=resolve_text_field_map(models, list_order_specs, option_name="--list-order"),
        enable_routes={name: set(routes) for name, routes in resolve_text_field_map(models, enable_route_specs, option_name="--enable-routes", allow_route_names=True).items()},
        exclude_fields=resolve_text_field_map(models, exclude_field_specs, option_name="--exclude-fields"),
        soft_delete_models=resolve_model_set(models, soft_delete_specs, option_name="--soft-delete"),
        tree_models=resolve_model_set(models, tree_specs, option_name="--tree"),
        button_auth_models={model.name for model in models} if button_auth else set(),
        data_scope=resolve_data_scope_map(models, data_scope_specs),
        list_cache_ttl=resolve_ttl_map(models, list_cache_specs),
        rate_limits=resolve_rate_limit_map(models, rate_limit_specs),
    )
    list_override_models = set(options.data_scope) | set(options.list_cache_ttl)
    for model_name in list_override_models:
        enabled = options.enable_routes.get(model_name)
        if enabled is not None and "list" not in enabled:
            raise click.ClickException(f"{model_name} 使用了 --data-scope/--list-cache，--enable-routes 必须包含 list")
    return options
