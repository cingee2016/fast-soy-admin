"""
HR 主管接口 — 查看/编辑部门员工 (需要主管身份)。
"""

from fastapi import APIRouter

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.controllers import skill_controller
from app.business.hr.dependency import DependManager
from app.business.hr.models import Employee
from app.business.hr.schemas import SkillIds
from app.utils import Fail, Success, radar_log

router = APIRouter(prefix="/hr", tags=["HR主管"])


@router.get("/department/employees", summary="[主管] 查看部门员工")
async def dept_employees(mgr: Employee = DependManager):
    """主管查看自己部门所有员工详细信息"""
    employees = await Employee.filter(department_id=mgr.department_id).prefetch_related("skills")  # type: ignore[arg-type]
    records = []
    for emp in employees:
        record = await emp.to_dict()
        record["skillNames"] = [s.name for s in emp.skills]
        records.append(record)
    return Success(data=records)


@router.patch("/department/employees/{emp_id}/skills", summary="[主管] 编辑下属技能")
async def edit_employee_skills(emp_id: int, body: SkillIds, mgr: Employee = DependManager):
    """主管编辑同部门下属的技能"""
    target = await Employee.filter(id=emp_id, department_id=mgr.department_id).first()  # type: ignore[arg-type]
    if not target:
        return Fail(msg="该员工不在您的部门中")

    if len(body.skill_ids) > BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE:
        return Fail(msg=f"技能数量不能超过 {BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE}")

    await target.skills.clear()
    for sid in body.skill_ids:
        await target.skills.add(await skill_controller.get(id=sid))

    radar_log("主管编辑下属技能", data={"managerId": mgr.id, "employeeId": emp_id, "skillIds": body.skill_ids})
    return Success(msg="技能更新成功")
