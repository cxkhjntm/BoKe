import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user, authenticate_from_token
from backend.models.user import User
from backend.models.document import Document
from backend.services import file_service
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.files")
router = APIRouter(prefix="/api/v1/files", tags=["files"])

CHUNK_SIZE = 8192


def _get_mime(file_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(file_path))
    return mime or "application/octet-stream"


def _resolve_user(
    token: Optional[str],
    current_user: Optional[User],
    db: Session,
    request: Request = None,
) -> User:
    """Resolve user from either dependency-injected JWT or query-param token."""
    if current_user:
        return current_user
    if token:
        return authenticate_from_token(token, db, request)
    raise AppException(code=4001, message="Authentication required", status_code=401)


@router.get("/{doc_id}/original")
async def serve_original(
    doc_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img/iframe auth"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)

    abs_path = file_service.get_file_path(doc.file_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="File not found on disk", status_code=404)

    file_size = abs_path.stat().st_size
    mime_type = _get_mime(abs_path)

    # Support Range requests for PDF preview
    range_header = request.headers.get("range")
    if range_header:
        return _serve_range(abs_path, file_size, mime_type, range_header, doc.original_filename)

    def file_iter():
        with open(abs_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.original_filename}"',
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


def _serve_range(abs_path: Path, file_size: int, mime_type: str, range_header: str, filename: str):
    """Handle HTTP Range request (206 Partial Content)."""
    try:
        ranges = range_header.replace("bytes=", "").split("-")
        start = int(ranges[0]) if ranges[0] else 0
        end = int(ranges[1]) if ranges[1] else file_size - 1
        if start < 0 or start > end or start >= file_size:
            start, end = 0, file_size - 1
    except (ValueError, IndexError):
        start, end = 0, file_size - 1

    end = min(end, file_size - 1)
    content_length = end - start + 1

    def range_iter():
        with open(abs_path, "rb") as f:
            f.seek(start)
            remaining = content_length
            while remaining > 0:
                chunk = f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        range_iter(),
        status_code=206,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
        },
    )


@router.get("/{doc_id}/thumbnail")
async def serve_thumbnail(
    doc_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)

    if not doc.thumbnail_path:
        raise AppException(code=4004, message="No thumbnail available", status_code=404)

    abs_path = file_service.get_file_path(doc.thumbnail_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Thumbnail not found on disk", status_code=404)

    def file_iter():
        with open(abs_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": "inline",
            "Accept-Ranges": "bytes",
        },
    )
