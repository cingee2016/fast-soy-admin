"""gen-all / crud 命令 — 一次生成完整前后端 CRUD。"""

from __future__ import annotations

from pathlib import Path

import click

from app.cli.display import echo_file_result, format_path, has_written_files, relative_path, run_just_format
from app.cli.generator import generate_all
from app.cli.parser import parse_models
from app.cli.prompts import (
    default_frontend_search_field_names,
    frontend_list_field_candidates,
    frontend_search_field_candidates,
    prompt_contains_fields,
    prompt_exact_fields,
    prompt_fields,
    prompt_model_selection,
)
from app.cli.web_generator import generate_web

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BUSINESS_DIR = PROJECT_ROOT / "app" / "business"
WEB_ROOT = PROJECT_ROOT / "web"

GUIDE = """\

\033[1;32m✅ 前后端 CRUD 生成完成！\033[0m

\033[1;33m📋 后续步骤：\033[0m

  \033[1m1.\033[0m 搜索生成代码中的 \033[33mTODO\033[0m，补充外键 / 枚举的 options 数据源
  \033[1m2.\033[0m 按需修改 \033[36mservices.py\033[0m / \033[36minit_data.py\033[0m，补充业务逻辑、菜单、种子数据
  \033[1m3.\033[0m 执行数据库迁移：

     \033[36mjust mm\033[0m

  \033[1m4.\033[0m 启动服务验证：

     \033[36mjust run\033[0m

  \033[1m5.\033[0m 提交前运行完整质量检查：

     \033[36mjust check\033[0m
"""


def _format_generated_crud(backend_results: list[tuple[str, str]], frontend_results: list[tuple[str, str]]) -> None:
    """Format generated backend and frontend files through project recipes."""
    if has_written_files(backend_results):
        run_just_format("backend")
    else:
        click.echo("\n  \033[90m-\033[0m 没有新写入的后端文件，跳过格式化")

    if has_written_files(frontend_results):
        run_just_format("frontend")
    else:
        click.echo("\n  \033[90m-\033[0m 没有新写入的前端文件，跳过格式化")


@click.command("gen-all")
@click.argument("module_name")
@click.option("--cn-name", default=None, help="模块中文名（用于 i18n）")
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
@click.option("--no-format", is_flag=True, help="跳过 just fmt backend/frontend")
def gen_all(module_name: str, cn_name: str | None, force: bool, no_format: bool):
    """根据 models.py 一次生成后端 + 前端 CRUD 代码。"""
    module_dir = BUSINESS_DIR / module_name
    models_path = module_dir / "models.py"

    if not module_dir.exists():
        raise click.ClickException(f"模块目录不存在: {relative_path(module_dir)}\n  请先运行: uv run python -m app.cli init {module_name}")

    if not models_path.exists():
        raise click.ClickException(f"models.py 不存在: {relative_path(models_path)}")

    if not WEB_ROOT.exists():
        raise click.ClickException(f"找不到前端目录 {format_path(WEB_ROOT)}")

    models = parse_models(models_path)
    if not models:
        raise click.ClickException("未在 models.py 中发现任何继承 BaseModel 的模型类")

    click.echo(f"\n  \033[1m✓\033[0m 解析模块: \033[36m{relative_path(models_path)}\033[0m")
    click.echo(f"  \033[1m✓\033[0m 发现模型: {', '.join(f'{m.name} ({m.cn_name})' for m in models)}")
    models = prompt_model_selection(models)

    module_cn: str = cn_name or click.prompt("\n  模块中文名 (用于 i18n)", default=module_name)

    click.echo("\n\033[1m🧩 后端 CRUD 配置\033[0m")
    contains_map = prompt_contains_fields(models)
    exact_map = prompt_exact_fields(models, contains_map)

    click.echo("\n\033[1m🖥 前端 CRUD 配置\033[0m")
    list_fields = prompt_fields(
        models,
        "列表展示字段",
        frontend_list_field_candidates,
    )
    search_fields = prompt_fields(
        models,
        "搜索字段",
        frontend_search_field_candidates,
        default_names_fn=default_frontend_search_field_names([contains_map, exact_map]),
    )

    click.echo("\n\033[1m🚀 写入后端文件\033[0m")
    backend_results = generate_all(module_dir, module_name, models, contains_map, exact_map=exact_map, force=force)
    for rel_path, status in backend_results:
        echo_file_result(f"app/business/{module_name}/{rel_path}", status)

    click.echo("\n\033[1m🎛 写入前端文件\033[0m")
    frontend_results = generate_web(
        WEB_ROOT,
        module_name,
        module_cn,
        models,
        list_fields_map=list_fields,
        search_fields_map=search_fields,
        force=force,
    )
    for rel_path, status in frontend_results:
        echo_file_result(f"web/{rel_path}", status)

    if not no_format:
        _format_generated_crud(backend_results, frontend_results)

    click.echo(GUIDE)
