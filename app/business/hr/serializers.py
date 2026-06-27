from __future__ import annotations

from typing import TYPE_CHECKING

from app.utils import encode_id

if TYPE_CHECKING:
    from app.business.hr.models import Employee


async def employee_record(
    emp: Employee,
    *,
    exclude_fields: list[str] | None = None,
    department_name: bool = False,
    tag_ids: bool = False,
    tag_names: bool = False,
    tags: bool = False,
) -> dict:
    """Serialize an employee with optional relation display fields."""
    record = await emp.to_dict(exclude_fields=exclude_fields)

    # 这些字段依赖调用方已经 select_related / prefetch_related，避免序列化层隐式 N+1。
    if department_name:
        record["departmentName"] = emp.department.name
    if tag_ids:
        record["tagIds"] = [encode_id(tag.id) for tag in emp.tags]
    if tag_names:
        record["tagNames"] = [tag.name for tag in emp.tags]
    if tags:
        record["tags"] = [await tag.to_dict() for tag in emp.tags]

    return record
