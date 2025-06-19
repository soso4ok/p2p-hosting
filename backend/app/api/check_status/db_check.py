from fastapi import APIRouter

from app.api.check_status.db_connection import test_db_connection

router = APIRouter()


@router.get("/health/db")
async def db_health():
    try:
        await test_db_connection()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
