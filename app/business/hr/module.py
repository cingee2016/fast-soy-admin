from app.business.hr.api.manage import router as manage_router
from app.business.hr.api.my import router as my_router
from app.business.hr.api.public import router as public_router
from app.business.hr.api.team import router as team_router
from app.business.hr.events import HR_EVENTS
from app.business.hr.init_data import INIT_DATA, init
from app.business.hr.policies import HR_DATA_POLICIES
from app.utils import BusinessModule, BusinessRouter, PermissionSpec

# HR 用 manifest 显式声明业务插槽，避免 autodiscover 再从 api/__init__.py 猜路由和权限。
module = BusinessModule(
    name="hr",
    title="HR管理 Demo",
    version="1.1.0",
    routers=[
        BusinessRouter(router=manage_router, auth="permission"),
        BusinessRouter(router=my_router, auth="permission"),
        BusinessRouter(router=team_router, auth="permission"),
        BusinessRouter(router=public_router, auth="public"),
    ],
    # INIT_DATA 会被 init-plan --strict 审计，启动时再由 init() 真正写入系统表。
    init=init,
    permissions=PermissionSpec(init_data=INIT_DATA),
    events=HR_EVENTS,
    data_policies=HR_DATA_POLICIES,
)
