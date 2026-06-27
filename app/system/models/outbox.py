# pyright: reportIncompatibleVariableOverride=false
from tortoise import fields

from app.core.base_model import BaseModel


class EventOutbox(BaseModel):
    id = fields.IntField(primary_key=True, description="事件 outbox ID")
    event_name = fields.CharField(max_length=200, db_index=True, description="事件名称")
    event_version = fields.IntField(default=1, description="事件版本")
    payload = fields.JSONField(null=True, description="事件负载")
    status = fields.CharField(max_length=20, db_index=True, default="pending", description="投递状态")
    attempts = fields.IntField(default=0, description="投递尝试次数")
    next_retry_at = fields.DatetimeField(null=True, description="下次重试时间")
    locked_at = fields.DatetimeField(null=True, description="锁定时间")
    processed_at = fields.DatetimeField(null=True, description="处理完成时间")
    last_error = fields.TextField(null=True, description="最后一次错误")

    class Meta:
        table = "event_outbox"
        table_description = "事件 outbox 表"


__all__ = ["EventOutbox"]
