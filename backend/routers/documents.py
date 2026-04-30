from pathlib import Path

import magic
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.schemas.document import DocumentOut, DocumentListItem, DocumentUpdate
from backend.services import document_service, file_service, processing_service, dashboard_service
from backend.utils.response import ok
from backend.utils.logger import get_logger
from backend.config import MAX_UPLOAD_SIZE_BYTES, ALLOWED_EXTENSIONS
from backend.exceptions.handlers import AppException

logger = get_logger("routers.documents")
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _dispatch_processing(document_id: int, db: Session, doc) -> None:
    """Dispatch document processing. Falls back to sync if Redis is unavailable."""
    try:
        from backend.tasks import process_document_task

        process_document_task.delay(document_id)
        logger.info("Document processing dispatched to Celery: id=%d", document_id)
    except Exception as e:
        logger.warning(
            "Celery dispatch failed (falling back to sync): id=%d, error=%s",
            document_id,
            e,
        )
        processing_service.process_document(db, doc)

# MIME type whitelist (extension -> allowed MIME patterns)
MIME_WHITELIST = {
    "pdf": ["application/pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # docx is a zip archive
    ],
    "md": ["text/markdown", "text/plain", "application/octet-stream"],
    "png": ["image/png"],
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"],
}


def _validate_file(file: UploadFile, content: bytes) -> str:
    """Three-layer file validation. Returns file_type."""
    # Layer 1: Extension whitelist
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise AppException(code=4009, message=f"File type '.{ext}' is not allowed", status_code=400)

    # Layer 2: MIME type detection (python-magic)
    detected_mime = magic.from_buffer(content, mime=True)
    allowed_mimes = MIME_WHITELIST.get(ext, [])
    if detected_mime not in allowed_mimes:
        raise AppException(
            code=4011,
            message=f"File content does not match expected type. Detected: {detected_mime}",
            status_code=400,
        )

    # Layer 3: Format validation
    _validate_format(ext, content)

    return ext


def _validate_format(ext: str, content: bytes) -> None:
    """Validate that the file can actually be parsed as its claimed type."""
    import io

    if ext == "pdf":
        import fitz

        doc = fitz.open(stream=content, filetype="pdf")
        if doc.page_count == 0:
            raise AppException(code=4011, message="Invalid PDF file", status_code=400)
        doc.close()

    elif ext == "docx":
        from docx import Document

        Document(io.BytesIO(content))

    elif ext in ("png", "jpg", "jpeg"):
        from PIL import Image

        img = Image.open(io.BytesIO(content))
        img.verify()


@router.post("")
def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Read file content
    content = file.file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise AppException(
            code=4010,
            message=f"File exceeds maximum size of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB",
            status_code=400,
        )

    # Validate file (three layers)
    file_type = _validate_file(file, content)

    # Use original filename as title if not provided
    doc_title = title or Path(file.filename).stem

    # Save file
    relative_path = file_service.save_file(current_user.id, file.filename, content, "original")

    # Create document record with queued status
    doc = document_service.create_document(
        db=db,
        user_id=current_user.id,
        title=doc_title,
        original_filename=file.filename,
        file_type=file_type,
        file_size=len(content),
        file_path=relative_path,
    )

    # Dispatch async processing (with sync fallback)
    _dispatch_processing(doc.id, db, doc)

    # Log activity
    dashboard_service.log_activity(db, current_user.id, "upload", doc.id)

    return ok(data=DocumentOut.model_validate(doc).model_dump())


@router.get("")
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", pattern="^(created_at|file_size|title)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    status: str | None = Query(None, pattern="^(queued|processing|ready|error)$"),
    file_type: str | None = Query(None, pattern="^(pdf|docx|md|png|jpg|jpeg)$"),
    is_favorite: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = document_service.list_documents(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status,
        file_type=file_type,
        is_favorite=is_favorite,
    )
    items = [DocumentListItem.model_validate(d).model_dump() for d in result["items"]]
    return ok(data={"items": items, "total": result["total"], "page": page, "limit": limit})


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.get_document(db, doc_id, current_user.id)
    document_service.record_view(db, doc_id, current_user.id)
    dashboard_service.log_activity(db, current_user.id, "view", doc_id)
    return ok(data=DocumentOut.model_validate(doc).model_dump())


@router.patch("/{doc_id}")
def update_document(
    doc_id: int,
    body: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.update_document(db, doc_id, current_user.id, title=body.title)
    return ok(data=DocumentOut.model_validate(doc).model_dump())


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document_service.delete_document(db, doc_id, current_user.id)
    return ok()


@router.post("/{doc_id}/retry")
def retry_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.retry_document(db, doc_id, current_user.id)
    _dispatch_processing(doc.id, db, doc)
    return ok(data=DocumentOut.model_validate(doc).model_dump())


@router.patch("/{doc_id}/favorite")
def toggle_favorite(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.toggle_favorite(db, doc_id, current_user.id)
    return ok(data={"id": doc.id, "is_favorite": doc.is_favorite})
