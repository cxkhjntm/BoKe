from fastapi import APIRouter

from backend.utils.response import ok

router = APIRouter(prefix="/api/v1/milvus", tags=["milvus"])


@router.get("/status")
def milvus_status():
    """TODO: Milvus integration (stage 3)"""
    return ok(data={"status": "not_configured"})
