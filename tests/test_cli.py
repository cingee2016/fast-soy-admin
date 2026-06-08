import importlib
import subprocess
from pathlib import Path

from click.testing import CliRunner

from app.cli import cli
from app.cli import display as cli_display
from app.cli.display import format_path
from app.cli.generator import gen_api_manage, gen_init_data, gen_schemas
from app.cli.parser import parse_models
from app.cli.prompts import resolve_model_selection
from app.cli.web_generator import gen_view_drawer, gen_view_search, generate_web


def test_cli_exposes_full_crud_commands():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "crud" in result.output
    assert "gen-all" in result.output


def test_cli_help_explains_backend_search_field_usage():
    result = CliRunner().invoke(cli, ["crud", "--help"])

    assert result.exit_code == 0
    assert "普通 CharField/TextField" in result.output
    assert "外键 *_id" in result.output
    assert "枚举字段/枚举类" in result.output


def test_format_path_uses_forward_slashes():
    assert format_path(r"app\business\inventory\models.py") == "app/business/inventory/models.py"
    assert format_path(Path("web") / "src" / "views") == "web/src/views"


def test_run_just_format_captures_child_output_on_success(monkeypatch, capsys):
    calls = []
    restores = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args[0], 0, stdout="child output\n", stderr="child error\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(cli_display, "restore_console_modes", lambda: restores.append(True))

    assert cli_display.run_just_format("backend") is True

    _, kwargs = calls[0]
    assert kwargs["cwd"] == cli_display.PROJECT_ROOT
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert "stdout" not in kwargs
    assert "stderr" not in kwargs
    assert restores == [True]
    output = capsys.readouterr().out
    assert "✅ just fmt backend 完成" in output
    assert "child output" not in output
    assert "child error" not in output


def test_run_just_format_prints_child_output_on_failure(monkeypatch, capsys):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="lint stdout\n", stderr="lint stderr\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(cli_display, "restore_console_modes", lambda: None)

    assert cli_display.run_just_format("frontend") is False

    captured = capsys.readouterr()
    assert "⚠️  just fmt frontend 失败" in captured.out
    assert "lint stdout" in captured.out
    assert "lint stderr" in captured.err


def test_cli_init_does_not_prompt_for_cn_name(tmp_path: Path, monkeypatch):
    init_module = importlib.import_module("app.cli.commands.init")
    monkeypatch.setattr(init_module, "BUSINESS_DIR", tmp_path)
    monkeypatch.setattr(init_module, "relative_path", lambda path: path.relative_to(tmp_path).as_posix())

    result = CliRunner().invoke(cli, ["init", "inventory"])

    assert result.exit_code == 0, result.output
    assert "模块中文名" not in result.output
    assert "\033" not in result.output
    assert "✅ 模块 inventory 创建成功！" in result.output

    models_content = (tmp_path / "inventory" / "models.py").read_text(encoding="utf-8")
    assert "inventory — 业务模型定义" in models_content
    assert "just cli-crud inventory" in models_content
    assert "just cli-crud inventory inventory" not in models_content


def test_cli_init_allows_existing_empty_module_dir(tmp_path: Path, monkeypatch):
    init_module = importlib.import_module("app.cli.commands.init")
    module_dir = tmp_path / "utility_fee2"
    (module_dir / "api" / "__pycache__").mkdir(parents=True)
    (module_dir / "api" / "__pycache__" / "manage.cpython-312.pyc").write_bytes(b"cache")
    monkeypatch.setattr(init_module, "BUSINESS_DIR", tmp_path)
    monkeypatch.setattr(init_module, "relative_path", lambda path: path.relative_to(tmp_path).as_posix())

    result = CliRunner().invoke(cli, ["init", "utility_fee2"])

    assert result.exit_code == 0, result.output
    assert (module_dir / "__init__.py").exists()
    assert (module_dir / "models.py").exists()


def test_cli_init_rejects_existing_non_empty_module_dir(tmp_path: Path, monkeypatch):
    init_module = importlib.import_module("app.cli.commands.init")
    module_dir = tmp_path / "utility_fee2" / "api"
    module_dir.mkdir(parents=True)
    (module_dir / "manage.py").write_text("existing", encoding="utf-8")
    monkeypatch.setattr(init_module, "BUSINESS_DIR", tmp_path)
    monkeypatch.setattr(init_module, "relative_path", lambda path: path.relative_to(tmp_path).as_posix())

    result = CliRunner().invoke(cli, ["init", "utility_fee2"])

    assert result.exit_code != 0
    assert "模块目录已存在: utility_fee2" in result.output
    assert (module_dir / "manage.py").read_text(encoding="utf-8") == "existing"


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
        """
from tortoise import fields

from app.utils import BaseModel


class UtilityConfig(BaseModel):
    id = fields.IntField(primary_key=True)


class UtilityPrice(BaseModel):
    id = fields.IntField(primary_key=True)


class UtilityReading(BaseModel):
    id = fields.IntField(primary_key=True)
""",
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


def test_gen_init_data_includes_business_menus(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel


class UtilityPrice(BaseModel):
    """水电费单价表"""

    id = fields.IntField(primary_key=True)
    remark = fields.CharField(max_length=500, null=True, description="备注")


class UtilityReading(BaseModel):
    """水电费读数表"""

    id = fields.IntField(primary_key=True)
    source = fields.CharField(max_length=50, description="来源")
''',
        encoding="utf-8",
    )
    models = parse_models(models_path)

    content = gen_init_data("utility_fee2", models, module_title="水电费2")

    compile(content, "init_data.py", "exec")
    assert "from app.system.services import apply_init_data" in content
    assert "INIT_DATA = {'menus':" in content
    assert "'menu_name': '水电费2'" in content
    assert "'route_name': 'utility-fee2'" in content
    assert "'route_name': 'utility-fee2_utility-price'" in content
    assert "'route_path': '/utility-fee2/utility-price'" in content
    assert "'component': 'view.utility-fee2_utility-price'" in content
    assert "'i18n_key': 'route.utility-fee2_utility-price'" in content
    assert "'reconcile': {'menus': True, 'buttons': False}" in content
    assert "await apply_init_data(INIT_DATA)" in content
    assert "await ensure_menu(**_build_menu_tree())" not in content
    assert 'parent_route = "_".join(parts[:level])' not in content
    assert "\\" not in content

    content_with_buttons = gen_init_data("utility_fee2", models, module_title="水电费2", button_auth_models={"UtilityPrice"})
    assert "'reconcile': {'menus': True, 'buttons': True}" in content_with_buttons
    assert "'button_code': 'B_UTILITY_FEE2_UTILITY_PRICE_CREATE'" in content_with_buttons
    assert "'button_desc': '创建水电费单价表'" in content_with_buttons


def test_generate_web_uses_elegant_router_official_route_keys(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel


class UtilityPrice(BaseModel):
    """水电费单价表"""

    id = fields.IntField(primary_key=True)
    remark = fields.CharField(max_length=500, null=True, description="备注")
''',
        encoding="utf-8",
    )
    [model] = parse_models(models_path)
    web_root = tmp_path / "web"
    (web_root / "src" / "service" / "api").mkdir(parents=True)
    (web_root / "src" / "service" / "api" / "index.ts").write_text("", encoding="utf-8")

    results = generate_web(
        web_root,
        "utility_fee2",
        "水电费2",
        [model],
        list_fields_map={"UtilityPrice": ["remark"]},
        search_fields_map={},
    )

    created_paths = {path for path, status in results if status == "created"}
    assert "src/views/utility-fee2/utility-price/index.vue" in created_paths
    assert "src/views/utility-fee2/utility-price/modules/utility-price-search.vue" in created_paths

    zh_content = (web_root / "src" / "locales" / "langs" / "_generated" / "utility_fee2" / "zh-cn.ts").read_text(encoding="utf-8")
    assert "'utility-fee2': '水电费2'" in zh_content
    assert "'utility-fee2_utility-price': '水电费单价表'" in zh_content


def test_gen_schemas_imports_custom_enums_from_business_models(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel, StatusType, StrEnum


class ReadingSource(StrEnum):
    external = "external"
    manual = "manual"


class UtilityReading(BaseModel):
    """水电费读数表"""

    id = fields.IntField(primary_key=True)
    source = fields.CharEnumField(enum_type=ReadingSource, default=ReadingSource.external, description="来源")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
''',
        encoding="utf-8",
    )
    models = parse_models(models_path)

    content = gen_schemas("utility_fee", models)

    utils_import = next(line for line in content.splitlines() if line.startswith("from app.utils import"))
    assert "from app.business.utility_fee.models import ReadingSource" in content
    assert "StatusType" in utils_import
    assert "ReadingSource" not in utils_import


def test_gen_view_drawer_skips_unused_form_rules_for_optional_models(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel


class UtilityConfig(BaseModel):
    """水电费配置表"""

    id = fields.IntField(primary_key=True)
    external_token = fields.TextField(null=True, description="外部接口 token")
    sync_enabled = fields.BooleanField(default=True, description="是否开启自动同步")
''',
        encoding="utf-8",
    )
    [model] = parse_models(models_path)

    content = gen_view_drawer("utility_fee", model)

    assert "useFormRules" not in content
    assert "defaultRequiredRule" not in content
    assert "const rules: Record<string, App.Global.FormRule> = {};" in content
    assert ':value="Boolean(model.syncEnabled)"' in content


def test_gen_frontend_controls_are_typecheck_friendly(tmp_path: Path):
    models_path = tmp_path / "models.py"
    models_path.write_text(
        '''
from tortoise import fields

from app.utils import BaseModel


class UtilityReading(BaseModel):
    """水电费读数表"""

    id = fields.IntField(primary_key=True)
    reading_time = fields.DatetimeField(description="读数时间")
    enabled = fields.BooleanField(default=True, description="是否启用")
    raw_data = fields.JSONField(null=True, description="原始数据")
''',
        encoding="utf-8",
    )
    [model] = parse_models(models_path)

    drawer = gen_view_drawer("utility_fee", model)
    search = gen_view_search("utility_fee", model, ["enabled"])

    assert 'v-model:formatted-value="model.readingTime"' in drawer
    assert 'value-format="yyyy-MM-dd HH:mm:ss"' in drawer
    assert "readingTime: null" in drawer
    assert "formatJsonInput(model.rawData)" in drawer
    assert "model.rawData = parseJsonInput(value)" in drawer
    assert ':value="model.enabled as any"' in search
    assert "value => (model.enabled = value as boolean | null)" in search
