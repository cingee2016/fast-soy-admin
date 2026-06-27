"""
HR 模块初始化数据 — 菜单、角色、标签与演示员工。

启动时由 autodiscover 自动发现并执行 init()。
所有操作幂等，重复启动不会重复创建。
"""

from __future__ import annotations

import asyncio

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.models import Department, Employee, Tag
from app.business.hr.seed_data import HR_DEPARTMENT_SEEDS, HR_EMPLOYEE_SEEDS, HR_TAG_SEEDS
from app.system.services import apply_init_data, ensure_user
from app.system.services.init_helper import _safe_update_or_create
from app.utils import DataScopeType

# 菜单和按钮是 HR 子树的 IaC 源；启用 reconcile 后，Web UI 手工加的同子树节点会被清理。
HR_MENU_CHILDREN = [
    {
        "menu_name": "我的工作台",
        "route_name": "hr_my-workspace",
        "route_path": "/hr/my-workspace",
        "component": "view.hr_my-workspace",
        "icon": "mdi:account-circle-outline",
        "order": 1,
        "buttons": [
            {"button_code": "B_HR_MY_TAG_EDIT", "button_desc": "编辑自己的标签"},
            {"button_code": "B_HR_MY_AVATAR_EDIT", "button_desc": "上传自己的头像"},
        ],
    },
    {
        "menu_name": "我的团队",
        "route_name": "hr_team",
        "route_path": "/hr/team",
        "component": "view.hr_team",
        "icon": "mdi:account-supervisor-circle-outline",
        "order": 2,
        "buttons": [
            {"button_code": "B_HR_TEAM_EMP_CREATE", "button_desc": "[主管] 创建下属"},
            {"button_code": "B_HR_TEAM_EMP_EDIT", "button_desc": "[主管] 编辑下属"},
            {"button_code": "B_HR_TEAM_TAG_EDIT", "button_desc": "[主管] 编辑下属标签"},
            {"button_code": "B_HR_TEAM_EMP_TRANSITION", "button_desc": "[主管] 推进下属状态"},
        ],
    },
    {
        "menu_name": "部门管理",
        "route_name": "hr_department",
        "route_path": "/hr/department",
        "component": "view.hr_department",
        "icon": "mdi:office-building",
        "order": 3,
        "buttons": [
            {"button_code": "B_HR_DEPT_CREATE", "button_desc": "创建部门"},
            {"button_code": "B_HR_DEPT_EDIT", "button_desc": "编辑部门"},
            {"button_code": "B_HR_DEPT_DELETE", "button_desc": "删除部门"},
        ],
    },
    {
        "menu_name": "员工管理",
        "route_name": "hr_employee",
        "route_path": "/hr/employee",
        "component": "view.hr_employee",
        "icon": "mdi:account",
        "order": 4,
        "buttons": [
            {"button_code": "B_HR_EMP_CREATE", "button_desc": "创建员工"},
            {"button_code": "B_HR_EMP_EDIT", "button_desc": "编辑员工"},
            {"button_code": "B_HR_EMP_DELETE", "button_desc": "删除员工"},
            {"button_code": "B_HR_EMP_TRANSITION", "button_desc": "员工状态流转"},
        ],
    },
    {
        "menu_name": "标签管理",
        "route_name": "hr_tag",
        "route_path": "/hr/tag",
        "component": "view.hr_tag",
        "icon": "mdi:tag-multiple",
        "order": 5,
        "buttons": [
            {"button_code": "B_HR_TAG_CREATE", "button_desc": "创建标签"},
            {"button_code": "B_HR_TAG_EDIT", "button_desc": "编辑标签"},
            {"button_code": "B_HR_TAG_DELETE", "button_desc": "删除标签"},
        ],
    },
]

# 三类 route key 聚合，角色授权只引用这些 key；just init-plan --strict 会校验它们是否存在。
HR_MY_APIS = [
    "hr.my.profile",
    "hr.my.update",
    "hr.my.tags",
    "hr.my.department",
    "hr.my.avatar",
    "hr.tags.list",
]

HR_TEAM_APIS = [
    "hr.team.list",
    "hr.team.stats",
    "hr.team.create",
    "hr.team.update",
    "hr.team.tags",
    "hr.team.transition",
    "hr.tags.list",
]

HR_ADMIN_APIS = [
    "hr.departments.list",
    "hr.departments.tree",
    "hr.departments.create",
    "hr.departments.update",
    "hr.departments.delete",
    "hr.departments.batch_delete",
    "hr.employees.list",
    "hr.employees.get",
    "hr.employees.create",
    "hr.employees.update",
    "hr.employees.delete",
    "hr.employees.batch_delete",
    "hr.employees.transition",
    "hr.employees.avatar",
    "hr.tags.list",
    "hr.tags.create",
    "hr.tags.update",
    "hr.tags.delete",
    "hr.tags.batch_delete",
]


HR_ROLE_SEEDS = [
    {
        "role_name": "HR管理员",
        "role_code": "R_HR_ADMIN",
        "role_desc": "HR 总管，掌管部门、员工、标签的全量维护",
        "data_scope": DataScopeType.all,
        "menus": ["home", "hr", "hr_my-workspace", "hr_team", "hr_department", "hr_employee", "hr_tag"],
        "buttons": [
            "B_HR_MY_TAG_EDIT",
            "B_HR_MY_AVATAR_EDIT",
            "B_HR_TEAM_EMP_CREATE",
            "B_HR_TEAM_EMP_EDIT",
            "B_HR_TEAM_TAG_EDIT",
            "B_HR_TEAM_EMP_TRANSITION",
            "B_HR_DEPT_CREATE",
            "B_HR_DEPT_EDIT",
            "B_HR_DEPT_DELETE",
            "B_HR_EMP_CREATE",
            "B_HR_EMP_EDIT",
            "B_HR_EMP_DELETE",
            "B_HR_EMP_TRANSITION",
            "B_HR_TAG_CREATE",
            "B_HR_TAG_EDIT",
            "B_HR_TAG_DELETE",
        ],
        "apis": HR_MY_APIS + HR_TEAM_APIS + HR_ADMIN_APIS,
    },
    {
        "role_name": "部门主管",
        "role_code": "R_DEPT_MGR",
        "role_desc": "部门主管，可管理本部门员工与下属",
        "data_scope": DataScopeType.scope,
        "menus": ["home", "hr", "hr_my-workspace", "hr_team"],
        "buttons": [
            "B_HR_MY_TAG_EDIT",
            "B_HR_MY_AVATAR_EDIT",
            "B_HR_TEAM_EMP_CREATE",
            "B_HR_TEAM_EMP_EDIT",
            "B_HR_TEAM_TAG_EDIT",
            "B_HR_TEAM_EMP_TRANSITION",
        ],
        "apis": HR_MY_APIS + HR_TEAM_APIS,
    },
    {
        "role_name": "普通员工",
        "role_code": "R_EMPLOYEE",
        "role_desc": "已绑定员工身份的普通用户，仅能维护自己的资料/标签并查看同部门同事",
        "data_scope": DataScopeType.self_,
        "menus": ["home", "hr", "hr_my-workspace"],
        "buttons": ["B_HR_MY_TAG_EDIT", "B_HR_MY_AVATAR_EDIT"],
        "apis": HR_MY_APIS,
    },
]

INIT_DATA = {
    "menus": [
        {
            # 公开展示页是常量路由：前端能访问，还需要后端种 Menu 让 dynamic route 模式能拉到。
            "menu_name": "HR数据展示",
            "route_name": "showcase",
            "route_path": "/showcase",
            "component": "layout.blank$view.showcase",
            "menu_type": "1",
            "constant": True,
            "hide_in_menu": True,
            "order": 100,
        },
        {
            "menu_name": "HR管理",
            "route_name": "hr",
            "route_path": "/hr",
            "icon": "mdi:account-group",
            "order": 20,
            "children": HR_MENU_CHILDREN,
            "reconcile": {"menus": True, "buttons": True},
        },
    ],
    "roles": HR_ROLE_SEEDS,
    "users": [],
    "dictionaries": [],
}


def _employee_no(serial: int) -> str:
    return f"{BIZ_SETTINGS.EMPLOYEE_NO_PREFIX}{serial:04d}"


async def _init_departments() -> None:
    await asyncio.gather(
        *(
            _safe_update_or_create(
                Department,
                {"code": seed["code"]},
                {"name": seed["name"], "description": seed["description"]},
            )
            for seed in HR_DEPARTMENT_SEEDS
        )
    )


async def _init_tags() -> None:
    await asyncio.gather(
        *(
            _safe_update_or_create(
                Tag,
                {"name": seed["name"]},
                {"category": seed["category"], "description": seed["description"]},
            )
            for seed in HR_TAG_SEEDS
        )
    )


async def _ensure_demo_employee(seed: dict) -> Employee:
    # Demo 员工先创建系统用户，再绑定 Employee；重复启动通过 employee_no 幂等更新。
    user = await ensure_user(**seed["user"])

    employee_seed = seed["employee"]
    department = await Department.get(code=employee_seed["department_code"])
    employee_no = _employee_no(employee_seed["employee_no_serial"])

    employee, _ = await _safe_update_or_create(
        Employee,
        {"employee_no": employee_no},
        {
            "name": employee_seed["name"],
            "email": employee_seed["email"],
            "phone": employee_seed["phone"],
            "position": employee_seed["position"],
            "user_id": user.id,
            "department_id": department.id,
        },
    )

    await employee.tags.clear()
    for tag_name in employee_seed["tag_names"]:
        tag = await Tag.get(name=tag_name)
        await employee.tags.add(tag)

    return employee


async def _init_demo_employees() -> None:
    employees = await asyncio.gather(*(_ensure_demo_employee(seed) for seed in HR_EMPLOYEE_SEEDS))
    employee_map: dict[int, Employee] = {seed["employee"]["employee_no_serial"]: emp for seed, emp in zip(HR_EMPLOYEE_SEEDS, employees)}

    async def _update_manager(seed: dict) -> None:
        # 部门主管引用 Employee.id，必须等员工 seed 都落库后再反向回填。
        manager = employee_map.get(seed["manager_employee_no"]) if seed.get("manager_employee_no") else None
        await Department.filter(code=seed["code"]).update(manager_id=manager.id if manager else None)

    await asyncio.gather(*(_update_manager(seed) for seed in HR_DEPARTMENT_SEEDS))


async def init():
    await apply_init_data(INIT_DATA)
    await asyncio.gather(_init_departments(), _init_tags())
    await _init_demo_employees()
