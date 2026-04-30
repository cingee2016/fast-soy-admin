# State Machine

Lightweight FSM that does three things:

1. Validates `from_state → to_state`
2. Atomically updates the model field
3. Calls a logger for audit

No separate `TransitionLog` table — audit goes through `radar_log`.

Source: `app/core/state_machine.py`.

## Define

```python
from app.utils import StateMachine

EMPLOYEE_FSM = StateMachine(
    transitions={
        "pending":    ["onboarding"],
        "onboarding": ["active"],
        "active":     ["resigned"],
        "resigned":   [],          # terminal
    }
)
```

`transitions` is an adjacency list: `{current_state: [allowed_targets]}`.

## Transition

```python
from app.utils import radar_log, get_current_user_id

async def transition_employee(emp_id: int, to_state: str):
    emp = await employee_controller.get(id=emp_id)
    await EMPLOYEE_FSM.transition(
        obj=emp,
        to_state=to_state,
        state_field="status",
        actor_id=get_current_user_id(),
        log_fn=radar_log,
    )
    await emit("employee.status_changed", employee_id=emp_id, ...)
    return Success(msg="state updated", data=await emp.to_dict())
```

Inside `transition`:

1. Reads `getattr(obj, state_field)`, handles `Enum.value`
2. If `allowed(from_state, to_state)` is false → raise `TransitionError(code=Code.HR_INVALID_TRANSITION, msg="not allowed from 'X' to 'Y'; allowed targets: [...]")`
3. `obj.update_from_dict({state_field: to_state, **extra_updates})` + `obj.save(update_fields=...)`
4. `log_fn("state changed", data={"model", "id", "fromState", "toState", "actorId", "at"})`

## Full signature

```python
async def transition(
    self,
    obj: Any,                                 # Tortoise model instance
    to_state: str,                            # target state
    state_field: str = "status",
    actor_id: int | None = None,
    log_fn: Callable[..., None] | None = None,
    extra_updates: dict[str, Any] | None = None,   # extra fields to write atomically
) -> None
```

`extra_updates` use case: write `resigned_at` together with the state transition.

```python
await EMPLOYEE_FSM.transition(
    obj=emp,
    to_state="resigned",
    state_field="status",
    actor_id=get_current_user_id(),
    log_fn=radar_log,
    extra_updates={"resigned_at": datetime.now(tz=timezone.utc)},
)
```

## Inspect allowed targets

```python
EMPLOYEE_FSM.allowed("pending", "active")    # → False
EMPLOYEE_FSM.allowed_targets("pending")      # → ["onboarding"]
```

The frontend can use this to show a "next action" button dynamically. See [HR module](/en/develop/business-hr#state-machine-employee-state-transitions).

## Failure → TransitionError

`TransitionError` extends `BizError`; the global handler turns it into `Fail(code=Code.HR_INVALID_TRANSITION, msg=...)`:

```python
try:
    await EMPLOYEE_FSM.transition(obj=emp, to_state="active", ...)
except TransitionError as e:
    return Fail(code=e.code, msg=e.msg)
```

> **Don't** catch it — let it propagate to the global handler; the frontend reacts to the code.

## Per-module business codes

Different modules use different code ranges:

```python
# end of app/core/code.py
class Code:
    ...
    # 40xx HR
    HR_INVALID_TRANSITION = "4007"

    # 41xx Order
    ORDER_INVALID_TRANSITION = "4107"
```

Then in business code wrap conditionally — or just reuse `Code.HR_INVALID_TRANSITION` if you don't care about the segment.

## Permission relationship

The state machine only validates "legality"; it doesn't check "who's allowed to transition". **Authorize at the route layer**:

```python
@router.post("/employees/{emp_id}/transition", dependencies=[require_buttons("B_HR_EMP_TRANSITION")])
async def _(emp_id: SqidPath, body: EmployeeTransition):
    return await transition_employee(emp_id, body.to_state)
```

## Tests

```python
async def test_pending_to_onboarding_ok():
    emp = await Employee.create(status="pending", ...)
    await EMPLOYEE_FSM.transition(obj=emp, to_state="onboarding")
    assert emp.status == "onboarding"


async def test_pending_to_active_blocked():
    emp = await Employee.create(status="pending", ...)
    with pytest.raises(TransitionError) as ei:
        await EMPLOYEE_FSM.transition(obj=emp, to_state="active")
    assert ei.value.code == Code.HR_INVALID_TRANSITION
```

## See also

- [HR module (full employee state transition example)](/en/develop/business-hr#state-machine-employee-state-transitions)
- [Event bus](/en/develop/events) — emit audit events after transitions
