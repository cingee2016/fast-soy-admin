"""gen 命令 — 解析 models.py 并生成 schemas / controllers / api 等文件。"""

from __future__ import annotations

from pathlib import Path

import click

from app.cli.display import echo_file_result, has_written_files, relative_path, run_just_format
from app.cli.generator import generate_all
from app.cli.parser import parse_models
from app.cli.prompts import prompt_contains_fields, prompt_exact_fields, prompt_model_selection

BUSINESS_DIR = Path(__file__).resolve().parents[2] / "business"

GUIDE_TEXT = """\

\033[1;32m✅ 代码生成完成！\033[0m

\033[1;33m📋 后续步骤：\033[0m

  \033[1m1.\033[0m 按需修改 \033[36mservices.py\033[0m 中的业务逻辑
  \033[1m2.\033[0m 按需修改 \033[36minit_data.py\033[0m 添加菜单、角色、种子数据
  \033[1m3.\033[0m 执行数据库迁移：

     \033[36mjust mm\033[0m

  \033[1m4.\033[0m 启动服务验证：

     \033[36mjust run\033[0m
"""


@click.command()
@click.argument("module_name")
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
@click.option("--no-format", is_flag=True, help="跳过 just fmt backend")
def gen(module_name: str, force: bool, no_format: bool):
    """根据 models.py 生成 schemas / controllers / api 等文件。

    MODULE_NAME: 业务模块名（app/business/<MODULE_NAME>/）
    """
    module_dir = BUSINESS_DIR / module_name
    models_path = module_dir / "models.py"

    if not module_dir.exists():
        raise click.ClickException(f"模块目录不存在: {relative_path(module_dir)}\n  请先运行: uv run python -m app.cli init {module_name}")

    if not models_path.exists():
        raise click.ClickException(f"models.py 不存在: {relative_path(models_path)}")

    # 1. 解析模型
    models = parse_models(models_path)
    if not models:
        raise click.ClickException("未在 models.py 中发现任何继承 BaseModel 的模型类")

    click.echo(f"\n  \033[1m✓\033[0m 解析模块: \033[36m{relative_path(models_path)}\033[0m")
    click.echo(f"  \033[1m✓\033[0m 发现模型: {', '.join(f'{m.name} ({m.cn_name})' for m in models)}")
    models = prompt_model_selection(models)

    # 2. 交互选择搜索字段
    contains_map = prompt_contains_fields(models)
    exact_map = prompt_exact_fields(models, contains_map)

    # 3. 生成文件
    click.echo("")
    results = generate_all(module_dir, module_name, models, contains_map, exact_map=exact_map, force=force)

    for rel_path, status in results:
        echo_file_result(f"app/business/{module_name}/{rel_path}", status)

    # 4. project formatter
    if not no_format:
        if has_written_files(results):
            run_just_format("backend")
        else:
            click.echo("\n  \033[90m-\033[0m 没有新写入的后端文件，跳过格式化")

    click.echo(GUIDE_TEXT)
