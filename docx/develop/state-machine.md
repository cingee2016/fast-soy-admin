# 状态机

轻量级状态机，做三件事：

1. 校验 `from_state → to_state` 是否合法
2. 原子更新模型字段
3. 调用日志函数记审计

不引入独立的 `TransitionLog` 表——审计走 `radar_log` 即可。

源码：[`app/core/state_machine.py`](../../../app/core/state_machine.py)。

## 定义

```python
from app.utils import StateMachine

EMPLOYEE_FSM = StateMachine(
    transitions={
        "pending":    ["onboarding"],          # pending → onboarding
        "onboarding": ["active"],              # onboarding → active
        "active":     ["resigned"],            # active → resigned
        "resigned":   [],                      # 终态
    }
)
```

`transitions` 是一张邻接表：`{当前状态: [合法的目标状态列表]}`。

## 执行流转

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
    return Success(msg="状态更新成功", data=await emp.to_dict())
```

`transition` 内部：

1. 读取 `getattr(obj, state_field)`，兼容 `Enum.value`
2. `allowed(from_state, to_state)` 不通过 → 抛 `TransitionError(code=Code.HR_INVALID_TRANSITION, msg="不允许从 'X' 转换为 'Y'，允许的目标: [...]")`
3. `obj.update_from_dict({state_field: to_state, **extra_updates})` + `obj.save(update_fields=...)`
4. `log_fn("状态变更", data={"model", "id", "fromState", "toState", "actorId", "at"})`

## 完整签名

```python
async def transition(
    self,
    obj: Any,                                      # Tortoise 模型实例
    to_state: str,                                 # 目标状态值
    state_field: str = "status",
    actor_id: int | None = None,
    log_fn: Callable[..., None] | None = None,
    extra_updates: dict[str, Any] | None = None,   # 与状态变更同时原子写入的额外字段
) -> None
```

`extra_updates` 用法：状态切到 `resigned` 时同时写离职日期。

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

## 查询合法目标

```python
EMPLOYEE_FSM.allowed("pending", "active")    # → False
EMPLOYEE_FSM.allowed_targets("pending")      # → ["onboarding"]
```

前端能据此做"动态展示下一步动作"——参考 [HR 模块](./business-hr.md#状态机员工状态流转)。

## 失败抛 TransitionError

`TransitionError` 继承 `BizError`，全局异常处理器会转成 `Fail(code=Code.HR_INVALID_TRANSITION, msg=...)`：

```python
try:
    await EMPLOYEE_FSM.transition(obj=emp, to_state="active", ...)
except TransitionError as e:
    return Fail(code=e.code, msg=e.msg)
```

> 通常**不需要**自己捕获——直接让它穿透到全局处理器，前端根据码做提示即可。

## 业务码扩展

不同模块的状态机错误用各自码段：

```python
# app/core/code.py 末尾
class Code:
    ...
    # 40xx HR
    HR_INVALID_TRANSITION = "4007"

    # 41xx 订单
    ORDER_INVALID_TRANSITION = "4107"
```

然后业务里：

```python
class _OrderTransitionError(BizError):
    """订单状态机错误（专属码）"""

# 在 transition 调用前自己包一层，或者按场景判定
```

对码段不挑剔时，直接复用 `Code.HR_INVALID_TRANSITION`——框架内置一个通用码即可。

## 与权限的关系

状态机只校验"合法性"，不做"谁有权这么做"。**鉴权放在路由层**：

```python
@router.post("/employees/{emp_id}/transition", dependencies=[require_buttons("B_HR_EMP_TRANSITION")])
async def _(emp_id: SqidPath, body: EmployeeTransition):
    return await transition_employee(emp_id, body.to_state)
```

## 测试

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

## 相关

- [HR 模块（员工状态流转完整实例）](./business-hr.md#状态机员工状态流转)
- [事件总线](./events.md) — 状态变更后常用 `emit` 发布事件
