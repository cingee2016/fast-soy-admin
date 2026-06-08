"""FastSoyAdmin CLI — 业务模块代码生成工具。"""

import click

from app.cli.commands.gen import gen
from app.cli.commands.gen_all import gen_all
from app.cli.commands.gen_web import gen_web
from app.cli.commands.init import init
from app.cli.commands.initdb import initdb
from app.cli.display import configure_output_encoding


@click.group()
def cli():
    """FastSoyAdmin 业务模块代码生成器"""
    configure_output_encoding()


cli.add_command(init)
cli.add_command(gen)
cli.add_command(gen_all, name="gen-all")
cli.add_command(gen_all, name="crud")
cli.add_command(gen_web, name="gen-web")
cli.add_command(initdb)
