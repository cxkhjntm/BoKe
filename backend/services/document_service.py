from pathlib import Path

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
) -> Document:
    doc = Document(
        user_id=user_id,
        title=title,
        original_filename=original_filename,
        file_type=file_type,
        file_size=file_size,
        file_path=file_path,
        status="processing",
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
) -> dict:
    query = db.query(Document).filter(Document.user_id == user_id)

    if status:
        query = query.filter(Document.status == status)
    if file_type:
        query = query.filter(Document.file_type == file_type)

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

    if doc.status == "processing":
        raise AppException(code=4005, message="Cannot delete document while processing", status_code=409)

    # Delete physical files
    file_service.delete_file(doc.file_path)
    if doc.thumbnail_path:
        file_service.delete_file(doc.thumbnail_path)

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
