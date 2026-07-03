"""
HR controllers — 基于 CRUDBase 的控制器。
"""

from app.business.hr.models import Department, Employee, EmployeeStatusLog, Tag
from app.utils import CRUDBase

department_controller = CRUDBase(model=Department)
tag_controller = CRUDBase(model=Tag)
employee_controller = CRUDBase(model=Employee)
status_log_controller = CRUDBase(model=EmployeeStatusLog)
