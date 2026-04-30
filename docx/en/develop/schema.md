# Schema Base

Business Pydantic schemas **must not** inherit `pydantic.BaseModel` directly — inherit `SchemaBase` (`app/core/base_schema.py`) so frontend / backend field naming stays consistent.

## SchemaBase

```python
from app.utils import SchemaBase

class DepartmentCreate(SchemaBase):
    name: str
    parent_id: int | None = None
```

Key configuration:

```python
model_config = ConfigDict(
    alias_generator=to_camel_case,   # snake_case → camelCase (the wire format)
    validate_by_name=True,           # accept snake_case input (internal calls)
    validate_by_alias=True,          # accept camelCase input (frontend default)
)
```

Result:

- Python side uses `snake_case`, JSON in / out uses `camelCase`
- Always use `model_dump(by_alias=True)` when serializing manually (`Success` / `SuccessExtra` already do)

## PageQueryBase

All `POST /resources/search` bodies inherit:

```python
from app.utils import PageQueryBase

class DepartmentSearch(PageQueryBase):
    name: str | None = None
    status: str | None = None
```

Fixed fields:

| Field | Type | Default | Constraint |
|---|---|---|---|
| `current` | `int` | `1` | `≥ 1` |
| `size` | `int` | `10` | `1–1000` |
| `order_by` | `list[str] \| None` | `None` | `["-created_at", "id"]`; `None` falls back to CRUDRouter's `list_order` |

## Response wrappers

```python
from app.utils import Success, Fail, SuccessExtra, Custom
```

| Class | Default code | status_code | Purpose |
|---|---|---|---|
| `Success(data=...)` | `0000` | 200 | Single / non-paginated |
| `SuccessExtra(data={"records": [...]}, total, current, size)` | `0000` | 200 | Paginated |
| `Fail(code=Code.X, msg="...")` | `2400` | 200 | Business failure (HTTP 200, business outcome via code) |
| `Custom(code, status_code, msg, data)` | `0000` | 200 | Rare custom status_code |

These are `JSONResponse` subclasses — **return directly**:

```python
@router.get("/{id}")
async def _(id: SqidPath):
    return Success(data={"foo": "bar"})
```

::: warning No raw dicts
Raw dicts skip camelCase conversion and the unified wrapper; later wiring `response_model` will misbehave.
:::

`SuccessExtra` auto-injects `total / current / size` when `data` is a dict, so:

```python
return SuccessExtra(
    data={"records": records},
    total=total, current=obj_in.current, size=obj_in.size,
)
```

## CommonIds / OfflineByRoleRequest

Reusable utility schemas:

```python
from app.utils import CommonIds, OfflineByRoleRequest

# DELETE /resources  body: {"ids": ["sqidA", "sqidB"]}
@router.delete("/users")
async def batch_delete(obj_in: CommonIds):
    ...

# Force-logout by role
class OfflineByRoleRequest(SchemaBase):
    role_codes: list[str]
```

`CommonIds.ids` elements are typed `SqidId`, so the frontend passes sqid strings directly.

## OpenAPI response models

`Success` / `SuccessExtra` are `JSONResponse` subclasses — FastAPI can't infer the response shape for Swagger UI. To get accurate docs:

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

`ResponseModel[T]` / `PageResponseModel[T]` / `PageData[T]` are doc-only — they don't affect the actual response body.

## make_optional — derive Update from Create

Many modules' `XxxUpdate` is "all `XxxCreate` fields, but Optional". Hand-writing duplicates and drifts. Use `make_optional`:

```python
from app.utils import make_optional, SchemaBase

class EmployeeCreate(SchemaBase):
    name: str
    email: str
    department_id: int

EmployeeUpdate = make_optional(EmployeeCreate, "EmployeeUpdate")
# Equivalent to:
# class EmployeeUpdate(SchemaBase):
#     name: str | None = None
#     email: str | None = None
#     department_id: int | None = None
```

`description` / `title` are preserved.

## Raising in schemas

When a validator needs a specific business code (not Pydantic's default `1200`), use `SchemaValidationError`:

```python
from app.utils import SchemaValidationError, Code
from pydantic import field_validator

class UserCreate(SchemaBase):
    user_name: str

    @field_validator("user_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not v:
            raise SchemaValidationError(Code.USERNAME_REQUIRED, "username required")
        return v
```

`SchemaValidationError` extends `BizError` but **not** `ValueError`, so Pydantic doesn't catch it — it reaches the global `BizErrorHandle` with the original code.

## Field constraint types

```python
from app.utils import Int16, Int32, Int64, SqidId, SqidPath
```

| Alias | Equivalent | Use |
|---|---|---|
| `Int16` | `int` + `ge=-32768, le=32767` | matches `SmallIntField` |
| `Int32` | `int` + 32-bit range | matches `IntField` |
| `Int64` | `int` + 64-bit range | matches `BigIntField` |
| `SqidId` | sqid ↔ int both ways | request / response field |
| `SqidPath` | sqid → int one way | FastAPI path param |

```python
class ProductCreate(SchemaBase):
    stock: Int32 = Field(title="stock")
```

See [Sqids](/en/develop/sqids).

## See also

- [API conventions](/en/develop/api) — paths / camelCase / response format
- [Response codes](/en/reference/codes) — full `Code.*`
- [CRUDRouter](/en/develop/crud-router) — wiring schemas to routes
