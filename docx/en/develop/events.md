# Event Bus

In-process event bus for **decoupled communication between business modules**. Per the rule "system doesn't know business; business modules don't know each other", cross-module wiring must go through this bus.

Source: `app/core/events.py`.

## Design

- **Same process**: dispatched within the current worker only; no cross-process / cross-service delivery (that's a message queue's job)
- **Sequential**: `emit` awaits handlers in registration order — easy to debug
- **Failure-isolated**: a handler exception is caught with `log.exception`; later handlers still run
- **Register on import**: `@on` adds the handler at module-import time, so a module containing `@on` must actually be imported (typically from `__init__.py`)

## Register handlers

```python
# app/business/notify/events.py
from app.utils import emit, on


@on("employee.created")
async def _send_welcome_mail(employee_id: int, **kwargs):
    # Handlers should accept **kwargs so emitters can extend later
    ...


@on("employee.status_changed")
async def _audit_state(employee_id: int, from_state: str, to_state: str, **kwargs):
    ...
```

Make sure the module gets loaded:

```python
# app/business/notify/__init__.py
from . import events  # noqa: F401  ← triggers @on registration
```

## Emit events

```python
# app/business/hr/services.py
from app.utils import emit

await emit("employee.created", employee_id=new_emp.id, department_id=dept.id)
```

All kwargs are passed through to handlers.

## Naming convention

```
<aggregate>.<verb>
```

| Recommended | Avoid |
|---|---|
| `employee.created` | `EmployeeCreated` |
| `employee.status_changed` | `change_employee_status_done` |
| `order.refunded` | `RefundOrder` |

Event names are a contract — **don't rename** once published; invisible handlers depend on them.

## Sync handlers

Sync functions are accepted but discouraged:

```python
@on("user.logged_in")
def _log_login(user_id: int, **kwargs):
    print(f"user {user_id} logged in")
```

`emit` checks `inspect.iscoroutinefunction`; sync handlers are called directly and will block the event loop. **Use only when truly no IO**.

## Failure semantics

```python
@on("employee.created")
async def _flaky_handler(employee_id: int, **kwargs):
    raise RuntimeError("oops")
```

`emit` doesn't re-raise — it logs `Event handler error: employee.created / module._flaky_handler` and the emitter continues.

::: warning Don't use the bus for "must succeed" work
- ✅ Good: notifications, audit logs, cache invalidation, derived-data updates
- ❌ Bad: stock decrement, balance change — those must live in the original request transaction
:::

## Bus vs direct call

```python
# A: direct call (tightly coupled)
from app.business.notify.services import send_welcome_mail
await send_welcome_mail(employee_id=emp.id)

# B: event bus (loosely coupled)
await emit("employee.created", employee_id=emp.id)
```

| Condition | Pick A | Pick B |
|---|---|---|
| Caller and callee are in the same module | ✅ | — |
| Callee is a different business module | ❌ | ✅ |
| Multiple modules need to react | — | ✅ |
| Failure must abort the main flow | ✅ | ❌ |

## Disable in tests

```python
# tests/conftest.py
import app.core.events as ev

@pytest.fixture(autouse=True)
def _clear_handlers(monkeypatch):
    monkeypatch.setattr(ev, "_handlers", __import__("collections").defaultdict(list))
```

Or no-op `emit`:

```python
async def test_xxx(monkeypatch):
    monkeypatch.setattr("app.utils.emit", lambda *a, **kw: asyncio.sleep(0))
```

## Published events

| Event | Source | kwargs | Purpose |
|---|---|---|---|
| `employee.created` | HR | `employee_id`, `department_id`, `created_by` | post-create notification / stats |
| `employee.status_changed` | HR | `employee_id`, `from_state`, `to_state`, `actor_id` | post-transition audit |

> When you add a new event, append it here and add a comment at the emit site pointing to this page.

## See also

- [HR module (event emit example)](/en/develop/business-hr)
- [State machine](/en/develop/state-machine) — often paired with `emit` to publish audit events
