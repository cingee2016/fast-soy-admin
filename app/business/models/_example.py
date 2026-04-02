"""
Business model example.

Create your business models here. They will be auto-discovered by Tortoise ORM.
Files starting with `_` are ignored by auto-discovery.

Usage:
    1. Copy this file and rename it (e.g., order.py)
    2. Define your models using BaseModel and AuditMixin
    3. Restart the server - models are auto-registered

Example:
    from tortoise import fields
    from app.utils import AuditMixin, BaseModel

    class Order(BaseModel, AuditMixin):
        id = fields.IntField(pk=True)
        order_no = fields.CharField(max_length=64, unique=True)
        amount = fields.DecimalField(max_digits=10, decimal_places=2)
        status = fields.CharField(max_length=20, default="pending")

        class Meta:
            table = "orders"
"""
