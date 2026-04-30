from fastapi import APIRouter

from backend.utils.response import fail

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.get("/")
def chat_placeholder():
    """TODO: LLM integration — reserved for future implementation"""
    return fail(code=5010, message="LLM integration is not available yet.")
