import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.models.chat_session import ChatSession
from backend.schemas.chat import ChatSessionCreate, ChatSessionUpdate, ChatSessionOut
from backend.services.chat_storage import delete_session_files
from backend.utils.response import ok
from backend.exceptions.handlers import AppException

router = APIRouter(prefix="/api/v1/chat-sessions", tags=["Chat Sessions"])


@router.get("")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return ok(data={"items": [ChatSessionOut.model_validate(s) for s in sessions]})


@router.post("")
def create_session(
    body: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = ChatSession(
        user_id=user.id,
        session_id=str(uuid.uuid4()),
        title=body.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ok(data=ChatSessionOut.model_validate(session))


@router.patch("/{session_id}")
def update_session(
    session_id: str,
    body: ChatSessionUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise AppException(code=4004, message="Session not found", status_code=404)
    session.title = body.title
    db.commit()
    db.refresh(session)
    return ok(data=ChatSessionOut.model_validate(session))


@router.delete("/{session_id}")
def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise AppException(code=4004, message="Session not found", status_code=404)
    db.delete(session)
    db.commit()
    delete_session_files(user.id, session_id)
    return ok()
