"""
HR 个人接口 — 查看/编辑自己的信息和技能 (需要员工身份)。
"""

from fastapi import APIRouter

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.controllers import skill_controller
from app.business.hr.dependency import DependEmployee
from app.business.hr.models import Employee
from app.business.hr.schemas import SkillIds
from app.utils import DependAuth, Fail, Success, radar_log

router = APIRouter(prefix="/hr", tags=["HR个人"], dependencies=[DependAuth])


@router.get("/my/profile", summary="我的信息")
async def my_profile(emp: Employee = DependEmployee):
    """查看自己的信息和技能"""
    await emp.fetch_related("department", "skills")
    record = await emp.to_dict()
    record["departmentName"] = emp.department.name
    record["skills"] = [await s.to_dict() for s in emp.skills]
    return Success(data=record)


@router.patch("/my/skills", summary="编辑我的技能")
async def my_skills(body: SkillIds, emp: Employee = DependEmployee):
    """编辑自己的技能列表"""
    if len(body.skill_ids) > BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE:
        return Fail(msg=f"技能数量不能超过 {BIZ_SETTINGS.MAX_SKILLS_PER_EMPLOYEE}")

    await emp.skills.clear()
    for sid in body.skill_ids:
        await emp.skills.add(await skill_controller.get(id=sid))

    radar_log("编辑个人技能", data={"employeeId": emp.id, "skillIds": body.skill_ids})
    return Success(msg="技能更新成功")


@router.get("/my/department", summary="同部门同事")
async def my_department(emp: Employee = DependEmployee):
    """查看同部门同事及其技能"""
    colleagues = await Employee.filter(department_id=emp.department_id).prefetch_related("skills")  # type: ignore[arg-type]
    records = []
    for c in colleagues:
        record = await c.to_dict(exclude_fields=["phone", "email"])
        record["skillNames"] = [s.name for s in c.skills]
        records.append(record)
    return Success(data=records)
