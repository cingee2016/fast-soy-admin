"""
HR service — 员工创建、技能管理的核心业务逻辑。
"""

from tortoise.transactions import in_transaction

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.controllers import employee_controller, skill_controller
from app.business.hr.models import Department, Employee
from app.business.hr.schemas import EmployeeCreate
from app.utils import Fail, Success, create_system_user, has_button_code, is_super_admin, radar_log


async def generate_employee_no() -> str:
    """生成工号: 前缀 + 自增序号"""
    count = await employee_controller.model.all().count()
    return f"{BIZ_SETTINGS.EMPLOYEE_NO_PREFIX}{count + 1:04d}"


async def create_employee(emp_in: EmployeeCreate, current_emp: Employee | None, redis):
    """
    统一创建员工 — 自动创建系统用户 + 员工 + 技能关联。

    - 超级管理员: department 必须指定
    - 部门主管(B_HR_CREATE): department 自动继承
    """
    # 1. 权限 & 部门
    if is_super_admin():
        if not emp_in.department_id:
            return Fail(msg="超级管理员创建员工需要指定部门")
    elif has_button_code("B_HR_CREATE") and current_emp:
        dept = await Department.filter(manager_id=current_emp.id).first()
        if not dept:
            return Fail(msg="仅部门主管可创建员工")
        emp_in.department_id = dept.id
    else:
        return Fail(msg="无权限创建员工")

    # 2. 校验技能上限
    if emp_in.skill_ids and len(emp_in.skill_ids) > BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE:
        return Fail(msg=f"技能数量不能超过 {BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE}")

    employee_no = await generate_employee_no()

    # 3. 一个事务: 创建 User + Employee + 技能关联
    async with in_transaction("conn_system"):
        # 创建系统用户 (随机密码 + must_change_password + R_USER)
        try:
            result = await create_system_user(
                redis,
                user_name=emp_in.user_name,
                nick_name=emp_in.name,
                user_email=emp_in.email,
                user_gender=emp_in.user_gender,
                user_phone=emp_in.phone,
            )
        except ValueError as e:
            return Fail(msg=str(e))

        # 创建员工
        new_emp = await employee_controller.create(obj_in=emp_in, exclude={"skill_ids", "password", "email", "user_name", "user_gender"})
        await Employee.filter(id=new_emp.id).update(employee_no=employee_no, email=emp_in.email, user_id=result.user.id)

        # 关联技能
        if emp_in.skill_ids:
            for sid in emp_in.skill_ids:
                skill = await skill_controller.get(id=sid)
                await new_emp.skills.add(skill)

    radar_log("创建员工", data={"employeeId": new_emp.id, "employeeNo": employee_no, "userId": result.user.id})
    return Success(
        msg="创建成功",
        data={
            "employee_id": new_emp.id,
            "employee_no": employee_no,
            "user_id": result.user.id,
            "raw_password": result.raw_password,
        },
    )


async def get_department_stats():
    """部门统计"""
    departments = await Department.all().select_related("manager")
    stats = []
    for dept in departments:
        emp_count = await Employee.filter(department_id=dept.id).count()
        stats.append({
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "managerName": dept.manager.name if dept.manager else None,
            "employeeCount": emp_count,
        })
    return stats
