from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="健康检测", include_in_schema=False)
async def health_check():
    """健康检测接口，用于 Docker/K8s 探针"""
    return {"status": "ok"}
