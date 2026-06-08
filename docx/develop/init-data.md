# 启动初始化与对账

业务模块通过 `init_data.py` 声明菜单、角色、按钮、种子数据等初始内容，应用每次启动时由 autodiscover 自动调用其 `init()` 函数。下文说明各类数据在启动时的同步语义，以及如何让业务模块成为 single-source-of-truth。

## 启动流程

启动时由 Redis leader worker 在 [app/\_\_init\_\_.py](../../../app/__init__.py) 的 lifespan 中顺序执行：

1. `init_menus()` — 系统菜单（`app/system/init_data.py`）
2. `refresh_api_list()` — **全量对账** FastAPI 路由与 `Api` 表
3. `init_users()` — 系统种子用户
4. 遍历所有业务模块的 `init_data.init()`（HR、后续新增模块……）
5. `refresh_all_cache()` — 刷新权限/菜单缓存

多 worker 场景下通过 Redis 分布式锁 `app:init_lock` 保证仅一个进程执行 init，其余 worker 等待完成信号；每次启动前 leader 会先删除旧锁，因此每次重启都会真的跑一次 init。

## 各类数据的同步语义

| 数据类型 | 同步方式 | 改字段 | 新增项 | 删除项 | 重命名 |
|---------|---------|-------|-------|-------|-------|
| **API**（路由） | `refresh_api_list` 全量对账 | ✅ 自动 | ✅ 自动 | ✅ 自动 | ✅ 自动（删旧建新） |
| **菜单** | `ensure_menu` upsert + 可选 `reconcile_menu_subtree` | ✅ 自动 | ✅ 自动 | ⚠️ 需启用对账 | ⚠️ 需启用对账 |
| **按钮** | `ensure_menu` upsert + 可选 `reconcile_menu_subtree` | ✅ 自动 | ✅ 自动 | ⚠️ 需启用对账 | ⚠️ 需启用对账 |
| **角色** | `ensure_role` upsert，关系 clear-and-readd | ✅ 自动 | ✅ 自动 | ❌ 需手动清库 | ❌ 需手动清库 |
| **角色权限**（menus/buttons/apis 授权） | clear-and-readd | ✅ 自动 | ✅ 自动 | ✅ 自动 | ⚠️ 缺失会 log.warning |
| **业务种子数据** | `_safe_update_or_create` by 唯一键 | ✅ 自动 | ✅ 自动 | ❌ 需手动清库 | ❌ 需手动清库 |

图例：✅ 重启即生效；⚠️ 需要显式启用或关注；❌ 需要 SQL/迁移手动处理。

## 菜单/按钮对账：`reconcile_menu_subtree`

`ensure_menu` 是前向应用（只 upsert，不删除），所以从 `init_data.py` 中**删除**条目不会自动清理数据库。为此 [app/system/services/init_helper.py](../../../app/system/services/init_helper.py) 提供了 `apply_init_data` / `reconcile_menu_subtree`：业务模块只声明一个 `INIT_DATA` 字典，应用器会递归创建菜单/按钮，并按菜单子树做可选对账。

### 使用方式

`just cli-gen` / `just cli-crud` 生成后端代码时，会在业务模块的 `init_data.py` 中自动写入 `INIT_DATA` 和 `apply_init_data(INIT_DATA)`。按钮挂在所属菜单节点的 `buttons` 下，菜单子树通过 `reconcile` 控制是否进入 IaC 对账。

推荐写法：

```python
from app.system.services import apply_init_data


INIT_DATA = {
    "menus": [
        {
            "menu_name": "客户管理",
            "route_name": "crm",
            "route_path": "/crm",
            "icon": "mdi:account-box",
            "order": 8,
            "reconcile": {
                "menus": True,
                "buttons": True,
            },
            "children": [
                {
                    "menu_name": "客户",
                    "route_name": "crm_customer",
                    "route_path": "/crm/customer",
                    "component": "view.crm_customer",
                    "buttons": [
                        {"button_code": "B_CRM_CUSTOMER_CREATE", "button_desc": "创建客户"},
                        {"button_code": "B_CRM_CUSTOMER_EDIT", "button_desc": "编辑客户"},
                    ],
                }
            ],
        }
    ],
    "roles": [],
    "users": [],
    "dictionaries": [],
}


async def init() -> None:
    await apply_init_data(INIT_DATA)
```

### 作用范围与语义

- **作用域严格限定在子树内**：以 `root_route` 对应菜单为根，递归 BFS 收集整个子树，只清理该子树内的条目，不会误伤其他模块。
- **菜单对账**：子树内 `route_name` 不在声明集合 ∪ `{root_route}` 的菜单会被 `delete()`（级联清 M2M 关系）。
- **按钮对账**：仅处理"挂在本子树菜单上的按钮"，这些按钮的 `button_code` 不在声明集合中的会被 `delete()`。`"reconcile": {"buttons": False}` 则跳过按钮对账。
- **幂等**：可重复执行，子树内无多余项时是 no-op。

### 心智转变

启用 `reconcile_menu_subtree` 后，该子树进入 **"Infrastructure-as-Code"** 模式：

- ✅ 修改/删除 `init_data.py` 即可，重启自动生效
- ✅ 改名相当于删旧 + 新增，对账会自动清掉旧项
- ❌ **从 Web 端手动新建的子菜单/按钮会在下次启动时被清掉**

如果需要保留 Web 端的动态菜单能力，不要对那个子树调 `reconcile_menu_subtree`。

## `ensure_role` 配置漂移告警

[app/system/services/init_helper.py](../../../app/system/services/init_helper.py) 的 `ensure_role` 会对 `menus` / `buttons` / `apis` 做 clear-and-readd。若声明列表里引用的 `route_name` / `button_code` / `(method, path)` 在数据库里找不到对应记录，会发出 warning：

```
ensure_role 'R_DEPT_MGR': missing apis [('patch', '/api/v1/business/hr/departments/{dept_id}/old')] (route signature changed?)
```

这常见于以下情况：
- 路由被重命名或删除，但 `init_data.py` 的 `apis` 列表忘了同步
- `button_code` 被改名，但种子角色的 `buttons` 列表没跟上
- 父菜单 `route_name` 改了，但种子角色的 `menus` 列表没跟上

**看到这类 warning 必须立即修** —— 否则对应的角色权限就会静默缺失，用户会遇到莫名的 403。

## 删除残留的手动清理

`reconcile_menu_subtree` 只处理菜单与按钮，以下几类**仍需手动清库**（SQL 或 Tortoise 迁移）：

1. **角色** — `HR_ROLE_SEEDS` 移除一个角色后，DB 里的 `Role` 行不会被清掉，挂在它身上的用户关系也保持原样
2. **业务种子数据** — `HR_DEPARTMENT_SEEDS` / `HR_TAG_SEEDS` / `HR_EMPLOYEE_SEEDS` 的移除同理
3. **跨子树的孤儿按钮** — 若某按钮同时被多个子树引用，仅从当前子树移除不会触发 `delete()`

这些场景发生频率低，且删除涉及级联语义（比如删角色要不要删关联用户的 role 挂载？），所以刻意不自动化 —— 走正式的 Tortoise 迁移更安全。

## 小结

| 场景 | 推荐做法 |
|------|---------|
| 新增菜单/按钮/角色/种子数据 | 改 `init_data.py`，重启即生效 |
| 修改菜单字段（名称、图标、排序等） | 改 `init_data.py`，重启即生效 |
| 删除菜单/按钮 | 启用 `reconcile_menu_subtree`，改 `init_data.py`，重启即生效 |
| 重命名菜单 `route_name` / 按钮 `button_code` | 启用 `reconcile_menu_subtree`，重启自动删旧建新 |
| 删除角色或种子业务数据 | 写 Tortoise 迁移 |
| 修改 API 路由路径 | 同步更新 `init_data.py` 中 `HR_ROLE_SEEDS` 的 `apis` 列表，否则启动会 warning |
