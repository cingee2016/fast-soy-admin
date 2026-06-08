"""init 命令 — 创建业务模块目录骨架，生成初始 models.py 并输出引导提示。"""

from __future__ import annotations

import re
from pathlib import Path

import click

from app.cli.display import echo_lines, relative_path

BUSINESS_DIR = Path(__file__).resolve().parents[2] / "business"

MODELS_TEMPLATE = '''\
# pyright: reportIncompatibleVariableOverride=false
"""
{module_title} — 业务模型定义。

在此文件中定义 Tortoise ORM 模型，完成后运行:

    just cli-crud {module_name}

即可一次生成后端 schemas / controllers / api 及前端 service / views / i18n 等文件。
"""

from tortoise import fields

from app.utils import AuditMixin, BaseModel, StatusType


# ---- 在下方定义你的模型 ----
#
# class Example(BaseModel, AuditMixin):
#     """示例"""
#
#     id = fields.IntField(primary_key=True)
#     name = fields.CharField(max_length=100, description="名称")
#     status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
#
#     # 外键规范：必须在 FK 字段上方声明 <name>_id: int（非空）或 int | None（可空）
#     # 使用时创建/更新/比较一律用 parent_id，访问关系对象字段前先 prefetch_related("parent")。
#     # 关联模型字符串使用 "app_system.<Model>"（默认情况下业务模块模型都注册到 app_system）；
#     # 仅当本模块在 config.py 声明了独立 DB_URL 时，才改用 "app_{module_name}.<Model>"。
#     # parent_id: int | None
#     # parent: fields.ForeignKeyNullableRelation["Example"] = fields.ForeignKeyField(
#     #     "app_system.Example", null=True, related_name="children", description="父节点",
#     # )
#
#     class Meta:
#         table = "biz_{module_name}_example"
#         table_description = "示例"
'''


def _guide_lines(module_name: str, module_path: str, models_path: str) -> list[str]:
    return [
        "",
        f"✅ 模块 {module_name} 创建成功！",
        "",
        f"  📂 {module_path}/",
        "     - __init__.py",
        "     - models.py          <- 请在这里定义你的模型",
        "",
        "📋 下一步：",
        "",
        f"  1. 用编辑器打开 {models_path}",
        "     参照注释中的示例，定义你的 Tortoise ORM 模型。",
        "",
        "     几个要点：",
        "     - 继承 BaseModel, AuditMixin",
        '     - 每个字段加上 description="..."（用于生成 schema 注释）',
        '     - 类的 docstring 写中文名（如 """仓库"""），将作为 API summary 前缀',
        f"     - Meta.table 建议用 biz_{module_name}_xxx 前缀",
        "     - 外键字段上方必须声明 <name>_id: int（或 int | None）注解；",
        "       使用时一律用 obj.<name>_id，访问关系对象字段前先 prefetch_related(...)",
        "",
        "  2. 模型写好后，运行代码生成（后端 + 前端 CRUD 一次生成）：",
        "",
        f"     just cli-crud {module_name}",
        "",
        "     如需指定模块 i18n 中文名：",
        "",
        f"     just cli-crud {module_name} 中文名",
        "",
        "     将自动生成后端 schemas.py / controllers.py / services.py / api/，",
        "     以及前端 service / typings / views / i18n 等文件。",
        "",
        "  3. 生成后执行数据库迁移：",
        "",
        "     just mm",
        "",
        "  4. 启动服务验证：",
        "",
        "     just run",
    ]


def _validate_module_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    if not re.match(r"^[a-z][a-z0-9_]*$", value):
        raise click.BadParameter("模块名只能包含小写字母、数字和下划线，且以字母开头")
    if value.startswith("_"):
        raise click.BadParameter("以 _ 开头的目录会被 autodiscover 跳过")
    return value


@click.command()
@click.argument("module_name", callback=_validate_module_name)
@click.option("--cn-name", default=None, help="可选模块中文名（仅写入初始注释；CRUD i18n 在 cli-crud 指定）")
def init(module_name: str, cn_name: str | None):
    """创建业务模块目录骨架。

    MODULE_NAME: 模块名（snake_case），将创建到 app/business/<MODULE_NAME>/
    """
    module_dir = BUSINESS_DIR / module_name

    if module_dir.exists():
        raise click.ClickException(f"模块目录已存在: {relative_path(module_dir)}")

    # 创建目录
    module_dir.mkdir(parents=True)

    # __init__.py
    (module_dir / "__init__.py").write_text("", encoding="utf-8")

    # models.py
    models_content = MODELS_TEMPLATE.format(module_name=module_name, module_title=cn_name or module_name)
    (module_dir / "models.py").write_text(models_content, encoding="utf-8")

    # 输出引导
    echo_lines(
        _guide_lines(
            module_name=module_name,
            module_path=relative_path(module_dir),
            models_path=relative_path(module_dir / "models.py"),
        ),
    )
