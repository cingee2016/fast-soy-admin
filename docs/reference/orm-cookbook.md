# Tortoise ORM 速查

面向日常 CRUD 的高频写法与踩坑清单。示例以 `inventory` 业务模块命名演示，并结合 `app/core/crud.py`、`app/core/cache.py` 的框架能力说明。

> 前置阅读：[外键访问规范](../standard/backend.md#外键访问规范)——`<name>_id` 同步属性 vs `<name>` 异步关系对象的区别。

## 一、一对多（ForeignKey）

### 正向：从子 → 父

```python
# models.py
class Product(BaseModel, AuditMixin):
    team_id: int
    team: fields.ForeignKeyRelation["Team"] = fields.ForeignKeyField(
        "app_system.Team", related_name="products",
    )
```

| 场景 | 写法 |
|---|---|
| 只要父 ID | `emp.team_id`（同步、零查询） |
| 要父对象的字段（单个） | `team = await emp.team` 后读 `team.name` |
| 批量列表要父字段 | `select_related("team")` 一次 JOIN 拉完，避免 N+1 |
| 按父字段过滤 | `Product.filter(team__name__icontains="技术")`（双下划线跨关系） |
| 按父 ID 过滤 | `Product.filter(team_id=1)`（**推荐**，走 FK 列，不 JOIN） |

### 反向：从父 → 子集合

`related_name="products"` 让 `Team` 拥有 `products` 反向关系（`ReverseRelation`）：

```python
# 单对象：要么 prefetch 后遍历，要么显式 all()
team = await Team.get(id=1).prefetch_related("products")
for emp in team.products:        # 已加载，同步遍历
    ...

# 不 prefetch 时必须 all()
emps = await team.products.all()

# 反向关系也能继续过滤
active = await team.products.filter(status="enable")
```

## 二、多对多（ManyToMany）

```python
# models.py
class Product(...):
    tags: fields.ManyToManyRelation["Tag"] = fields.ManyToManyField(
        "app_system.Tag", related_name="products",
    )
```

### 读

```python
# 列表查询：prefetch_related，一次拉完所有关联
total, products = await product_controller.list(
    page=1, page_size=20,
    select_related=["team"],
    prefetch_related=["tags"],
)
for emp in products:
    emp.tags  # 已加载的 list，直接遍历
    tag_ids = [t.id for t in emp.tags]

# 单对象：fetch_related 原地加载
await emp.fetch_related("team", "tags")
```

### 写：`add` / `remove` / `clear`

```python
# 追加
await emp.tags.add(tag1, tag2)

# 移除
await emp.tags.remove(tag1)

# 清空
await emp.tags.clear()

# 替换（clear-and-readd 模式，必须在事务内）
async with in_transaction(get_db_conn(Product)):
    await emp.tags.clear()
    for tid in new_tag_ids:
        await emp.tags.add(await tag_controller.get(id=tid))
```

示例：`update_product` 这类更新逻辑应优先使用 `fetch_for_update()` 或等价锁定方式处理并发写入。

### 按 M2M 过滤

```python
# 拥有某 tag 的商品
await Product.filter(tags__id=tag_id)
await Product.filter(tags__name="Python")

# 去重（否则跨 M2M JOIN 会出重复行）
from tortoise.expressions import Q
await Product.filter(tags__id__in=[1, 2, 3]).distinct()
```

## 三、Q 表达式与复杂过滤

```python
from tortoise.expressions import Q

q = Q(status="enable")
q &= Q(team_id=1)                    # AND
q |= Q(team_id=2)                    # OR
q = ~Q(deleted_at__isnull=False)           # NOT
q = Q(name__icontains="张") | Q(email__icontains="zhang")

await Product.filter(q)
```

`CRUDBase.build_search` 已经按 `contains_fields` / `exact_fields` / `range_fields` 封装了常见 `Q` 拼装，自定义 list 接口优先用它：

```python
q = product_controller.build_search(
    search_in,
    contains_fields=["name", "email"],
    exact_fields=["status"],
    range_fields=["created_at"],
)
q &= Q(team_id=search_in.team_id)
```

## 四、聚合与注解

### 内置函数

```python
from tortoise.functions import Count, Sum, Avg, Max, Min, Lower, Upper, Length, Coalesce, Trim

# 每个团队的商品数
rows = await Team.annotate(emp_count=Count("products")).values("id", "name", "emp_count")

# 字段变形
await Product.annotate(lname=Lower("name")).filter(lname__icontains="zhang")

# COALESCE 处理 null
await Product.annotate(dept_name=Coalesce("team__name", "—")).values("id", "dept_name")
```

### 聚合（不带 annotate）

```python
total = await Product.filter(status="enable").count()
max_id = await Product.all().annotate(m=Max("id")).first().values_list("m", flat=True)
```

### `values()` / `values_list()` — 跳过 ORM 对象构造

```python
# 只要几个字段，直接返回 dict / tuple，省掉对象实例化
rows = await Product.filter(status="enable").values("id", "name", "team__name")
ids = await Product.filter(status="enable").values_list("id", flat=True)
```

## 五、自定义函数 / 原生 SQL

### 通过 `Function` 子类扩展

```python
from pypika.terms import Function

class DateFormat(Function):
    def __init__(self, field, fmt):
        super().__init__("DATE_FORMAT", field, fmt)

await Product.annotate(
    ymd=DateFormat("created_at", "%Y-%m-%d"),
).values("id", "ymd")
```

### 原生 SQL 兜底

```python
from tortoise import connections

conn = connections.get(get_db_conn(Product))
# execute_query 返回 (count, rows)
count, rows = await conn.execute_query(
    "SELECT team_id, COUNT(*) c FROM biz_inventory_product WHERE status = ? GROUP BY team_id",
    ["enable"],
)
```

参数必须走占位符，**不要**字符串拼接（SQL 注入）。

## 六、事务

```python
from tortoise.transactions import in_transaction

# get_db_conn(Model) 取模型所在的连接名（系统 / 各业务模块可能分库）
async with in_transaction(get_db_conn(Product)):
    emp = await product_controller.update(id=1, obj_in=...)
    await emp.tags.clear()
    for tid in new_tag_ids:
        await emp.tags.add(await tag_controller.get(id=tid))
```

::: warning 事务内不要做 HTTP / Redis / 队列 IO
事务持有行锁，外部 IO 一旦慢或失败，锁等待会雪崩。写完 DB 再在事务外做外部副作用，或通过 [事件总线](../develop/events.md) 延迟派发。
:::

## 七、保存

### 单条

```python
# create：INSERT
emp = await Product.create(name="张三", team_id=1)

# save：INSERT 或 UPDATE（有 pk 就 UPDATE）
emp.name = "张三三"
await emp.save()

# save 只更新部分字段
await emp.save(update_fields=["name", "updated_at"])
```

### 批量

```python
# bulk_create：一条 SQL 插入多行（不会触发 save 钩子、不会回填 pk）
await Product.bulk_create([
    Product(name="a", team_id=1),
    Product(name="b", team_id=1),
])

# bulk_update：更新已有对象的指定字段
for e in products:
    e.status = "disable"
await Product.bulk_update(products, fields=["status"])
```

### upsert 模式

```python
emp, created = await Product.get_or_create(
    product_no="EMP0001",
    defaults={"name": "张三", "team_id": 1},
)

emp, created = await Product.update_or_create(
    product_no="EMP0001",
    defaults={"name": "张三三"},
)
```

## 八、性能 / 常见坑

| 症状 | 原因 | 修复 |
|---|---|---|
| 列表接口慢，看 SQL 数百条 | 循环里访问 `emp.team.xxx` 触发懒加载 | `select_related("team")` 或 `prefetch_related(...)` |
| `for m in role.by_role_menus:` 报 `TypeError: ... is not iterable` | M2M / 反向关系是 RelatedManager 不是 list | 先 `.all()` 或 `prefetch_related` |
| `await Product.create(team=other.team)` 报 TypeError | `other.team` 未 prefetch 是 coroutine | 用 `team_id=other.team_id` |
| `await emp.team` 拿到 `None` 但 FK 设了 non-null | FK 目标行被硬删或 FK 未 prefetch 之前读过一次 | 先 `await emp.fetch_related("team")` 再读 |
| 跨 M2M 过滤后行数翻倍 | M2M JOIN 天然产生重复 | 加 `.distinct()` |
| 软删的旧行和新行 `unique` 冲突 | `deleted_at IS NOT NULL` 的旧行仍占唯一约束 | PG 改部分索引，详见 [SoftDeleteMixin 陷阱](../develop/mixins.md#软删与-unique) |

## 九、配合项目的 CRUDBase

[`CRUDBase`](../develop/crud.md) 已把 `list` / `get` / `create` / `update` / `soft_remove` / `get_tree` 封装好，并透传 `select_related` / `prefetch_related`。自定义列表接口优先用它而不是手写：

```python
total, records = await product_controller.list(
    page=1, page_size=20,
    search=q,
    order=["-created_at", "id"],
    select_related=["team"],
    prefetch_related=["tags"],
)
```

参考：[`app/core/crud.py`](../../../app/core/crud.py) 的实现。

## 相关

- [后端规范 / 模型 / 外键访问](../standard/backend.md#外键访问规范)
- [CRUDBase](../develop/crud.md)
- [数据模型（System）](../develop/models.md)
- [模型 Mixin](../develop/mixins.md)
- [Sqids](../develop/sqids.md) — 主键 / 外键怎么变成 sqid
