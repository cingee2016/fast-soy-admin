from pathlib import Path

from click.testing import CliRunner

from app.cli import cli
from app.cli.display import format_path
from app.cli.generator import gen_api_manage
from app.cli.parser import parse_models
from app.cli.prompts import resolve_model_selection


def test_cli_exposes_full_crud_commands():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "crud" in result.output
    assert "gen-all" in result.output


def test_format_path_uses_forward_slashes():
    assert format_path(r"app\business\inventory\models.py") == "app/business/inventory/models.py"
    assert format_path(Path("web") / "src" / "views") == "web/src/views"


def test_parse_models_uses_first_docstring_line(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel


class InventoryItem(BaseModel):
    """库存项。

    这里是较长的业务说明，不应该进入 CLI 标题。
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="名称")

    class Meta:
        table = "biz_inventory_item"
''',
        encoding="utf-8",
    )

    [model] = parse_models(models_path)

    assert model.cn_name == "库存项"


def test_resolve_model_selection_supports_indexes_and_names(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel


class UtilityConfig(BaseModel):
    id = fields.IntField(primary_key=True)


class UtilityPrice(BaseModel):
    id = fields.IntField(primary_key=True)


class UtilityReading(BaseModel):
    id = fields.IntField(primary_key=True)
''',
        encoding="utf-8",
    )
    models = parse_models(models_path)

    selected = resolve_model_selection(models, "1,UtilityReading")

    assert [model.name for model in selected] == ["UtilityConfig", "UtilityReading"]


def test_gen_api_manage_uses_explicit_exact_fields(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel, StatusType


class UtilityPrice(BaseModel):
    """水电费单价表"""

    id = fields.IntField(primary_key=True)
    remark = fields.CharField(max_length=500, null=True, description="备注")
    enabled = fields.BooleanField(default=True, description="是否启用")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
''',
        encoding="utf-8",
    )
    [model] = parse_models(models_path)

    content = gen_api_manage(
        "utility_fee",
        [model],
        {"UtilityPrice": ["remark"]},
        {"UtilityPrice": ["enabled"]},
    )

    assert "contains_fields=['remark']" in content
    assert "exact_fields=['enabled']" in content
    assert "exact_fields=['status']" not in content
