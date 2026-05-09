from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from backend.models.document import Document
from backend.services import file_service
from backend.utils.logger import get_logger
from backend.exceptions.handlers import AppException

logger = get_logger("services.document")


def _cleanup_rag_chunks(db: Session, user_id: int, file_path: str) -> None:
    try:
        from types import SimpleNamespace

        from backend.models.embedding_config import EmbeddingConfig
        from backend.services import rag_service
        from backend.utils.crypto_utils import decrypt_api_key

        embedding_cfg = db.query(EmbeddingConfig).filter(EmbeddingConfig.user_id == user_id).first()
        if not embedding_cfg or not embedding_cfg.api_key:
            return

        ec = SimpleNamespace(
            api_key=decrypt_api_key(str(embedding_cfg.api_key)),
            base_url=str(embedding_cfg.base_url),
            model_name=str(embedding_cfg.model_name),
            vector_dimension=int(embedding_cfg.vector_dimension),
        )

        rag_service.delete_document_chunks(user_id, file_path, ec)
    except Exception as e:
        logger.warning("RAG chunk cleanup failed (non-fatal): user_id=%d, file=%s, error=%s", user_id, file_path, e)


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

    _cleanup_rag_chunks(db, user_id, doc.file_path)

    # Capture file paths before deleting DB record
    file_path = doc.file_path
    thumbnail_path = doc.thumbnail_path
    is_docx = doc.file_type == "docx"

    # Delete DB record first (within transaction)
    db.delete(doc)
    db.commit()
    logger.info("Document deleted: id=%d", doc_id)

    # Delete physical files after successful DB commit
    file_service.delete_file(file_path)
    if thumbnail_path:
        file_service.delete_file(thumbnail_path)
    if is_docx:
        file_service.delete_docx_images(user_id, doc_id)


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
    if doc.thumbnail_path:
        file_service.delete_file(doc.thumbnail_path)
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
    if doc.file_type == "docx":
        file_service.delete_docx_images(doc.user_id, doc.id)
    if doc.thumbnail_path:
        file_service.delete_file(doc.thumbnail_path)
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

    _handle_favorite_rag(db, user_id, doc)

    return doc


def _handle_favorite_rag(db: Session, user_id: int, doc: Document) -> None:
    try:
        from types import SimpleNamespace

        from backend.models.embedding_config import EmbeddingConfig
        from backend.models.rag_config import RAGConfig
        from backend.services import rag_service
        from backend.utils.crypto_utils import decrypt_api_key

        embedding_cfg = db.query(EmbeddingConfig).filter(EmbeddingConfig.user_id == user_id).first()

        if doc.is_favorite:
            # Auto-create default EmbeddingConfig if missing
            if not embedding_cfg:
                embedding_cfg = EmbeddingConfig(
                    user_id=user_id,
                    base_url="https://api.siliconflow.cn/v1",
                    model_name="BAAI/bge-large-zh-v1.5",
                    vector_dimension=1024,
                )
                db.add(embedding_cfg)
                db.commit()
                db.refresh(embedding_cfg)
                logger.info("Auto-created default EmbeddingConfig for user_id=%d", user_id)

            # Can't index without an API key
            if not embedding_cfg.api_key:
                logger.warning(
                    "EmbeddingConfig has no API key for user_id=%d, skipping RAG indexing. Please set an API key in RAG settings.",
                    user_id,
                )
                return

            # Auto-create default RAGConfig if missing
            rag_cfg = db.query(RAGConfig).filter(RAGConfig.user_id == user_id).first()
            if not rag_cfg:
                rag_cfg = RAGConfig(
                    user_id=user_id,
                    chunk_size=300,
                    chunk_overlap=50,
                    top_k=3,
                    threshold_dist=0.35,
                    query_buffer=10,
                )
                db.add(rag_cfg)
                db.commit()
                db.refresh(rag_cfg)
                logger.info("Auto-created default RAGConfig for user_id=%d", user_id)

            if not doc.content_text:
                logger.warning("Document content_text missing for doc_id=%d, skipping RAG indexing", doc.id)
                return

            ec = SimpleNamespace(
                api_key=decrypt_api_key(str(embedding_cfg.api_key)),
                base_url=str(embedding_cfg.base_url),
                model_name=str(embedding_cfg.model_name),
                vector_dimension=int(embedding_cfg.vector_dimension),
            )

            chunk_count = rag_service.process_document(
                user_id=user_id,
                file_path=doc.file_path,
                file_content=doc.content_text,
                rag_config=rag_cfg,
                embedding_config=ec,
            )
            logger.info("RAG indexed %d chunks for favorited doc_id=%d", chunk_count, doc.id)
        else:
            # Unfavorite — need embedding config to delete chunks
            if not embedding_cfg or not embedding_cfg.api_key:
                return

            ec = SimpleNamespace(
                api_key=decrypt_api_key(str(embedding_cfg.api_key)),
                base_url=str(embedding_cfg.base_url),
                model_name=str(embedding_cfg.model_name),
                vector_dimension=int(embedding_cfg.vector_dimension),
            )

            deleted = rag_service.delete_document_chunks(user_id, doc.file_path, ec)
            logger.info("RAG deleted %d chunks for unfavorited doc_id=%d", deleted, doc.id)
    except Exception as e:
        logger.error("RAG favorite indexing/deletion failed (non-fatal): user_id=%d, doc_id=%d, error=%s", user_id, doc.id, e, exc_info=True)


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


def get_document_timeline(
    db: Session,
    user_id: int,
    before: datetime | None = None,
    limit: int = 20,
    status: str | None = None,
    file_type: str | None = None,
    is_favorite: bool | None = True,
) -> dict:
    """Cursor-based timeline of documents, grouped by date."""
    query = db.query(Document).filter(Document.user_id == user_id)

    if status:
        query = query.filter(Document.status == status)
    if file_type:
        query = query.filter(Document.file_type == file_type)
    if is_favorite is not None:
        query = query.filter(Document.is_favorite == is_favorite)

    if before is not None:
        query = query.filter(Document.created_at < before)

    query = query.order_by(desc(Document.created_at))
    items = query.limit(limit).all()

    # Group by date string
    groups: dict[str, list] = {}
    for doc in items:
        date_key = doc.created_at.strftime("%Y-%m-%d")
        groups.setdefault(date_key, []).append(doc)

    # Determine if more exist
    has_more = False
    next_before = None
    if len(items) == limit:
        last = items[-1]
        # Check if any docs exist before the last item
        exists_query = db.query(Document).filter(
            Document.user_id == user_id,
            Document.created_at < last.created_at,
        )
        if status:
            exists_query = exists_query.filter(Document.status == status)
        if file_type:
            exists_query = exists_query.filter(Document.file_type == file_type)
        if is_favorite is not None:
            exists_query = exists_query.filter(Document.is_favorite == is_favorite)
        has_more = db.query(exists_query.exists()).scalar()
        next_before = last.created_at.isoformat() if has_more else None

    return {"groups": groups, "next_before": next_before, "has_more": has_more}


def rebuild_fts_index(db: Session) -> int:
    """Rebuild FTS5 index. Returns number of documents indexed."""
    from sqlalchemy import text

    db.execute(text("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')"))
    db.commit()
    count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
    logger.info("FTS5 index rebuilt. Total documents: %d", count)
    return count
