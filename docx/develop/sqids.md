# Sqids 资源 ID

对外暴露的资源 ID 一律是 **sqid 字符串**（如 `Yc7vN3kE`），不是数据库自增 int。这样：

- URL 不泄露顺序信息（对业务量、推算其他资源的 ID 都有阻断作用）
- 看起来像短而紧凑的 ID，比 UUID 友好
- 可编解码，本质仍是 int，不引入新的存储成本

源码：[`app/core/sqids.py`](../../../app/core/sqids.py)、[`app/core/types.py`](../../../app/core/types.py)。

## 关键事实

- 字母表由 `APP_SETTINGS.SECRET_KEY` 派生（SHA-256 → 种子 → 确定性 shuffle）
- 同一 `SECRET_KEY` 在任何部署下产出的 sqid **完全一致**
- 最短长度 8（`_MIN_LENGTH`）
- **轮换 `SECRET_KEY` 会同时使所有历史 sqid 与所有 JWT 失效**——务必和数据迁移一起规划

## API

```python
from app.utils import encode_id, decode_id

encode_id(42)         # → "Yc7vN3kE"
decode_id("Yc7vN3kE") # → 42
decode_id("foo")      # → ValueError: invalid sqid: 'foo'
```

## Pydantic 字段类型

```python
from app.utils import SqidId, SqidPath, SchemaBase
```

| 别名 | 等价 | 用途 |
|---|---|---|
| `SqidId` | `int + BeforeValidator(sqid→int) + PlainSerializer(int→sqid)` | 请求/响应字段（双向） |
| `SqidPath` | `int + BeforeValidator(sqid→int)` | FastAPI 路径参数（仅入参） |

```python
class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None     # body 字段：可选

class EmployeeAssign(SchemaBase):
    employee_ids: list[SqidId]          # 列表中的每项也走编解码

@router.get("/departments/{item_id}")
async def _(item_id: SqidPath):         # FastAPI 路径参数
    obj = await dept_controller.get(id=item_id)
    return Success(data=await obj.to_dict())
```

## Model.to_dict 自动编码

`BaseModel.to_dict()`（[源码](../../../app/core/base_model.py)）对主键和外键自动编码：

```python
# 原始模型字段:  id=42, parent_id=10, manager_id=0, name="技术部"
await dept.to_dict()
# →
{
  "id":         "Yc7vN3kE",
  "parentId":   "Lp7BQ9hT",
  "managerId":  0,                  # 注意：值为 0 不编码（保留根/空引用语义）
  "name":       "技术部",
  ...
}
```

规则：

- 字段名为 `id` 或以 `_id` 结尾且类型为 `int`
- 值非 `0`（`0` 在 `TreeMixin.parent_id` 表示根节点，业务上不能编成普通 sqid）

## 在 controller 中

`CRUDBase` 的 `id: int` 参数始终是**真整数**——`SqidPath` 在路由层已经把 sqid 解码完成。所以：

```python
@router.get("/departments/{item_id}")
async def _(item_id: SqidPath):           # item_id: int
    return Success(data=await dept_controller.get(id=item_id))
```

`CRUDRouter` 标准路由的返回值 `{"createdId": encode_id(new_obj.id)}` / `{"updatedId": ...}` / `{"deletedId": ...}` 全部走编码。

## 何时不用 sqid

- **系统内部 token / cookie / session id** — 用 UUID 或随机串
- **跨服务调用** — 看对方协议，sqid 是本系统私有约定
- **数据库内部主键** — 仍是 int，sqid 仅出现在 HTTP 边界

## 轮换 SECRET_KEY 怎么办

如果必须轮换：

1. **导出旧 sqid 与对应 int 的映射**（必要时业务侧记录）
2. 轮换 SECRET_KEY 后所有历史链接、书签、第三方持有的 sqid 都会失效
3. 对外 API 必须同时升一个版本号，告知集成方做相应迁移
4. 内部代码不受影响（永远存的是 int）

不需要外部稳定性时可"按部署生成一次稳定 SECRET_KEY 后永不轮换"。

## 相关

- [Schema 基类 / 字段约束类型](./schema.md#字段约束类型)
- [模型 Mixin / BaseModel.to_dict](./mixins.md#basemodel)
- [配置 / SECRET_KEY](../ops/config.md)
