# pyright: reportIncompatibleVariableOverride=false
"""
Business schema example — 员工、部门、技能的请求/响应 Schema。
"""

from pydantic import Field

from app.utils import SchemaBase, StatusType

# ============================================================
# Department
# ============================================================


class DepartmentBase(SchemaBase):
    name: str | None = Field(None, title="部门名称")
    code: str | None = Field(None, title="部门编码")
    description: str | None = Field(None, title="部门描述")
    manager_id: int | None = Field(None, title="主管员工ID")
    status: StatusType | None = Field(None, title="状态")


class DepartmentCreate(DepartmentBase):
    name: str = Field(title="部门名称")
    code: str = Field(title="部门编码")


class DepartmentUpdate(DepartmentBase): ...


class DepartmentSearch(DepartmentBase):
    current: int | None = Field(1, title="页码")
    size: int | None = Field(10, title="每页数量")


# ============================================================
# Skill
# ============================================================


class SkillBase(SchemaBase):
    name: str | None = Field(None, title="技能名称")
    category: str | None = Field(None, title="技能分类")
    description: str | None = Field(None, title="技能描述")


class SkillCreate(SkillBase):
    name: str = Field(title="技能名称")
    category: str = Field(title="技能分类")


class SkillUpdate(SkillBase): ...


# ============================================================
# Employee
# ============================================================


class EmployeeBase(SchemaBase):
    name: str | None = Field(None, title="员工姓名")
    email: str | None = Field(None, title="邮箱")
    phone: str | None = Field(None, title="电话")
    position: str | None = Field(None, title="职位")
    status: StatusType | None = Field(None, title="状态")


class EmployeeCreate(EmployeeBase):
    user_name: str = Field(title="用户名 (手机号)")
    name: str = Field(title="昵称/姓名")
    email: str = Field(title="邮箱")
    user_gender: str | None = Field(None, title="性别 (1男 2女)")
    department_id: int | None = Field(None, title="部门ID (主管创建时自动继承)")
    skill_ids: list[int] | None = Field(None, title="技能ID列表")


class EmployeeUpdate(EmployeeBase):
    skill_ids: list[int] | None = Field(None, title="技能ID列表")


class SkillIds(SchemaBase):
    skill_ids: list[int] = Field(title="技能ID列表")


class EmployeeSearch(EmployeeBase):
    current: int | None = Field(1, title="页码")
    size: int | None = Field(10, title="每页数量")
    department_id: int | None = Field(None, title="部门ID")
