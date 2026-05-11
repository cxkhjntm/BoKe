import json

from types import SimpleNamespace

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.config import CHAT_MAX_MESSAGE_LENGTH
from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.models.chat_session import ChatSession
from backend.models.llm_config import LLMConfig
from backend.schemas.chat import ChatMessageCreate
from backend.services.chat_service import stream_chat_session
from backend.utils.response import ok
from backend.exceptions.handlers import AppException
from backend.utils.logger import get_logger

logger = get_logger("chat")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.get("/messages/{session_id}")
def get_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    from backend.services.chat_storage import load_messages

    messages = load_messages(current_user.id, session_id)
    return ok(data={"session_id": session_id, "messages": messages})


@router.post("/messages/{session_id}")
async def post_message(
    session_id: str,
    body: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Verify session belongs to user
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise AppException(code=4004, message="Session not found", status_code=404)

    # 2. Verify message length
    if len(body.content) > CHAT_MAX_MESSAGE_LENGTH:
        raise AppException(code=4008, message="Message too long", status_code=400)

    # 3. Verify user has LLM config (prefer active, fallback to first)
    config = db.query(LLMConfig).filter(
        LLMConfig.user_id == current_user.id,
        LLMConfig.is_active == 1
    ).first()
    if not config:
        config = db.query(LLMConfig).filter(LLMConfig.user_id == current_user.id).first()
    if not config:
        raise AppException(code=4005, message="LLM config not set", status_code=400)

    # 4. Auto-update session title if it's still the default "新会话"
    if session.title == "新会话":
        title_text = body.content.strip()
        if len(title_text) > 10:
            session.title = title_text[:10] + "..."
        else:
            session.title = title_text
        db.commit()
        db.refresh(session)

    # 5. Extract config values BEFORE the async generator to avoid detached instance error.
    #    After db.commit(), SQLAlchemy expires all ORM objects (expire_on_commit=True default).
    #    Accessing config.api_key inside the generator would trigger a lazy-refresh on a
    #    potentially-closed session, causing "Instance is not bound to a Session" error.
    llm_config = SimpleNamespace(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
    )

    # 6. Read max_rounds
    max_rounds = current_user.max_rounds or 0

    async def event_generator():
        yield {
            "event": "start",
            "data": json.dumps({"type": "start", "session_id": session_id}),
        }
        try:
            full_content = ""
            async for delta in stream_chat_session(
                current_user.id, session_id, body.content, llm_config, max_rounds
            ):
                full_content += delta
                yield {
                    "event": "delta",
                    "data": json.dumps({"type": "delta", "content": delta}),
                }
            yield {
                "event": "finish",
                "data": json.dumps({"type": "finish", "content": full_content}),
            }
        except Exception as e:
            logger.exception("Chat stream error")
            yield {
                "event": "error",
                "data": json.dumps({"type": "error", "message": str(e)}),
            }

    return EventSourceResponse(event_generator())
