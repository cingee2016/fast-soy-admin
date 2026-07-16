import asyncio
from fastapi import FastAPI, APIRouter, Request

app = FastAPI()
router = APIRouter()
@router.get("/test")
def test(request: Request):
    print("path_format:", request.scope["route"].path_format)
    return "ok"
app.include_router(router, prefix="/api/v1")

async def main():
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/v1/test")

asyncio.run(main())
