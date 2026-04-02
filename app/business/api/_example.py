"""
Business API route example.

Create your business API routes here. They will be auto-discovered.
Files starting with `_` are ignored by auto-discovery.

Usage:
    1. Copy this file and rename it (e.g., orders.py)
    2. Define a `router` variable (APIRouter)
    3. Restart the server - routes are auto-registered at /api/v1/business/

Example:
    from fastapi import APIRouter
    from app.utils import Success, SuccessExtra, CRUDRouter

    router = APIRouter(prefix="/orders", tags=["订单管理"])

    @router.get("/orders", summary="查看订单列表")
    async def list_orders():
        return Success(data=[])

    # Or use CRUDRouter for standard CRUD:
    # crud = CRUDRouter(
    #     prefix="/orders",
    #     controller=order_controller,
    #     create_schema=OrderCreate,
    #     update_schema=OrderUpdate,
    #     summary_prefix="订单",
    # )
    # router = crud.router
"""
