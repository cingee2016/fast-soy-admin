"""FastSoyAdmin CLI — 业务模块代码生成工具。"""

import click

from app.cli.commands.gen import gen
from app.cli.commands.gen_all import gen_all
from app.cli.commands.gen_web import gen_web
from app.cli.commands.init import init
from app.cli.commands.initdb import initdb
from app.cli.display import configure_output_encoding

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 120}


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """FastSoyAdmin 业务模块代码生成器。

    常用:

      uv run python -m app.cli init inventory
      uv run python -m app.cli crud inventory --cn-name 库存 --yes
      uv run python -m app.cli crud inventory --models Item --contains Item:name --exact Item:status_type

    查询字段:

      --contains 适合普通 CharField/TextField 模糊查询。
      --exact 适合外键 *_id、布尔、枚举字段/枚举类、唯一字段或字典值等精确匹配字段。
    """
    configure_output_encoding()


cli.add_command(init)
cli.add_command(gen)
cli.add_command(gen_all, name="gen-all")
cli.add_command(gen_all, name="crud")
cli.add_command(gen_web, name="gen-web")
cli.add_command(initdb)
