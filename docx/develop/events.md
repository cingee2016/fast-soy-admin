# 事件总线

进程内事件总线，用于**业务模块之间的解耦通信**。FastSoyAdmin 强约定 "system → 不知道 business、business 之间不互相 import"，跨模块联动必须走事件总线。

源码：[`app/core/events.py`](../../../app/core/events.py)。

## 设计原则

- **同进程**：仅在当前 worker 内分发，不做跨进程 / 跨服务投递（那是消息队列的工作）
- **顺序执行**：`emit` 中按注册顺序逐个 `await`，方便调试与定位
- **失败隔离**：单个处理器抛异常被 `log.exception` 捕获，不阻塞后续处理器
- **导入即注册**：`@on` 装饰器在模块导入时把处理器加进字典，所以含 `@on` 的模块必须被 import（一般在 `__init__.py` 顶层 import）

## 注册处理器

```python
# app/business/notify/events.py
from app.utils import emit, on


@on("employee.created")
async def _send_welcome_mail(employee_id: int, **kwargs):
    # 处理器签名应接受 **kwargs，便于发送方未来扩展参数
    ...


@on("employee.status_changed")
async def _audit_state(employee_id: int, from_state: str, to_state: str, **kwargs):
    ...
```

确保模块被加载：

```python
# app/business/notify/__init__.py
from . import events  # noqa: F401  ← 触发 @on 注册
```

## 触发事件

```python
# app/business/hr/services.py
from app.utils import emit

await emit("employee.created", employee_id=new_emp.id, department_id=dept.id)
```

任何 kwargs 都会原样透传给所有处理器。

## 命名约定

```
<aggregate>.<verb>
```

| 推荐 | 不推荐 |
|---|---|
| `employee.created` | `EmployeeCreated` |
| `employee.status_changed` | `change_employee_status_done` |
| `order.refunded` | `RefundOrder` |

事件名是契约，命好后**别改**——会有看不见的处理器依赖它。

## 同步处理器

接受同步函数，但不推荐：

```python
@on("user.logged_in")
def _log_login(user_id: int, **kwargs):
    print(f"user {user_id} logged in")
```

`emit` 会用 `inspect.iscoroutinefunction` 判断；同步处理器直接调用，会阻塞协程循环。**只在确实没有 IO 的场景**才用同步。

## 失败语义

```python
@on("employee.created")
async def _flaky_handler(employee_id: int, **kwargs):
    raise RuntimeError("oops")
```

`emit` 不会重抛——只在日志里输出 `Event handler error: employee.created / module._flaky_handler`，发送方代码继续往下执行。

::: warning 不要把"必须成功"的事情放在事件处理器
- ✅ 适合：通知、审计日志、缓存失效、衍生数据更新
- ❌ 不适合：扣减库存、改账户余额——这些必须放在原始请求的事务里
:::

## 事件处理 vs 直接调用

```python
# A: 直接调用（紧耦合）
from app.business.notify.services import send_welcome_mail
await send_welcome_mail(employee_id=emp.id)

# B: 事件总线（松耦合）
await emit("employee.created", employee_id=emp.id)
```

| 条件 | 选 A | 选 B |
|---|---|---|
| 调用方与被调用方在同一模块 | ✅ | — |
| 被调用方是另一个业务模块 | ❌ | ✅ |
| 多个模块需要联动 | — | ✅ |
| 失败必须中断主流程 | ✅ | ❌ |

## 测试时禁用

```python
# tests/conftest.py
import app.core.events as ev

@pytest.fixture(autouse=True)
def _clear_handlers(monkeypatch):
    monkeypatch.setattr(ev, "_handlers", __import__("collections").defaultdict(list))
```

或者只跑空 emit：

```python
async def test_xxx(monkeypatch):
    monkeypatch.setattr("app.utils.emit", lambda *a, **kw: asyncio.sleep(0))
```

## 已发布事件清单

| 事件 | 发起方 | kwargs | 用途 |
|---|---|---|---|
| `employee.created` | HR | `employee_id`, `department_id`, `created_by` | HR 创建员工后的通知/统计 |
| `employee.status_changed` | HR | `employee_id`, `from_state`, `to_state`, `actor_id` | 状态机流转后的审计 |

> 新增事件请追加到本表，并在事件发起处保留一行注释指向本文档。

## 相关

- [HR 模块（事件触发示例）](./business-hr.md)
- [状态机](./state-machine.md) — 状态变更后常配合 `emit` 发审计事件
