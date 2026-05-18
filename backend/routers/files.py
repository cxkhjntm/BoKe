import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
import io
from PIL import Image

from backend.database import get_db
from backend.middleware.auth import get_current_user, get_current_user_optional, authenticate_from_token
from backend.models.user import User
from backend.models.document import Document
from backend.models.user_background import UserBackground
from backend.services import file_service
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("routers.files")
router = APIRouter(prefix="/api/v1/files", tags=["files"])

CHUNK_SIZE = 8192


def _content_disposition(filename: str) -> str:
    """Build Content-Disposition header with RFC 5987 encoding for non-ASCII filenames."""
    safe = filename.encode('ascii', 'ignore').decode()
    encoded = quote(filename)
    return f'inline; filename="{safe}"; filename*=UTF-8\'\'{encoded}'


def _get_mime(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".png": return "image/png"
    if ext in (".jpg", ".jpeg"): return "image/jpeg"
    if ext == ".gif": return "image/gif"
    if ext == ".webp": return "image/webp"
    
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
    current_user: Optional[User] = Depends(get_current_user_optional),
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
            "Content-Disposition": _content_disposition(doc.original_filename),
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Cache-Control": "no-store, no-cache, must-revalidate",
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
            "Content-Disposition": _content_disposition(filename),
            "Accept-Ranges": "bytes",
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
            "Cache-Control": "no-store, no-cache, must-revalidate",
        },
    )


@router.get("/profile/avatar")
async def serve_avatar(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    if not user.avatar_path:
        raise AppException(code=4004, message="No avatar available", status_code=404)

    abs_path = file_service.get_file_path(user.avatar_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Avatar not found on disk", status_code=404)

    return FileResponse(
        path=abs_path,
        media_type=_get_mime(abs_path),
        filename=abs_path.name,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=604800, immutable",
        }
    )


@router.get("/profile/background")
async def serve_background(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    if not user.background_path:
        raise AppException(code=4004, message="No background available", status_code=404)

    abs_path = file_service.get_file_path(user.background_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Background not found on disk", status_code=404)

    return FileResponse(
        path=abs_path,
        media_type=_get_mime(abs_path),
        filename=abs_path.name,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=604800, immutable",
        }
    )


@router.get("/profile/backgrounds/{bg_id}")
async def serve_background_by_id(
    bg_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    bg = db.query(UserBackground).filter(
        UserBackground.id == bg_id,
        UserBackground.user_id == user.id,
    ).first()
    if not bg:
        raise AppException(code=4004, message="Background not found", status_code=404)

    abs_path = file_service.get_file_path(bg.image_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Background file not found on disk", status_code=404)

    return FileResponse(
        path=abs_path,
        media_type=_get_mime(abs_path),
        filename=abs_path.name,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=604800, immutable",
        }
    )


@router.get("/profile/backgrounds/{bg_id}/thumb")
async def serve_background_thumb_by_id(
    bg_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    bg = db.query(UserBackground).filter(
        UserBackground.id == bg_id,
        UserBackground.user_id == user.id,
    ).first()
    if not bg:
        raise AppException(code=4004, message="Background not found", status_code=404)

    abs_path = file_service.get_file_path(bg.image_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Background file not found on disk", status_code=404)

    # Generate thumb path
    thumb_path = abs_path.parent / f"{abs_path.stem}_thumb.jpg"
    
    if not thumb_path.exists():
        try:
            img = Image.open(abs_path)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")
            img.thumbnail((320, 320), Image.Resampling.LANCZOS)
            img.save(thumb_path, format="JPEG", quality=75, optimize=True)
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail for {abs_path}: {e}")
            thumb_path = abs_path # Fallback to original

    return FileResponse(
        path=thumb_path,
        media_type="image/jpeg" if thumb_path != abs_path else _get_mime(abs_path),
        filename=thumb_path.name,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=604800, immutable",
        }
    )




@router.get("/profile/background")
async def serve_background(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    if not user.background_path:
        raise AppException(code=4004, message="No background available", status_code=404)

    abs_path = file_service.get_file_path(user.background_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Background not found on disk", status_code=404)

    def file_iter():
        with open(abs_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type=_get_mime(abs_path),
        headers={
            "Content-Disposition": "inline",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get("/profile/backgrounds/{bg_id}")
async def serve_background_by_id(
    bg_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    bg = db.query(UserBackground).filter(
        UserBackground.id == bg_id,
        UserBackground.user_id == user.id,
    ).first()
    if not bg:
        raise AppException(code=4004, message="Background not found", status_code=404)

    abs_path = file_service.get_file_path(bg.image_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Background file not found on disk", status_code=404)

    def file_iter():
        with open(abs_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type=_get_mime(abs_path),
        headers={
            "Content-Disposition": "inline",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get("/{doc_id}/docx_images/{image_index}")
async def serve_docx_image(
    doc_id: int,
    image_index: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Serve an extracted DOCX image by index."""
    user = _resolve_user(token, current_user, db, request)

    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)

    abs_path = file_service.get_docx_image_path(user.id, doc_id, image_index)
    if abs_path is None or not abs_path.exists():
        raise AppException(code=4004, message="Image not found", status_code=404)

    def file_iter():
        with open(abs_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type=_get_mime(abs_path),
        headers={"Content-Disposition": "inline", "Accept-Ranges": "bytes"},
    )


@router.get("/{doc_id}/thumbnail")
async def serve_thumbnail(
    doc_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
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
