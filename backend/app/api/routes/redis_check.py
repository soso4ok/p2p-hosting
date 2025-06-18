from fastapi import APIRouter

from app.db.redis_connection import redis

router = APIRouter()


@router.get("/health/redis")
async def redis_health():
    try:
        pong = await redis.ping()
        return {"status": "ok", "pong": pong}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
