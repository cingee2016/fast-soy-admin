"""gen-web 命令 — 根据 models.py 生成前端 service / typings / views / i18n。"""

from __future__ import annotations

from pathlib import Path

import click

from app.cli.display import echo_file_result, format_path, has_written_files, relative_path, run_just_format
from app.cli.options import all_choice_names, resolve_field_map
from app.cli.parser import parse_models
from app.cli.prompts import frontend_list_field_candidates, frontend_search_field_candidates, prompt_fields, prompt_model_selection, resolve_model_selection
from app.cli.web_generator import generate_web

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUSINESS_DIR = PROJECT_ROOT / "app" / "business"
WEB_ROOT = PROJECT_ROOT / "web"

GUIDE = """\

\033[1;32m✅ 前端代码生成完成！\033[0m

\033[1;33m📋 后续步骤：\033[0m

  \033[1m1.\033[0m i18n 已写入 \033[36mweb/src/locales/langs/_generated/{module}/\033[0m，
     由 \033[36mweb/src/locales/locale.ts\033[0m 通过 \033[36mimport.meta.glob\033[0m 自动合并，
     类型由同目录 \033[36mtypes.d.ts\033[0m 通过 declare 合并注入 \033[1mApp.I18n.GeneratedPages\033[0m，
     \033[2m无需手动合并到 zh-cn.ts / en-us.ts / app.d.ts。\033[0m

  \033[1m2.\033[0m 搜索生成代码中的 \033[33mTODO\033[0m 注释，补充外键 / 枚举的 options 数据源

  \033[1m3.\033[0m 启动前端验证（首次启动会自动更新 elegant-router.d.ts 的路由类型）：

     \033[36mcd web && pnpm dev\033[0m
"""


def _format_generated_files(results: list[tuple[str, str]]) -> None:
    """对生成/追加的前端文件执行项目格式化。"""
    if not has_written_files(results):
        click.echo("\n  \033[90m-\033[0m 没有新写入的前端文件，跳过格式化")
        return

    run_just_format("frontend")


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 120}


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("module_name")
@click.option("--cn-name", default=None, help="模块中文名（用于 i18n）")
@click.option("--models", "models_spec", default=None, help="要生成页面的模型，逗号分隔；支持序号、类名、all")
@click.option("-y", "--yes", "assume_yes", is_flag=True, help="不进入交互，使用全模型与默认字段")
@click.option("--list-fields", "list_field_specs", multiple=True, help="前端列表字段，例: Employee:name,tenant_id,status_type")
@click.option("--search-fields", "search_field_specs", multiple=True, help="前端搜索字段，例: Employee:name,status_type")
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
@click.option("--no-format", is_flag=True, help="跳过 just fmt frontend")
def gen_web(
    module_name: str,
    cn_name: str | None,
    models_spec: str | None,
    assume_yes: bool,
    list_field_specs: tuple[str, ...],
    search_field_specs: tuple[str, ...],
    force: bool,
    no_format: bool,
):
    """根据 models.py 生成前端代码（service / typings / views / i18n）。

    示例:

      uv run python -m app.cli gen-web hr --cn-name 人事 --yes
      uv run python -m app.cli gen-web hr --models Employee --list-fields Employee:name,status_type --search-fields Employee:name
    """
    module_dir = BUSINESS_DIR / module_name
    models_path = module_dir / "models.py"

    if not models_path.exists():
        raise click.ClickException(f"找不到 {relative_path(models_path)}\n  请先运行: uv run python -m app.cli init {module_name}")

    if not WEB_ROOT.exists():
        raise click.ClickException(f"找不到前端目录 {format_path(WEB_ROOT)}")

    # 1. 解析模型
    models = parse_models(models_path)
    if not models:
        raise click.ClickException("未在 models.py 中发现任何继承 BaseModel 的模型类")

    click.echo(f"\n  \033[1m✓\033[0m 解析模块: \033[36m{relative_path(models_path)}\033[0m")
    click.echo(f"  \033[1m✓\033[0m 发现模型: {', '.join(f'{m.name} ({m.cn_name})' for m in models)}")
    if models_spec:
        models = resolve_model_selection(models, models_spec)
        click.echo(f"  \033[1m✓\033[0m 本次生成 CRUD: {', '.join(model.name for model in models)}")
    elif assume_yes:
        click.echo(f"  \033[1m✓\033[0m 本次生成 CRUD: {', '.join(model.name for model in models)}")
    else:
        models = prompt_model_selection(models)

    # 2. 模块中文名
    module_cn: str = cn_name or (module_name if assume_yes else click.prompt("\n  模块中文名 (用于 i18n)", default=module_name))

    # 3. 列表展示字段
    if list_field_specs or assume_yes:
        list_fields = resolve_field_map(
            models,
            list_field_specs,
            frontend_list_field_candidates,
            default_names_fn=all_choice_names,
            defaults_when_missing=assume_yes,
            option_name="--list-fields",
        )
    else:
        list_fields = prompt_fields(
            models,
            "列表展示字段",
            frontend_list_field_candidates,
        )

    # 4. 搜索字段
    if search_field_specs or assume_yes:
        search_fields = resolve_field_map(
            models,
            search_field_specs,
            frontend_search_field_candidates,
            default_names_fn=all_choice_names,
            defaults_when_missing=assume_yes,
            option_name="--search-fields",
        )
    else:
        search_fields = prompt_fields(
            models,
            "搜索字段",
            frontend_search_field_candidates,
        )

    # 5. 生成
    click.echo("")
    results = generate_web(
        WEB_ROOT,
        module_name,
        module_cn,
        models,
        list_fields_map=list_fields,
        search_fields_map=search_fields,
        force=force,
    )

    for rel_path, status in results:
        echo_file_result(f"web/{rel_path}", status)

    # 6. 格式化
    if not no_format:
        _format_generated_files(results)

    click.echo(GUIDE.format(module=module_name))
