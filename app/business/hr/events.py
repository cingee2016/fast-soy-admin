"""HR typed events and local handlers."""

from pydantic import BaseModel

from app.utils import EventSpec, on, radar_log


class EmployeeCreatedPayload(BaseModel):
    employee_id: int
    employee_no: str


class EmployeeUpdatedPayload(BaseModel):
    employee_id: int


class EmployeeDeletedPayload(BaseModel):
    employee_ids: list[int]


class EmployeeStatusChangedPayload(BaseModel):
    employee_id: int
    from_state: str
    to_state: str


HR_EMPLOYEE_CREATED = EventSpec(name="hr.employee.created", payload=EmployeeCreatedPayload)
HR_EMPLOYEE_UPDATED = EventSpec(name="hr.employee.updated", payload=EmployeeUpdatedPayload)
HR_EMPLOYEE_DELETED = EventSpec(name="hr.employee.deleted", payload=EmployeeDeletedPayload)
HR_EMPLOYEE_STATUS_CHANGED = EventSpec(name="hr.employee.status_changed", payload=EmployeeStatusChangedPayload)

HR_EVENTS = [
    HR_EMPLOYEE_CREATED,
    HR_EMPLOYEE_UPDATED,
    HR_EMPLOYEE_DELETED,
    HR_EMPLOYEE_STATUS_CHANGED,
]


@on(HR_EMPLOYEE_CREATED)
async def _on_employee_created(employee_id: int, employee_no: str, **kwargs):
    radar_log("HR事件: 员工已创建", data={"employeeId": employee_id, "employeeNo": employee_no})


@on(HR_EMPLOYEE_UPDATED)
async def _on_employee_updated(employee_id: int, **kwargs):
    radar_log("HR事件: 员工信息已更新", data={"employeeId": employee_id})


@on(HR_EMPLOYEE_DELETED)
async def _on_employee_deleted(employee_ids: list[int], **kwargs):
    radar_log("HR事件: 员工已删除（软删除）", data={"employeeIds": employee_ids})


@on(HR_EMPLOYEE_STATUS_CHANGED)
async def _on_status_changed(employee_id: int, from_state: str, to_state: str, **kwargs):
    radar_log("HR事件: 员工状态变更", data={"employeeId": employee_id, "fromState": from_state, "toState": to_state})
