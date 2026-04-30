# Sqids Resource IDs

Public-facing resource IDs are **sqid strings** (e.g. `Yc7vN3kE`), not raw auto-increment ints. Benefits:

- URLs don't leak ordering (blocking traffic estimation and ID-walking attacks)
- Looks like a short compact ID, friendlier than UUID
- Encoded both ways; the storage stays as `int` — no extra cost

Source: `app/core/sqids.py`, `app/core/types.py`.

## Key facts

- The alphabet is derived from `APP_SETTINGS.SECRET_KEY` (SHA-256 → seed → deterministic shuffle)
- The same `SECRET_KEY` produces the same sqid in every deployment
- Min length 8 (`_MIN_LENGTH`)
- **Rotating `SECRET_KEY` invalidates all historical sqids and all JWTs at once** — coordinate with a data migration

## API

```python
from app.utils import encode_id, decode_id

encode_id(42)         # → "Yc7vN3kE"
decode_id("Yc7vN3kE") # → 42
decode_id(42)         # → 42  (passthrough for ints, easy bidirectional support)
decode_id("foo")      # → ValueError: invalid sqid: 'foo'
```

## Pydantic field types

```python
from app.utils import SqidId, SqidPath, SchemaBase
```

| Alias | Equivalent | Use |
|---|---|---|
| `SqidId` | `int + BeforeValidator(sqid→int) + PlainSerializer(int→sqid)` | request / response field (both ways) |
| `SqidPath` | `int + BeforeValidator(sqid→int)` | FastAPI path params (input only) |

```python
class DepartmentUpdate(SchemaBase):
    parent_id: SqidId | None = None     # body field; optional

class EmployeeAssign(SchemaBase):
    employee_ids: list[SqidId]          # each item also encoded

@router.get("/departments/{item_id}")
async def _(item_id: SqidPath):         # FastAPI path param
    obj = await dept_controller.get(id=item_id)
    return Success(data=await obj.to_dict())
```

### Compatibility (numeric IDs during migration)

`_sqid_to_int` accepts int, numeric string, and sqid:

```python
def _sqid_to_int(v: Any) -> int:
    if isinstance(v, int):
        return v
    s = str(v)
    if s.lstrip("-").isdigit():     # "123" or "-1"
        return int(s)
    return decode_id(s)              # real sqid
```

Lets the frontend / legacy tests send numeric IDs during the transition. Tighten in source after migration is complete.

## Model.to_dict auto-encode

`BaseModel.to_dict()` auto-encodes PK and FK:

```python
# Raw model fields:  id=42, parent_id=10, manager_id=0, name="Engineering"
await dept.to_dict()
# →
{
  "id":         "Yc7vN3kE",
  "parentId":   "Lp7BQ9hT",
  "managerId":  0,                  # value 0 is preserved (root / empty-reference semantics)
  "name":       "Engineering",
  ...
}
```

Rules:

- Field name is `id` or ends with `_id` and the value is an int
- Value is non-zero (`0` in `TreeMixin.parent_id` means "root" — must not be encoded as a regular sqid)

## Inside controllers

`CRUDBase`'s `id: int` parameter is **always a real int** — `SqidPath` already decoded it at the route layer:

```python
@router.get("/departments/{item_id}")
async def _(item_id: SqidPath):           # item_id: int
    return Success(data=await dept_controller.get(id=item_id))
```

`CRUDRouter`'s default returns `{"createdId": encode_id(new_obj.id)}` / `{"updatedId": ...}` / `{"deletedId": ...}` are all encoded.

## When NOT to use sqids

- **Internal token / cookie / session id** — use UUID or a random string
- **Cross-service calls** — depends on the protocol; sqids are an internal convention
- **Internal DB primary keys** — still `int`; sqids only at the HTTP boundary

## Rotating SECRET_KEY

If you must rotate:

1. **Export old sqid → int mappings** if needed (business side records)
2. After rotation, all historical links / bookmarks / external sqids are invalid
3. Bump an API version and notify integrators
4. Internal code is unaffected (only stores int)

Without external stability requirements, "generate a stable SECRET_KEY at deploy and never rotate" is simpler.

## See also

- [Schema / constraint types](/en/develop/schema#field-constraint-types)
- [Mixins / BaseModel.to_dict](/en/develop/mixins#basemodel)
- [Configuration / SECRET_KEY](/en/ops/config)
