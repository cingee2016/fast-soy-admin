# pyright: reportIncompatibleVariableOverride=false
"""
系统字典 — 为前端下拉框、动态枚举提供可后台配置的选项数据。

字典按 ``dict_type`` 分组，每组包含多个 ``(label, value)`` 选项。
前端通过 ``GET /dictionaries/{type}/options`` 获取选项列表。

用法示例::

    # 业务模块可使用 dict_type="category"
    # 前端调用 GET /api/v1/system-manage/dictionaries/category/options
    # 返回: [{"label": "默认分类", "value": "default"}, ...]
"""

from tortoise import fields

from app.core.base_model import AuditMixin, BaseModel, StatusType


class Dictionary(BaseModel, AuditMixin):
    """系统字典项"""

    id = fields.IntField(primary_key=True)
    dict_type = fields.CharField(max_length=100, description="字典类型，如 category / status")
    label = fields.CharField(max_length=100, description="显示标签")
    value = fields.CharField(max_length=100, description="存储值")
    order = fields.IntField(default=0, description="排序")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")
    remark = fields.CharField(max_length=500, null=True, blank=True, description="备注")

    class Meta:
        table = "sys_dictionary"
        unique_together = [("dict_type", "value")]
        ordering = ["dict_type", "order", "id"]


__all__ = ["Dictionary"]
