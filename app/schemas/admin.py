from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.models.system import IconType, MenuType, StatusType

# ============================================================
# Role Schemas
# ============================================================


class RoleBase(BaseModel):
    role_name: Annotated[str | None, Field(alias="roleName", title="角色名称")] = None
    role_code: Annotated[str | None, Field(alias="roleCode", title="角色编码")] = None
    role_desc: Annotated[str | None, Field(alias="roleDesc", title="角色描述")] = None
    by_role_home_id: Annotated[int | None, Field(alias="byRoleHomeId", title="角色首页")] = None
    status_type: Annotated[StatusType | None, Field(alias="statusType", title="角色状态")] = None

    class Config:
        allow_extra = True
        populate_by_name = True


class RoleCreate(RoleBase):
    role_name: Annotated[str, Field(alias="roleName", title="角色名称")]
    role_code: Annotated[str, Field(alias="roleCode", title="角色编码")]


class RoleUpdate(RoleBase): ...


class RoleUpdateAuthrization(BaseModel):
    by_role_home_id: Annotated[int | None, Field(alias="byRoleHomeId", title="角色首页菜单id")] = None
    by_role_menu_ids: Annotated[list[int] | None, Field(alias="byRoleMenuIds", title="角色菜单列表")] = None
    by_role_api_ids: Annotated[list[int] | None, Field(alias="byRoleApiIds", title="角色API列表")] = None
    by_role_button_ids: Annotated[list[int] | None, Field(alias="byRoleButtonIds", title="角色按钮列表")] = None


# ============================================================
# API Schemas
# ============================================================


class BaseApi(BaseModel):
    api_path: Annotated[str | None, Field(alias="apiPath", title="请求路径", description="/api/v1/auth/login")] = None
    api_method: Annotated[str | None, Field(alias="apiMethod", title="请求方法", description="GET")] = None
    summary: Annotated[str | None, Field(title="API简介")] = None
    tags: Annotated[list[str] | None, Field(title="API标签")] = None
    status_type: Annotated[StatusType | None, Field(alias="statusType", title="API状态")] = None

    class Config:
        populate_by_name = True


class ApiSearch(BaseApi):
    current: Annotated[int | None, Field(title="页码")] = 1
    size: Annotated[int | None, Field(title="每页数量")] = 10


class ApiCreate(BaseApi):
    api_path: Annotated[str, Field(alias="apiPath", title="请求路径", description="/api/v1/auth/login")]
    api_method: Annotated[str, Field(alias="apiMethod", title="请求方法", description="GET")]


class ApiUpdate(BaseApi): ...


# ============================================================
# Menu Schemas
# ============================================================


class ButtonBase(BaseModel):
    button_code: Annotated[str | None, Field(alias="buttonCode", title="按钮编码")] = None
    button_desc: Annotated[str | None, Field(alias="buttonDesc", title="按钮描述")] = None

    class Config:
        allow_extra = True
        populate_by_name = True


class MenuBase(BaseModel):
    menu_name: Annotated[str | None, Field(alias="menuName", max_length=200, title="菜单名称")] = None
    menu_type: Annotated[MenuType | None, Field(alias="menuType", max_length=200, title="菜单类型")] = None
    route_name: Annotated[str | None, Field(max_length=200, alias="routeName", title="路由名称")] = None
    route_path: Annotated[str | None, Field(max_length=200, alias="routePath", title="路由路径")] = None

    path_param: Annotated[str | None, Field(max_length=200, alias="pathParam", description="路径参数")] = None
    route_param: Annotated[list[dict[str, Any]] | None, Field(alias="query", description="路由参数列表")] = []
    by_menu_buttons: Annotated[list[ButtonBase] | None, Field(alias="byMenuButtons", description="按钮列表")] = []
    order: Annotated[int | None, Field(description="菜单顺序")] = None
    component: Annotated[str | None, Field(description="路由组件")] = None

    parent_id: Annotated[int | None, Field(alias="parentId", description="父菜单ID")] = None
    i18n_key: Annotated[str | None, Field(alias="i18nKey", description="用于国际化的展示文本，优先级高于title")] = None

    icon: Annotated[str | None, Field(description="图标名称")] = None
    icon_type: Annotated[IconType | None, Field(alias="iconType", description="图标类型")] = None

    href: Annotated[str | None, Field(description="外链")] = None
    multi_tab: Annotated[bool | None, Field(alias="multiTab", description="是否支持多页签")] = None
    keep_alive: Annotated[bool | None, Field(alias="keepAlive", description="是否缓存")] = None
    hide_in_menu: Annotated[bool | None, Field(alias="hideInMenu", description="是否在菜单隐藏")] = None
    active_menu: Annotated[str | None, Field(alias="activeMenu", description="隐藏的路由需要激活的菜单")] = None
    fixed_index_in_tab: Annotated[int | None, Field(alias="fixedIndexInTab", description="固定在页签的序号")] = None
    status: Annotated[str | None, Field(description="状态")] = None

    redirect: Annotated[str | None, Field(description="重定向路径")] = None
    props: Annotated[bool | None, Field(description="是否为首路由")] = None
    constant: Annotated[bool | None, Field(description="是否为公共路由")] = None

    class Config:
        allow_extra = True
        populate_by_name = True


class MenuCreate(MenuBase):
    menu_name: Annotated[str, Field(alias="menuName", max_length=200, title="菜单名称")]
    menu_type: Annotated[MenuType, Field(alias="menuType", max_length=200, title="菜单类型")]
    route_name: Annotated[str, Field(max_length=200, alias="routeName", title="路由名称")]
    route_path: Annotated[str, Field(max_length=200, alias="routePath", title="路由路径")]


class MenuUpdate(MenuBase): ...


__all__ = [
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RoleUpdateAuthrization",
    "BaseApi",
    "ApiSearch",
    "ApiCreate",
    "ApiUpdate",
    "ButtonBase",
    "MenuBase",
    "MenuCreate",
    "MenuUpdate",
]
