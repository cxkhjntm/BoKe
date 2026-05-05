from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from backend.models.document import Document
from backend.services import file_service
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("services.document")


def create_document(
    db: Session,
    user_id: int,
    title: str,
    original_filename: str,
    file_type: str,
    file_size: int,
    file_path: str,
    status: str = "queued",
) -> Document:
    doc = Document(
        user_id=user_id,
        title=title,
        original_filename=original_filename,
        file_type=file_type,
        file_size=file_size,
        file_path=file_path,
        status=status,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info("Document created: id=%d, title='%s'", doc.id, title)
    return doc


def get_document(db: Session, doc_id: int, user_id: int) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)
    return doc


def list_documents(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    status: str | None = None,
    file_type: str | None = None,
    is_favorite: bool | None = None,
    category: str | None = None,
) -> dict:
    query = db.query(Document).filter(Document.user_id == user_id)

    if status:
        query = query.filter(Document.status == status)
    if file_type:
        query = query.filter(Document.file_type == file_type)
    if is_favorite is not None:
        query = query.filter(Document.is_favorite == is_favorite)
    if category == "uncategorized":
        query = query.filter(Document.category.is_(None))
    elif category is not None:
        query = query.filter(Document.category == category)

    total = query.count()

    # Sorting
    sort_column = getattr(Document, sort_by, Document.created_at)
    order_func = desc if sort_order == "desc" else asc
    query = query.order_by(order_func(sort_column))

    # Pagination
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    return {"items": items, "total": total, "page": page, "limit": limit}


def delete_document(db: Session, doc_id: int, user_id: int) -> None:
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)

    if doc.status in ("queued", "processing"):
        raise AppException(code=4005, message="Cannot delete document while processing", status_code=409)

    # Delete physical files
    file_service.delete_file(doc.file_path)
    if doc.thumbnail_path:
        file_service.delete_file(doc.thumbnail_path)
    if doc.file_type == "docx":
        file_service.delete_docx_images(doc.user_id, doc.id)

    db.delete(doc)
    db.commit()
    logger.info("Document deleted: id=%d", doc_id)


def update_document(db: Session, doc_id: int, user_id: int, title: str | None = None) -> Document:
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)
    if title is not None:
        doc.title = title
    db.commit()
    db.refresh(doc)
    return doc


def retry_document(db: Session, doc_id: int, user_id: int) -> Document:
    """Retry processing a failed document."""
    doc = get_document(db, doc_id, user_id)
    if doc.status != "error":
        raise AppException(
            code=4005,
            message="Only documents with 'error' status can be retried",
            status_code=409,
        )
    doc.status = "queued"
    doc.error_message = None
    doc.content_text = None
    doc.thumbnail_path = None
    db.commit()
    db.refresh(doc)
    logger.info("Document retry initiated: id=%d", doc_id)
    return doc


def reprocess_document(db: Session, doc_id: int, user_id: int) -> Document:
    """Reprocess a document regardless of current status.

    Used to re-extract content after extraction code improvements.
    Cleans up old extracted images and resets to queued status.
    """
    doc = get_document(db, doc_id, user_id)
    if doc.status in ("queued", "processing"):
        raise AppException(
            code=4005,
            message="Cannot reprocess while document is already queued or processing",
            status_code=409,
        )
    # Clean up old extracted images
    if doc.file_type == "docx":
        file_service.delete_docx_images(doc.user_id, doc.id)
    doc.status = "queued"
    doc.error_message = None
    doc.content_text = None
    doc.thumbnail_path = None
    db.commit()
    db.refresh(doc)
    logger.info("Document reprocess initiated: id=%d", doc_id)
    return doc


def toggle_favorite(db: Session, doc_id: int, user_id: int) -> Document:
    """Toggle favorite status of a document."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)
    doc.is_favorite = not doc.is_favorite
    db.commit()
    db.refresh(doc)
    logger.info("Document favorite toggled: id=%d, is_favorite=%s", doc_id, doc.is_favorite)
    return doc


def set_category(db: Session, doc_id: int, user_id: int, category: str | None) -> Document:
    """Set or clear category of a document."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if not doc:
        raise AppException(code=4004, message="Document not found", status_code=404)
    doc.category = category
    db.commit()
    db.refresh(doc)
    logger.info("Document category updated: id=%d, category=%s", doc_id, category)
    return doc


def record_view(db: Session, doc_id: int, user_id: int) -> None:
    """Increment view count and update last_viewed_at."""
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if doc:
        doc.view_count = (doc.view_count or 0) + 1
        doc.last_viewed_at = datetime.utcnow()
        db.commit()


def rebuild_fts_index(db: Session) -> int:
    """Rebuild FTS5 index. Returns number of documents indexed."""
    from sqlalchemy import text

    db.execute(text("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')"))
    db.commit()
    count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    logger.info("FTS5 index rebuilt. Total documents: %d", count)
    return count
