"""
HR 模块初始化数据 — 菜单、按钮、角色。

启动时由 autodiscover 自动发现并执行 init()。
所有操作幂等，重复启动不会重复创建。
"""

from app.utils.init_helper import ensure_menu, ensure_role


async def init():
    # ---- HR 顶级菜单 ----
    await ensure_menu(
        menu_name="HR管理",
        route_name="hr",
        route_path="/hr",
        icon="mdi:account-group",
        order=8,
        children=[
            dict(
                menu_name="员工管理",
                route_name="hr_employee",
                route_path="/hr/employee",
                component="view.hr_employee",
                icon="mdi:account",
                order=1,
                buttons=[
                    dict(button_code="B_HR_CREATE", button_desc="创建员工"),
                    dict(button_code="B_HR_EDIT", button_desc="编辑员工"),
                    dict(button_code="B_HR_DELETE", button_desc="删除员工"),
                ],
            ),
            dict(
                menu_name="部门管理",
                route_name="hr_department",
                route_path="/hr/department",
                component="view.hr_department",
                icon="mdi:office-building",
                order=2,
            ),
            dict(
                menu_name="技能管理",
                route_name="hr_skill",
                route_path="/hr/skill",
                component="view.hr_skill",
                icon="mdi:star",
                order=3,
            ),
        ],
    )

    # ---- 部门主管角色 ----
    await ensure_role(
        role_name="部门主管",
        role_code="R_DEPT_MGR",
        role_desc="部门主管，可管理本部门员工",
        menus=[
            "home",
            "hr",
            "hr_employee",
            "hr_department",
            "hr_skill",
        ],
        buttons=["B_HR_CREATE", "B_HR_EDIT"],
        apis=[
            ("post", "/api/v1/business/hr/employees"),
            ("post", "/api/v1/business/hr/employees/all/"),
            ("patch", "/api/v1/business/hr/employees/{emp_id}"),
            ("get", "/api/v1/business/hr/employees/{item_id}"),
            ("get", "/api/v1/business/hr/department/employees"),
            ("post", "/api/v1/business/hr/departments/all/"),
            ("patch", "/api/v1/business/hr/department/employees/{emp_id}/skills"),
            ("get", "/api/v1/business/hr/departments/stats"),
            ("get", "/api/v1/business/hr/skills"),
        ],
    )
