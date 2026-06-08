"""Interactive prompts shared by CLI generators."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import click

from app.cli.parser import FieldInfo, ModelInfo, RelationInfo


@dataclass(frozen=True)
class PromptChoice:
    name: str
    description: str = ""


ChoiceInput = PromptChoice | FieldInfo | RelationInfo | str


def _split_selection(raw: str) -> list[str]:
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


def _normalize_choice(choice: ChoiceInput) -> PromptChoice:
    if isinstance(choice, PromptChoice):
        return choice
    if isinstance(choice, FieldInfo):
        return PromptChoice(choice.name, choice.description or choice.name)
    if isinstance(choice, RelationInfo):
        return PromptChoice(f"{choice.name}_id", choice.description or choice.name)
    return PromptChoice(choice, choice)


def _resolve_choice_names(raw: str, choices: Sequence[PromptChoice], *, allow_empty: bool) -> list[str]:
    if not raw.strip():
        if allow_empty:
            return []
        raise click.ClickException("至少选择一项")

    if raw.strip().lower() in {"*", "all"}:
        return [choice.name for choice in choices]

    aliases: dict[str, str] = {}
    for index, choice in enumerate(choices, start=1):
        aliases[str(index)] = choice.name
        aliases[choice.name] = choice.name
        aliases[choice.name.lower()] = choice.name

    selected: list[str] = []
    invalid: list[str] = []
    for token in _split_selection(raw):
        name = aliases.get(token) or aliases.get(token.lower())
        if not name:
            invalid.append(token)
            continue
        if name not in selected:
            selected.append(name)

    if invalid:
        valid = ", ".join(choice.name for choice in choices)
        raise click.ClickException(f"无效选择: {', '.join(invalid)}。可选值: {valid}")

    if not selected and not allow_empty:
        raise click.ClickException("至少选择一项")

    return selected


def _prompt_choice_names(
    label: str,
    choices: Sequence[PromptChoice],
    *,
    default_names: Sequence[str] | None = None,
    allow_empty: bool = True,
) -> list[str]:
    default_names = list(default_names or [])
    default_value = ",".join(default_names)

    raw = click.prompt(
        label,
        default=default_value,
        show_default=bool(default_value),
    )
    return _resolve_choice_names(raw, choices, allow_empty=allow_empty)


def _display_choices(choices: Sequence[PromptChoice]) -> str:
    return " | ".join(f"{index}.{choice.name}({choice.description or choice.name})" for index, choice in enumerate(choices, start=1))


def resolve_model_selection(models: Sequence[ModelInfo], raw: str) -> list[ModelInfo]:
    """Resolve a model selection string without prompting."""
    choices = [PromptChoice(model.name, model.cn_name) for model in models]
    selected_names = _resolve_choice_names(raw, choices, allow_empty=False)
    return [model for model in models if model.name in selected_names]


def prompt_model_selection(models: list[ModelInfo]) -> list[ModelInfo]:
    """Interactively choose which models should get CRUD code."""
    if len(models) <= 1:
        return models

    choices = [PromptChoice(model.name, f"{model.cn_name} / {model.table or model.snake_name}") for model in models]
    click.echo("")
    click.echo(f"  可生成 CRUD 的模型: {_display_choices(choices)}")
    selected_names = _prompt_choice_names(
        "  选择要生成 CRUD 的模型 (序号或类名，逗号分隔，回车全选)",
        choices,
        default_names=[choice.name for choice in choices],
        allow_empty=False,
    )
    selected = [model for model in models if model.name in selected_names]
    click.echo(f"  [ok] 本次生成 CRUD: {', '.join(model.name for model in selected)}")
    return selected


def prompt_fields(
    models: list[ModelInfo],
    label: str,
    candidates_fn: Callable[[ModelInfo], Sequence[ChoiceInput]],
    *,
    default_names_fn: Callable[[ModelInfo, list[PromptChoice]], Sequence[str]] | None = None,
) -> dict[str, list[str]]:
    """Interactively choose fields for every selected model."""
    result: dict[str, list[str]] = {}
    for model in models:
        candidates = [_normalize_choice(choice) for choice in candidates_fn(model)]
        if not candidates:
            result[model.name] = []
            continue

        defaults = list(default_names_fn(model, candidates) if default_names_fn else [choice.name for choice in candidates])
        defaults = [name for name in defaults if any(choice.name == name for choice in candidates)]

        click.echo("")
        click.echo(f"  模型 {model.name} ({model.cn_name}) 可配置的{label}: {_display_choices(candidates)}")
        result[model.name] = _prompt_choice_names(
            f"  选择{label} (序号或字段名，逗号分隔，回车使用默认值；输入空格跳过)",
            candidates,
            default_names=defaults,
            allow_empty=True,
        )
    return result


def fuzzy_field_candidates(model: ModelInfo) -> list[FieldInfo]:
    """Fields suitable for contains-based fuzzy search."""
    return [field for field in model.schema_fields if field.field_type in ("CharField", "TextField")]


def exact_field_candidates(model: ModelInfo, contains_map: dict[str, list[str]] | None = None) -> list[PromptChoice]:
    """Fields suitable for exact matching."""
    contains = set((contains_map or {}).get(model.name, []))
    choices: list[PromptChoice] = []
    skip_types = {"TextField", "JSONField"}

    for field in model.schema_fields:
        if field.name in contains or field.field_type in skip_types:
            continue
        choices.append(PromptChoice(field.name, field.description or field.name))

    for relation in model.relations:
        if relation.relation_type in ("ForeignKeyField", "OneToOneField"):
            name = f"{relation.name}_id"
            if name not in contains:
                choices.append(PromptChoice(name, relation.description or relation.name))

    return choices


def default_exact_field_names(model: ModelInfo, candidates: list[PromptChoice]) -> list[str]:
    """Recommended defaults for exact matching."""
    preferred = {"status", "status_type", "enabled", "sync_enabled"}
    fields = {field.name: field for field in model.schema_fields}
    defaults: list[str] = []
    for choice in candidates:
        field = fields.get(choice.name)
        if choice.name.endswith("_id"):
            defaults.append(choice.name)
        elif choice.name in preferred:
            defaults.append(choice.name)
        elif field and (field.enum_type or field.field_type == "BooleanField" or field.unique):
            defaults.append(choice.name)
    return defaults


def prompt_contains_fields(models: list[ModelInfo]) -> dict[str, list[str]]:
    """Choose contains-based fuzzy search fields."""
    return prompt_fields(models, "模糊查询字段", fuzzy_field_candidates)


def prompt_exact_fields(models: list[ModelInfo], contains_map: dict[str, list[str]]) -> dict[str, list[str]]:
    """Choose exact-match search fields."""
    return prompt_fields(
        models,
        "精确查询字段",
        lambda model: exact_field_candidates(model, contains_map),
        default_names_fn=default_exact_field_names,
    )


def frontend_list_field_candidates(model: ModelInfo) -> list[FieldInfo]:
    return [field for field in model.schema_fields if field.field_type not in ("TextField",)][:6]


def frontend_search_field_candidates(model: ModelInfo) -> list[FieldInfo]:
    return [field for field in model.schema_fields if field.field_type not in ("JSONField",)]


def default_frontend_search_field_names(search_maps: Sequence[dict[str, list[str]]]) -> Callable[[ModelInfo, list[PromptChoice]], Sequence[str]]:
    def default_names(model: ModelInfo, candidates: list[PromptChoice]) -> list[str]:
        candidate_names = {choice.name for choice in candidates}
        names: list[str] = []
        for search_map in search_maps:
            for name in search_map.get(model.name, []):
                if name in candidate_names and name not in names:
                    names.append(name)
        return names or [choice.name for choice in candidates if choice.name in {"status", "status_type", "enabled"}]

    return default_names
