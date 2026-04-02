import pretty_errors
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import MultipleObjectsReturned

from app.api import api_router
from app.controllers import role_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.core.middlewares import BackGroundTaskMiddleware, PrettyErrorsMiddleware, RequestIDMiddleware
from app.models.system import Api, Button, IconType, Menu, MenuType, Role, StatusType, User
from app.settings import APP_SETTINGS


async def _guard_response_modifier(response):
    """Rewrite guard error responses to the project's unified JSON format."""
    import orjson
    from starlette.responses import Response

    from app.core.code import Code

    status = response.status_code
    if status < 400:
        return response
    if status == 429:
        code, msg = Code.RATE_LIMITED, "请求过于频繁，请稍后再试"
    elif status == 403 and b"banned" in (response.body or b"").lower():
        code, msg = Code.IP_BANNED, "IP已被封禁，请稍后再试"
    elif status == 403:
        code, msg = Code.ACCESS_DENIED, "访问被拒绝"
    else:
        code, msg = Code.ACCESS_DENIED, "请求被安全策略拦截"
    body = orjson.dumps({"code": code, "msg": msg, "data": None})
    response._response = Response(content=body, status_code=200, media_type="application/json")
    return response


def _make_guard_config():
    """Create fastapi-guard SecurityConfig from app settings."""
    from guard import SecurityConfig

    return SecurityConfig(
        rate_limit=APP_SETTINGS.GUARD_RATE_LIMIT,
        rate_limit_window=APP_SETTINGS.GUARD_RATE_LIMIT_WINDOW,
        auto_ban_threshold=APP_SETTINGS.GUARD_AUTO_BAN_THRESHOLD,
        auto_ban_duration=APP_SETTINGS.GUARD_AUTO_BAN_DURATION,
        enable_redis=True,
        redis_url=APP_SETTINGS.REDIS_URL,
        enable_cors=False,  # CORS already handled by CORSMiddleware
        enforce_https=False,
        security_headers=None,  # Let nginx handle security headers
        custom_log_file=str(APP_SETTINGS.LOGS_ROOT / "guard.log"),
        custom_response_modifier=_guard_response_modifier,
        exclude_paths=["/docs", "/redoc", "/openapi.json", "/favicon.ico", "/static"],
        endpoint_rate_limits={
            "/api/v1/auth/login": (5, 60),  # 5 requests per 60 seconds
            "/api/v1/auth/refresh-token": (10, 60),  # 10 requests per 60 seconds
        },
    )


def make_middlewares():
    middleware = [
        Middleware(
            PrettyErrorsMiddleware,
            line_number_first=True,
            lines_before=5,
            lines_after=2,
            line_color=pretty_errors.RED + "> " + pretty_errors.default_config.line_color,
            code_color="  " + pretty_errors.default_config.line_color,
            truncate_code=True,
            display_locals=True,
            filename_display=pretty_errors.FILENAME_EXTENDED,
        ),
        Middleware(
            CORSMiddleware,
            allow_origins=APP_SETTINGS.CORS_ORIGINS,
            allow_credentials=APP_SETTINGS.CORS_ALLOW_CREDENTIALS,
            allow_methods=APP_SETTINGS.CORS_ALLOW_METHODS,
            allow_headers=APP_SETTINGS.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(RequestIDMiddleware),
    ]
    if APP_SETTINGS.GUARD_ENABLED:
        from guard.middleware import SecurityMiddleware

        middleware.append(Middleware(SecurityMiddleware, config=_make_guard_config()))

    if APP_SETTINGS.RADAR_ENABLED:
        from app.radar.middleware import RadarMiddleware

        middleware.append(Middleware(RadarMiddleware))
    return middleware


def register_db(app: FastAPI):
    register_tortoise(
        app,
        config=APP_SETTINGS.TORTOISE_ORM,
        generate_schemas=True,
    )


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)  # type: ignore
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)  # type: ignore
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)  # type: ignore


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def modify_db():
    from tortoise.migrations.api.migrate import migrate

    try:
        await migrate(config=APP_SETTINGS.TORTOISE_ORM, app_labels=["app_system"])
    except Exception:
        ...


async def init_menus():
    menus = await Menu.exists()
    if menus:
        return

    constant_menu = [
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="login",
            route_name="login",
            route_path="/login",
            component="layout.blank$view.login",
            order=1,
            i18n_key="route.login",
            props=True,
            constant=True,
            hide_in_menu=True,
        ),
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="403",
            route_name="403",
            route_path="/403",
            component="layout.blank$view.403",
            order=2,
            i18n_key="route.403",
            constant=True,
            hide_in_menu=True,
        ),
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="404",
            route_name="404",
            route_path="/404",
            component="layout.blank$view.404",
            order=3,
            i18n_key="route.404",
            constant=True,
            hide_in_menu=True,
        ),
        Menu(
            status=StatusType.enable,
            parent_id=0,
            menu_type=MenuType.catalog,
            menu_name="500",
            route_name="500",
            route_path="/500",
            component="layout.blank$view.500",
            order=4,
            i18n_key="route.500",
            constant=True,
            hide_in_menu=True,
        ),
    ]
    await Menu.bulk_create(constant_menu)

    # 1
    await Menu.create(
        status=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.menu,
        menu_name="首页",
        route_name="home",
        route_path="/home",
        component="layout.base$view.home",
        order=1,
        i18n_key="route.home",
        icon="mdi:monitor-dashboard",
        icon_type=IconType.iconify,
    )
    await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.menu,
        menu_name="关于",
        route_name="about",
        route_path="/about",
        component="layout.base$view.about",
        order=99,
        i18n_key="route.about",
        icon="fluent:book-information-24-regular",
        icon_type=IconType.iconify,
    )

    # 2
    root_menu = await Menu.create(
        status=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="功能",
        route_name="function",
        route_path="/function",
        component="layout.base",
        order=2,
        i18n_key="route.function",
        icon="icon-park-outline:all-application",
        icon_type=IconType.iconify,
    )

    parent_menu = await Menu.create(
        status=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.menu,
        menu_name="切换权限",
        route_name="function_toggle-auth",
        route_path="/function/toggle-auth",
        component="view.function_toggle-auth",
        order=4,
        i18n_key="route.function_toggle-auth",
        icon="ic:round-construction",
        icon_type=IconType.iconify,
    )

    button_code1 = await Button.create(button_code="B_CODE1", button_desc="超级管理员可见")
    await parent_menu.by_menu_buttons.add(button_code1)
    button_code2 = await Button.create(button_code="B_CODE2", button_desc="管理员可见")
    await parent_menu.by_menu_buttons.add(button_code2)
    button_code3 = await Button.create(button_code="B_CODE3", button_desc="管理员和用户可见")
    await parent_menu.by_menu_buttons.add(button_code3)
    await parent_menu.save()

    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="请求",
            route_name="function_request",
            route_path="/function/request",
            component="view.function_request",
            order=3,
            i18n_key="route.function_request",
            icon="carbon:network-overlay",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="超级管理员可见",
            route_name="function_super-page",
            route_path="/function/super-page",
            component="view.function_super-page",
            order=5,
            i18n_key="route.function_super-page",
            icon="ic:round-supervisor-account",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="标签页",
            route_name="function_tab",
            route_path="/function/tab",
            component="view.function_tab",
            order=2,
            i18n_key="route.function_tab",
            icon="ic:round-tab",
            icon_type=IconType.iconify,
        ),
    ]
    await Menu.bulk_create(children_menu)
    await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.menu,
        menu_name="多标签页",
        route_name="function_multi-tab",
        route_path="/function/multi-tab",
        component="view.function_multi-tab",
        order=1,
        i18n_key="route.function_multi-tab",
        icon="ic:round-tab",
        icon_type=IconType.iconify,
        multi_tab=True,
        hide_in_menu=True,
        active_menu=await Menu.get(route_name="function_tab"),
    )

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.catalog,
        menu_name="隐藏子菜单",
        route_name="function_hide-child",
        route_path="/function/hide-child",
        redirect="/function/hide-child/one",
        order=2,
        i18n_key="route.function_hide-child",
        icon="material-symbols:filter-list-off",
        icon_type=IconType.iconify,
    )

    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=parent_menu.id,
            menu_type=MenuType.menu,
            menu_name="隐藏子菜单1",
            route_name="function_hide-child_one",
            route_path="/function/hide-child/one",
            component="view.function_hide-child_one",
            order=1,
            i18n_key="route.function_hide-child_one",
            icon="material-symbols:filter-list-off",
            icon_type=IconType.iconify,
            hide_in_menu=True,
            active_menu=parent_menu,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=parent_menu.id,
            menu_type=MenuType.menu,
            menu_name="隐藏子菜单2",
            route_name="function_hide-child_two",
            route_path="/function/hide-child/two",
            component="view.function_hide-child_two",
            order=2,
            i18n_key="route.function_hide-child_two",
            hide_in_menu=True,
            active_menu=parent_menu,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=parent_menu.id,
            menu_type=MenuType.menu,
            menu_name="隐藏子菜单3",
            route_name="function_hide-child_three",
            route_path="/function/hide-child/three",
            component="view.function_hide-child_three",
            order=3,
            i18n_key="route.function_hide-child_three",
            hide_in_menu=True,
            active_menu=parent_menu,
        ),
    ]
    await Menu.bulk_create(children_menu)

    # 5
    root_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="异常页",
        route_name="exception",
        route_path="/exception",
        component="layout.base",
        order=3,
        i18n_key="route.exception",
        icon="ant-design:exception-outlined",
        icon_type=IconType.iconify,
    )
    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="403",
            route_name="exception_403",
            route_path="/exception/403",
            component="view.403",
            order=1,
            i18n_key="route.exception_403",
            icon="ic:baseline-block",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="404",
            route_name="exception_404",
            route_path="/exception/404",
            component="view.404",
            order=2,
            i18n_key="route.exception_404",
            icon="ic:baseline-web-asset-off",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="500",
            route_name="exception_500",
            route_path="/exception/500",
            component="view.500",
            order=3,
            i18n_key="route.exception_500",
            icon="ic:baseline-wifi-off",
            icon_type=IconType.iconify,
        ),
    ]
    await Menu.bulk_create(children_menu)

    # 6
    root_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="alova示例",
        route_name="alova",
        route_path="/alova",
        component="layout.base",
        order=7,
        i18n_key="route.alova",
        icon="carbon:http",
        icon_type=IconType.iconify,
    )
    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="alova_request",
            route_name="alova_request",
            route_path="/alova/request",
            component="view.alova_request",
            order=1,
            i18n_key="route.alova_request",
            icon="ic:baseline-block",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="alova_scenes",
            route_name="alova_scenes",
            route_path="/alova/scenes",
            component="view.alova_scenes",
            order=2,
            i18n_key="route.alova_scenes",
            icon="cbi:scene-dynamic",
            icon_type=IconType.iconify,
        ),
    ]
    await Menu.bulk_create(children_menu)

    # 插件示例1

    # 7
    root_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="插件示例",
        route_name="plugin",
        route_path="/plugin",
        component="layout.base",
        order=7,
        i18n_key="route.plugin",
        icon="clarity:plugin-line",
        icon_type=IconType.iconify,
    )

    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_barcode",
            route_name="plugin_barcode",
            route_path="/plugin/barcode",
            component="view.plugin_barcode",
            order=1,
            i18n_key="route.plugin_barcode",
            icon="ic:round-barcode",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_charts",
            route_name="plugin_charts",
            route_path="/plugin/charts",
            component=None,  # No component specified for the parent
            order=2,
            i18n_key="route.plugin_charts",
            icon="mdi:chart-areaspline",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_copy",
            route_name="plugin_copy",
            route_path="/plugin/copy",
            component="view.plugin_copy",
            order=3,
            i18n_key="route.plugin_copy",
            icon="mdi:clipboard-outline",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_editor",
            route_name="plugin_editor",
            route_path="/plugin/editor",
            component=None,  # No component specified for the parent
            order=4,
            i18n_key="route.plugin_editor",
            icon="icon-park-outline:editor",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_excel",
            route_name="plugin_excel",
            route_path="/plugin/excel",
            component="view.plugin_excel",
            order=5,
            i18n_key="route.plugin_excel",
            icon="ri:file-excel-2-line",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_gantt",
            route_name="plugin_gantt",
            route_path="/plugin/gantt",
            component=None,  # No component specified for the parent
            order=6,
            i18n_key="route.plugin_gantt",
            icon="ant-design:bar-chart-outlined",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_icon",
            route_name="plugin_icon",
            route_path="/plugin/icon",
            component="view.plugin_icon",
            order=7,
            i18n_key="route.plugin_icon",
            icon="custom-icon",
            icon_type=IconType.local,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_map",
            route_name="plugin_map",
            route_path="/plugin/map",
            component="view.plugin_map",
            order=8,
            i18n_key="route.plugin_map",
            icon="mdi:map",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_pdf",
            route_name="plugin_pdf",
            route_path="/plugin/pdf",
            component="view.plugin_pdf",
            order=9,
            i18n_key="route.plugin_pdf",
            icon="uiw:file-pdf",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_pinyin",
            route_name="plugin_pinyin",
            route_path="/plugin/pinyin",
            component="view.plugin_pinyin",
            order=10,
            i18n_key="route.plugin_pinyin",
            icon="entypo-social:google-hangouts",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_print",
            route_name="plugin_print",
            route_path="/plugin/print",
            component="view.plugin_print",
            order=11,
            i18n_key="route.plugin_print",
            icon="mdi:printer",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_swiper",
            route_name="plugin_swiper",
            route_path="/plugin/swiper",
            component="view.plugin_swiper",
            order=12,
            i18n_key="route.plugin_swiper",
            icon="simple-icons:swiper",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_tables",
            route_name="plugin_tables",
            route_path="/plugin/tables",
            component=None,  # No component specified for the parent
            order=13,
            i18n_key="route.plugin_tables",
            icon="icon-park-outline:table",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_typeit",
            route_name="plugin_typeit",
            route_path="/plugin/typeit",
            component="view.plugin_typeit",
            order=14,
            i18n_key="route.plugin_typeit",
            icon="mdi:typewriter",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_video",
            route_name="plugin_video",
            route_path="/plugin/video",
            component="view.plugin_video",
            order=15,
            i18n_key="route.plugin_video",
            icon="mdi:video",
            icon_type=IconType.iconify,
        ),
    ]

    # Bulk create all child menus
    await Menu.bulk_create(children_menu)

    # Now, handle the nested children for 'plugin_charts' and 'plugin_editor' separately

    plugin_charts_menu = await Menu.get(route_name="plugin_charts")
    plugin_charts_children = [
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_charts_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_charts_antv",
            route_name="plugin_charts_antv",
            route_path="/plugin/charts/antv",
            component="view.plugin_charts_antv",
            order=1,
            i18n_key="route.plugin_charts_antv",
            icon="hugeicons:flow-square",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_charts_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_charts_echarts",
            route_name="plugin_charts_echarts",
            route_path="/plugin/charts/echarts",
            component="view.plugin_charts_echarts",
            order=2,
            i18n_key="route.plugin_charts_echarts",
            icon="simple-icons:apacheecharts",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_charts_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_charts_vchart",
            route_name="plugin_charts_vchart",
            route_path="/plugin/charts/vchart",
            component="view.plugin_charts_vchart",
            order=3,
            i18n_key="route.plugin_charts_vchart",
            icon="visactor",
            icon_type=IconType.local,
        ),
    ]

    await Menu.bulk_create(plugin_charts_children)

    # Nested children for 'plugin_editor'
    plugin_editor_menu = await Menu.get(route_name="plugin_editor")
    plugin_editor_children = [
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_editor_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_editor_markdown",
            route_name="plugin_editor_markdown",
            route_path="/plugin/editor/markdown",
            component="view.plugin_editor_markdown",
            order=1,
            i18n_key="route.plugin_editor_markdown",
            icon="ri:markdown-line",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_editor_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_editor_quill",
            route_name="plugin_editor_quill",
            route_path="/plugin/editor/quill",
            component="view.plugin_editor_quill",
            order=2,
            i18n_key="route.plugin_editor_quill",
            icon="mdi:file-document-edit-outline",
            icon_type=IconType.iconify,
        ),
    ]

    # Bulk create editor children
    await Menu.bulk_create(plugin_editor_children)

    # Nested children for 'plugin_gantt'
    plugin_gantt_menu = await Menu.get(route_name="plugin_gantt")
    plugin_gantt_children = [
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_gantt_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_gantt_dhtmlx",
            route_name="plugin_gantt_dhtmlx",
            route_path="/plugin/gantt/dhtmlx",
            component="view.plugin_gantt_dhtmlx",
            order=1,
            i18n_key="route.plugin_gantt_dhtmlx",
            icon=None,  # No icon specified
            icon_type=None,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_gantt_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_gantt_vtable",
            route_name="plugin_gantt_vtable",
            route_path="/plugin/gantt/vtable",
            component="view.plugin_gantt_vtable",
            order=2,
            i18n_key="route.plugin_gantt_vtable",
            icon="visactor",
            icon_type=IconType.local,
        ),
    ]

    # Bulk create gantt children
    await Menu.bulk_create(plugin_gantt_children)

    # Nested children for 'plugin_tables'
    plugin_tables_menu = await Menu.get(route_name="plugin_tables")
    plugin_tables_children = [
        Menu(
            status_type=StatusType.enable,
            parent_id=plugin_tables_menu.id,
            menu_type=MenuType.menu,
            menu_name="plugin_tables_vtable",
            route_name="plugin_tables_vtable",
            route_path="/plugin/tables/vtable",
            component="view.plugin_tables_vtable",
            order=1,
            i18n_key="route.plugin_tables_vtable",
            icon="visactor",
            icon_type=IconType.local,
        ),
    ]

    # Bulk create tables children
    await Menu.bulk_create(plugin_tables_children)

    # 插件示例2

    # 9
    root_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="多级菜单",
        route_name="multi-menu",
        route_path="/multi-menu",
        component="layout.base",
        order=4,
        i18n_key="route.multi-menu",
        icon="mdi:menu",
        icon_type=IconType.iconify,
    )
    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.catalog,
        menu_name="一级子菜单1",
        route_name="multi-menu_first",
        route_path="/multi-menu/first",
        order=1,
        i18n_key="route.multi-menu_first",
        icon="mdi:menu",
        icon_type=IconType.iconify,
    )
    await Menu.create(
        status_type=StatusType.enable,
        parent_id=parent_menu.id,
        menu_type=MenuType.menu,
        menu_name="二级子菜单",
        route_name="multi-menu_first_child",
        route_path="/multi-menu/first/child",
        component="view.multi-menu_first_child",
        order=1,
        i18n_key="route.multi-menu_first_child",
        icon="mdi:menu",
        icon_type=IconType.iconify,
    )

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.catalog,
        menu_name="一级子菜单2",
        route_name="multi-menu_second",
        route_path="/multi-menu/second",
        order=13,
        i18n_key="route.multi-menu_second",
        icon="mdi:menu",
        icon_type=IconType.iconify,
    )

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=parent_menu.id,
        menu_type=MenuType.catalog,
        menu_name="二级子菜单2",
        route_name="multi-menu_second_child",
        route_path="/multi-menu/second/child",
        order=1,
        i18n_key="route.multi-menu_second_child",
        icon="mdi:menu",
        icon_type=IconType.iconify,
    )

    await Menu.create(
        status_type=StatusType.enable,
        parent_id=parent_menu.id,
        menu_type=MenuType.menu,
        menu_name="三级菜单",
        route_name="multi-menu_second_child_home",
        route_path="/multi-menu/second/child/home",
        component="view.multi-menu_second_child_home",
        order=1,
        i18n_key="route.multi-menu_second_child_home",
        icon="mdi:menu",
        icon_type=IconType.iconify,
    )

    # 16
    root_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=0,
        menu_type=MenuType.catalog,
        menu_name="系统管理",
        route_name="manage",
        route_path="/manage",
        component="layout.base",
        order=5,
        i18n_key="route.manage",
        icon="carbon:cloud-service-management",
        icon_type=IconType.iconify,
    )

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.menu,
        menu_name="日志管理",
        route_name="manage_log",
        route_path="/manage/log",
        component="view.manage_log",
        order=1,
        i18n_key="route.manage_log",
        icon="material-symbols:list-alt-outline",
        icon_type=IconType.iconify,
    )
    button_add_del_batch_del = await Button.create(button_code="B_Add_Del_Batch-del", button_desc="新增_删除_批量删除")

    await parent_menu.by_menu_buttons.add(button_add_del_batch_del)
    await parent_menu.save()

    parent_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.menu,
        menu_name="API管理",
        route_name="manage_api",
        route_path="/manage/api",
        component="view.manage_api",
        order=2,
        i18n_key="route.manage_api",
        icon="ant-design:api-outlined",
        icon_type=IconType.iconify,
    )
    button_refreshAPI = await Button.create(button_code="B_refreshAPI", button_desc="刷新API")

    await parent_menu.by_menu_buttons.add(button_refreshAPI)
    await parent_menu.save()

    children_menu = [
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="用户管理",
            route_name="manage_user",
            route_path="/manage/user",
            component="view.manage_user",
            order=3,
            i18n_key="route.manage_user",
            icon="ic:round-manage-accounts",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="角色管理",
            route_name="manage_role",
            route_path="/manage/role",
            component="view.manage_role",
            order=4,
            i18n_key="route.manage_role",
            icon="carbon:user-role",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="菜单管理",
            route_name="manage_menu",
            route_path="/manage/menu",
            component="view.manage_menu",
            order=5,
            i18n_key="route.manage_menu",
            icon="material-symbols:route",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=root_menu.id,
            menu_type=MenuType.menu,
            menu_name="用户详情",
            route_name="manage_user-detail",
            route_path="/manage/user-detail/:id",
            component="view.manage_user-detail",
            order=6,
            i18n_key="route.manage_user-detail",
            hide_in_menu=True,
        ),
    ]
    await Menu.bulk_create(children_menu)

    # Radar 性能监控
    radar_menu = await Menu.create(
        status_type=StatusType.enable,
        parent_id=root_menu.id,
        menu_type=MenuType.catalog,
        menu_name="性能监控",
        route_name="manage_radar",
        route_path="/manage/radar",
        order=7,
        i18n_key="route.manage_radar",
        icon="mdi:radar",
        icon_type=IconType.iconify,
    )
    radar_children = [
        Menu(
            status_type=StatusType.enable,
            parent_id=radar_menu.id,
            menu_type=MenuType.menu,
            menu_name="仪表板",
            route_name="manage_radar_overview",
            route_path="/manage/radar/overview",
            component="view.manage_radar_overview",
            order=1,
            i18n_key="route.manage_radar_overview",
            icon="mdi:chart-box-outline",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=radar_menu.id,
            menu_type=MenuType.menu,
            menu_name="请求列表",
            route_name="manage_radar_requests",
            route_path="/manage/radar/requests",
            component="view.manage_radar_requests",
            order=2,
            i18n_key="route.manage_radar_requests",
            icon="mdi:swap-horizontal",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=radar_menu.id,
            menu_type=MenuType.menu,
            menu_name="SQL查询",
            route_name="manage_radar_queries",
            route_path="/manage/radar/queries",
            component="view.manage_radar_queries",
            order=3,
            i18n_key="route.manage_radar_queries",
            icon="mdi:database-search",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=radar_menu.id,
            menu_type=MenuType.menu,
            menu_name="异常列表",
            route_name="manage_radar_exceptions",
            route_path="/manage/radar/exceptions",
            component="view.manage_radar_exceptions",
            order=4,
            i18n_key="route.manage_radar_exceptions",
            icon="mdi:bug-outline",
            icon_type=IconType.iconify,
        ),
        Menu(
            status_type=StatusType.enable,
            parent_id=radar_menu.id,
            menu_type=MenuType.menu,
            menu_name="系统监控",
            route_name="manage_radar_monitor",
            route_path="/manage/radar/monitor",
            component="view.manage_radar_monitor",
            order=5,
            i18n_key="route.manage_radar_monitor",
            icon="mdi:monitor-dashboard",
            icon_type=IconType.iconify,
        ),
    ]
    await Menu.bulk_create(radar_children)


async def insert_role(children_role: list[Role], role_apis: list[tuple[str, str]] = None, role_menus: list[str] = None, role_buttons: list[str] = None):
    if role_apis is None:
        role_apis = []
    if role_menus is None:
        role_menus = []
    if role_buttons is None:
        role_buttons = []

    on_conflict = ("role_code",)
    update_fields = ("role_name", "role_desc")

    await Role.bulk_create(children_role, on_conflict=on_conflict, update_fields=update_fields)

    for role_zs in children_role:
        role_obj = await Role.get(role_code=role_zs.role_code)
        for api_method, api_path in role_apis:
            try:
                api_obj: Api = await Api.get(api_method=api_method, api_path=api_path)
                await role_obj.by_role_apis.add(api_obj)
            except DoesNotExist:
                print("不存在API", api_method, api_path)
                return False

        for route_name in role_menus:
            try:
                menu_obj: Menu = await Menu.get(route_name=route_name)
                await role_obj.by_role_menus.add(menu_obj)
            except MultipleObjectsReturned:
                print("多个菜单", route_name)
                return False

        for button_code in role_buttons:
            button_obj: Button = await Button.get(button_code=button_code)
            await role_obj.by_role_buttons.add(button_obj)

        await role_obj.save()
    return True


async def init_users():
    role_exist = await role_controller.model.exists()
    if not role_exist:
        role_home_menu = await Menu.get(route_name="home")
        # 超级管理员拥有所有菜单 所有按钮
        super_role_obj = await Role.create(role_name="超级管理员", role_code="R_SUPER", role_desc="超级管理员", by_role_home=role_home_menu)
        role_super_menu_objs = await Menu.filter(constant=False)  # 过滤常量路由(公共路由)
        for menu_obj in role_super_menu_objs:
            await super_role_obj.by_role_menus.add(menu_obj)
        for button_obj in await Button.all():
            await super_role_obj.by_role_buttons.add(button_obj)

        # 管理员拥有 首页 关于 插件示例(全部) 多级菜单(全部) 系统管理-用户管理 系统管理-用户详情
        role_admin = await Role.create(role_name="管理员", role_code="R_ADMIN", role_desc="管理员", by_role_home=role_home_menu)

        role_admin_apis = [
            ("post", "/api/v1/system-manage/users/all/"),
            ("get", "/api/v1/system-manage/users/{item_id}"),
            ("get", "/api/v1/system-manage/roles"),
            ("post", "/api/v1/system-manage/users"),
            ("patch", "/api/v1/system-manage/users/{user_id}"),
            ("delete", "/api/v1/system-manage/users/{user_id}"),
            ("delete", "/api/v1/system-manage/users"),
        ]
        role_admin_menus = [
            "home",
            "about",
            # 插件示例
            "plugin",
            "plugin_barcode",
            "plugin_charts",
            "plugin_charts_antv",
            "plugin_charts_echarts",
            "plugin_charts_vchart",
            "plugin_copy",
            "plugin_editor",
            "plugin_editor_markdown",
            "plugin_editor_quill",
            "plugin_excel",
            "plugin_gantt",
            "plugin_gantt_dhtmlx",
            "plugin_gantt_vtable",
            "plugin_icon",
            "plugin_map",
            "plugin_pdf",
            "plugin_pinyin",
            "plugin_print",
            "plugin_swiper",
            "plugin_tables",
            "plugin_tables_vtable",
            "plugin_typeit",
            "plugin_video",
            # 多级菜单
            "multi-menu",
            "multi-menu_first",
            "multi-menu_first_child",
            "multi-menu_second",
            "multi-menu_second_child",
            "multi-menu_second_child_home",
            # 系统管理-用户管理/详情
            "manage",
            "manage_user",
            "manage_user-detail",
        ]
        role_admin_buttons = ["B_CODE2", "B_CODE3"]
        await insert_role([role_admin], role_admin_apis, role_admin_menus, role_admin_buttons)

        # 普通用户拥有 首页 关于
        role_user = await Role.create(role_name="普通用户", role_code="R_USER", role_desc="普通用户", by_role_home=role_home_menu)
        role_user_apis: list[tuple[str, str]] = []
        role_user_menus = ["home", "about"]
        role_user_buttons: list[str] = []
        await insert_role([role_user], role_user_apis, role_user_menus, role_user_buttons)

    user = await user_controller.model.exists()
    if not user:
        super_role_obj: Role | None = await role_controller.get_by_code("R_SUPER")
        user_super_obj: User = await user_controller.create(
            UserCreate(
                userName="Soybean",  # type: ignore
                userEmail="admin@admin.com",  # type: ignore
                password="123456",
            )
        )
        await user_super_obj.by_user_roles.add(super_role_obj)

        user_super_obj: User = await user_controller.create(
            UserCreate(
                userName="Super",  # type: ignore
                userEmail="admin1@admin.com",  # type: ignore
                password="123456",
            )
        )
        await user_super_obj.by_user_roles.add(super_role_obj)

        admin_role_obj: Role | None = await role_controller.get_by_code("R_ADMIN")
        user_admin_obj = await user_controller.create(
            UserCreate(
                userName="Admin",  # type: ignore
                userEmail="admin2@admin.com",  # type: ignore
                password="123456",
            )
        )
        await user_admin_obj.by_user_roles.add(admin_role_obj)

        user_role_obj: Role | None = await role_controller.get_by_code("R_USER")
        user_user_obj = await user_controller.create(
            UserCreate(
                userName="User",  # type: ignore
                userEmail="user@user.com",  # type: ignore
                password="123456",
            )
        )
        await user_user_obj.by_user_roles.add(user_role_obj)
