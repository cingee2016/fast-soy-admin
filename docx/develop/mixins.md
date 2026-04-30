# 模型 Mixin

所有 Tortoise 模型都应继承 `BaseModel`，再按需混入下面的 Mixin。Mixin 集中在 [`app/core/base_model.py`](../../../app/core/base_model.py)、[`app/core/soft_delete.py`](../../../app/core/soft_delete.py)。

```python
# pyright: reportIncompatibleVariableOverride=false
from tortoise import fields

from app.utils import AuditMixin, BaseModel, SoftDeleteMixin, StatusType, TreeMixin


class Department(BaseModel, AuditMixin, TreeMixin, SoftDeleteMixin):
    """部门"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="部门名称")
    code = fields.CharField(max_length=50, unique=True, description="部门编号")
    status = fields.CharEnumField(enum_type=StatusType, default=StatusType.enable, description="状态")

    class Meta:
        table = "biz_hr_department"
        table_description = "部门"
```

> `# pyright: reportIncompatibleVariableOverride=false` 是 Tortoise + Pyright 已知的误报抑制，所有模型文件统一开头加这一行。

## BaseModel

`BaseModel(models.Model)` 提供 `to_dict()` —— 把模型实例转为 **camelCase** dict，自动处理：

- `datetime` → 毫秒时间戳；同时输出格式化字符串字段 `fmtCreatedAt` 等（可关）
- `Decimal` → `float`
- `Enum` → `value`
- `UUID` → `str`
- 主键和外键（`id` / `*_id`）→ **sqid 字符串**；`0`（根 / 空引用语义）保留为 `0`

```python
async def to_dict(
    self,
    include_fields: list[str] | None = None,   # 白名单
    exclude_fields: list[str] | None = None,   # 黑名单
    m2m: bool = False,                         # 是否同时序列化 M2M 关系
    fmt_datetime: bool = True,                 # 是否输出格式化时间字段
)
```

使用：

```python
data = await user.to_dict(exclude_fields=["password", "created_by", "updated_by"])
return Success(data=data)
```

> `CRUDRouter` 内部默认走 `obj.to_dict(exclude_fields=...)`，不需要业务每次手动调。

## AuditMixin

```python
created_by = CharField(max_length=64, null=True)
created_at = DatetimeField(auto_now_add=True)
updated_by = CharField(max_length=64, null=True)
updated_at = DatetimeField(auto_now=True)
```

`CRUDBase.create` / `update` / `soft_remove` 自动从 `CTX_USER_ID` 写入 `created_by` / `updated_by`（值为字符串化的 user_id）。

::: tip 系统所有持久化模型都应混入
即使是不可变种子数据（如系统字典），有审计字段在故障排查时收益巨大。
:::

## TreeMixin

```python
parent_id = IntField(default=0)   # 0 表示顶级
order     = IntField(default=0)   # 同层排序
level     = IntField(default=1)   # 冗余字段，业务侧维护
```

约定：

- `parent_id = 0` 是顶级
- `level` 不自动维护——业务侧写入时设为 `parent.level + 1`（如果用得到）
- 树形序列化用 `CRUDRouter(tree_endpoint=True)` 自动生成 `GET /resources/tree`，内部用 `_build_nested_tree(records, parent_id_key="parentId", root_value=0)`

::: warning Menu 模型不要继承 TreeMixin
`Menu` 已经有自己的 `parent_id` / `order` 字段；混入会触发 Tortoise 字段声明冲突。
:::

## SoftDeleteMixin

源码：[`app/core/soft_delete.py`](../../../app/core/soft_delete.py)。

```python
deleted_at = DatetimeField(null=True, default=None)
```

行为：

- 默认 Manager 替换为 `SoftDeleteManager`，`Model.filter()` / `.all()` / `.get()` 自动加 `deleted_at IS NULL`
- 软删除走 `controller.soft_remove(id=...)`：`UPDATE deleted_at = now()` + 同时刷新 `updated_by`
- 访问已删除行用 `Model.all_objects.filter(deleted_at__isnull=False)`

```python
# 软删除
await dept_controller.soft_remove(id=1)

# 默认查询不包含已删除
await Department.filter(name="技术部")          # deleted_at IS NULL

# 看已删除
await Department.all_objects.filter(deleted_at__isnull=False)

# 全量（含已删除）
await Department.all_objects.all()
```

### PostgreSQL 优化：部分唯一索引

`SoftDeleteMixin` 配合 `unique=True` 的字段时，**已删除的旧行**仍占用唯一约束，新建同名行会冲突。生产用 PostgreSQL 时建议替换为部分索引：

```sql
CREATE UNIQUE INDEX biz_department_code_active_uq
    ON biz_department(code)
    WHERE deleted_at IS NULL;
```

SQLite 不支持 `WHERE` 部分索引，需要在应用层（`controller.exists`）保证。

## CRUDRouter 配合

```python
CRUDRouter(
    ...,
    soft_delete=True,        # delete / batch_delete 走 soft_remove
    tree_endpoint=True,      # 注册 GET /resources/tree
)
```

## 自定义 Mixin

业务里需要重复出现的字段（如多租户 `tenant_id`）可以自己抽：

```python
class TenantMixin:
    tenant_id = fields.IntField(db_index=True, description="租户ID")

    class Meta:
        abstract = True
```

注意 `abstract = True` 否则 Tortoise 会尝试为 Mixin 单独建表。

## 相关

- [数据模型 / System](./models.md) — User / Role / Menu / Api / Button / Dictionary 完整字段
- [后端规范 / 模型 / 外键访问](../standard/backend.md#外键访问规范) — `<name>_id: int` 注解、prefetch 坑点
- [ORM 速查](../reference/orm-cookbook.md) — 一对多 / 多对多 / 聚合 / 自定义函数 / 事务
- [CRUDBase](./crud.md) — `soft_remove` / `get_tree` 等方法
- [Sqids](./sqids.md) — 主键 / 外键怎么变成 sqid
