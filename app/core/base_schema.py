from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.tools import to_camel_case


class SchemaBase(BaseModel):
    """全局 Schema 基类：自动 snake_case → camelCase 别名"""

    model_config = ConfigDict(
        alias_generator=to_camel_case,
        validate_by_name=True,
        validate_by_alias=True,
    )


class PageQueryBase(SchemaBase):
    """分页查询基类 — 所有 POST /resources/search 接口的 body 应继承它"""

    current: int | None = Field(1, title="页码")
    size: int | None = Field(10, title="每页数量")


class Custom(JSONResponse):
    def __init__(
        self,
        code: str | int = "0000",
        status_code: int = 200,
        msg: str = "OK",
        data: Any = None,
        **kwargs,
    ):
        content = {"code": str(code), "msg": msg, "data": data}
        content.update(kwargs)
        super().__init__(content=content, status_code=status_code)


class Success(Custom):
    pass


class Fail(Custom):
    def __init__(
        self,
        code: str | int = "2400",
        msg: str = "OK",
        data: Any = None,
        **kwargs,
    ):
        super().__init__(code=code, msg=msg, data=data, status_code=200, **kwargs)


class SuccessExtra(Custom):
    def __init__(
        self,
        code: str | int = "0000",
        msg: str = "OK",
        data: Any = None,
        total: int = 0,
        current: int | None = 1,
        size: int | None = 20,
        **kwargs,
    ):
        if isinstance(data, dict):
            data.update({"total": total, "current": current, "size": size})
        super().__init__(code=code, msg=msg, data=data, status_code=200, **kwargs)


class CommonIds(SchemaBase):
    ids: list[int] = Field(title="通用ids")


class OfflineByRoleRequest(SchemaBase):
    role_codes: list[str] = Field(title="角色编码列表")
