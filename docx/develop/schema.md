# Schema 基类

业务 Pydantic schema **不要**直接继承 `pydantic.BaseModel`，应继承 [`SchemaBase`](../../../app/core/base_schema.py)，否则前后端字段命名风格会出错。

## SchemaBase

```python
from app.utils import SchemaBase

class DepartmentCreate(SchemaBase):
    name: str
    parent_id: int | None = None
```

`SchemaBase` 的关键配置：

```python
model_config = ConfigDict(
    alias_generator=to_camel_case,   # snake_case → camelCase（用作前端可见的字段名）
    validate_by_name=True,           # 也接受 snake_case 输入（兼容内部传值）
    validate_by_alias=True,          # 接受 camelCase 输入（前端默认）
)
```

效果：

- 字段在 Python 端用 `snake_case`，对 JSON 输出与输入都用 `camelCase`
- 序列化时务必 `model_dump(by_alias=True)`（`Success` / `SuccessExtra` 内部已经走 by_alias）

## PageQueryBase

所有 `POST /resources/search` 接口的 body 应继承：

```python
from app.utils import PageQueryBase

class DepartmentSearch(PageQueryBase):
    name: str | None = None
    status: str | None = None
```

固定字段：

| 字段 | 类型 | 默认 | 约束 |
|---|---|---|---|
| `current` | `int` | `1` | `≥ 1` |
| `size` | `int` | `10` | `1–1000` |
| `order_by` | `list[str] \| None` | `None` | `["-created_at", "id"]` 形式，`None` 时用 CRUDRouter 的 `list_order` |

## 响应封装

```python
from app.utils import Success, Fail, SuccessExtra, Custom
```

| 类 | 默认 code | status_code | 用途 |
|---|---|---|---|
| `Success(data=...)` | `0000` | 200 | 单条 / 无分页 |
| `SuccessExtra(data={"records": [...]}, total, current, size)` | `0000` | 200 | 分页 |
| `Fail(code=Code.X, msg="...")` | `2400` | 200 | 业务失败（HTTP 仍为 200，业务结果靠 code） |
| `Custom(code, status_code, msg, data)` | `0000` | 200 | 极少数自定义 status_code 场景 |

它们都是 `JSONResponse` 子类，**直接返回**即可：

```python
@router.get("/{id}")
async def _(id: SqidPath):
    return Success(data={"foo": "bar"})
```

::: warning 不要返回裸 dict
裸 dict 会跳过 camelCase 转换、跳过统一响应封装；后续接入 OpenAPI response_model 也会出错。
:::

`SuccessExtra` 在 `data` 是 dict 时自动注入 `total / current / size`，所以一般传 `{"records": [...]}` 即可：

```python
return SuccessExtra(
    data={"records": records},
    total=total, current=obj_in.current, size=obj_in.size,
)
```

## CommonIds / OfflineByRoleRequest

通用 schema，业务直接复用：

```python
from app.utils import CommonIds, OfflineByRoleRequest

# DELETE /resources  body: {"ids": ["sqidA", "sqidB"]}
@router.delete("/users")
async def batch_delete(obj_in: CommonIds):
    ...

# 按角色批量下线
class OfflineByRoleRequest(SchemaBase):
    role_codes: list[str]
```

`CommonIds.ids` 元素类型是 [`SqidId`](./sqids.md)，前端传 sqid 字符串即可。

## OpenAPI 响应模型

`Success` / `SuccessExtra` 是 `JSONResponse` 子类，FastAPI 默认无法在 Swagger UI 展示真实结构。需要 OpenAPI 文档准确时：

```python
from app.utils import ResponseModel, PageResponseModel

@router.get("/{id}", response_model=ResponseModel[UserOut])
async def _(id: SqidPath):
    ...
    return Success(data=user_dict)

@router.post("/search", response_model=PageResponseModel[UserOut])
async def _(obj_in: UserSearch):
    ...
    return SuccessExtra(data={"records": records}, total=total, current=..., size=...)
```

`ResponseModel[T]` / `PageResponseModel[T]` / `PageData[T]` 仅用于文档生成，**不影响**实际返回值。

## make_optional — 自动派生 Update schema

很多模块的 `XxxUpdate` 是 `XxxCreate` 所有字段都变 Optional。手写一份冗余且容易漂移。用 `make_optional`：

```python
from app.utils import make_optional, SchemaBase

class EmployeeCreate(SchemaBase):
    name: str
    email: str
    department_id: int

EmployeeUpdate = make_optional(EmployeeCreate, "EmployeeUpdate")
# 等价于:
# class EmployeeUpdate(SchemaBase):
#     name: str | None = None
#     email: str | None = None
#     department_id: int | None = None
```

`description` / `title` 会被保留。

## 在 Schema 中抛错

校验器中需要业务码（而不是 Pydantic 默认 `1200 REQUEST_VALIDATION`）时用 `SchemaValidationError`：

```python
from app.utils import SchemaValidationError, Code
from pydantic import field_validator

class UserCreate(SchemaBase):
    user_name: str

    @field_validator("user_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not v:
            raise SchemaValidationError(Code.USERNAME_REQUIRED, "用户名不能为空")
        return v
```

`SchemaValidationError` 继承 `BizError` 但不继承 `ValueError`，所以**不会被** Pydantic 当作普通校验失败捕获——会直接由全局 `BizErrorHandle` 处理，返回原始码。

## 字段约束类型

```python
from app.utils import Int16, Int32, Int64, SqidId, SqidPath
```

| 别名 | 等价 | 用途 |
|---|---|---|
| `Int16` | `int` + `ge=-32768, le=32767` | 与 `SmallIntField` 对齐 |
| `Int32` | `int` + 32 位范围 | 与 `IntField` 对齐 |
| `Int64` | `int` + 64 位范围 | 与 `BigIntField` 对齐 |
| `SqidId` | sqid ↔ int 双向编解码 | 请求 / 响应字段 |
| `SqidPath` | sqid → int 单向解码 | FastAPI 路径参数 |

```python
class ProductCreate(SchemaBase):
    stock: Int32 = Field(title="库存")
```

详见 [Sqids 资源 ID](./sqids.md)。

## 相关

- [API 约定](./api.md) — 路径 / camelCase / 响应格式
- [响应码](../reference/codes.md) — `Code.*` 全集
- [CRUDRouter](./crud-router.md) — 怎么把 schema 接到路由
