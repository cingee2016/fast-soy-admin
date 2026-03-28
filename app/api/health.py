from fastapi import APIRouter, Depends

from app.core.dependency import AuthControl

router = APIRouter(tags=["Health"])


@router.get("/health", summary="健康检测")
async def health_check():
    """健康检测接口，用于 Docker/K8s 探针"""
    return {"status": "ok"}


@router.get("/api/v1/test-error", summary="测试错误", tags=["Test"], dependencies=[Depends(AuthControl.is_authed)])
async def test_error():
    """测试错误接口（需鉴权），用于验证异常捕获和 Radar 监控"""
    raise RuntimeError("This is a test error for monitoring verification")
