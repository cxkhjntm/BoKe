from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db
from backend.config import STORAGE_PATH
from backend.utils.response import ok

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    # Check database
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check storage
    storage_status = "ok"
    try:
        test_file = STORAGE_PATH / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
    except Exception:
        storage_status = "error"

    # Check Redis (informational — doesn't affect overall health)
    redis_status = "not_configured"
    try:
        from backend.config import REDIS_URL
        import redis

        r = redis.from_url(REDIS_URL, socket_connect_timeout=2)
        r.ping()
        redis_status = "ok"
        r.close()
    except Exception:
        redis_status = "unavailable"

    overall = "healthy" if db_status == "ok" and storage_status == "ok" else "unhealthy"

    data = {"status": overall, "db": db_status, "storage": storage_status, "redis": redis_status}
    if overall == "healthy":
        return ok(data=data)
    return JSONResponse(
        status_code=503,
        content={"code": 5000, "message": "Service unhealthy", "data": data},
    )
