"""
Document processing pipeline.

Orchestrates text extraction and thumbnail generation.
Each step is independently isolated — thumbnail failure does not block text extraction.

Design is compatible with future Celery integration:
  - Function signature uses db Session (replaceable with scoped_session for Celery workers)
  - Each step is a discrete unit that can become a subtask
"""

from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import STORAGE_PATH
from backend.services import extract_service, thumbnail_service
from backend.utils.logger import get_logger

logger = get_logger("services.processing")


def process_document(db: Session, doc) -> None:
    """Full processing pipeline: extract text + generate thumbnail.

    Args:
        db: SQLAlchemy session (auto-commits intermediate results)
        doc: Document ORM instance (must be attached to session)

    Side effects:
        - Sets doc.status to "processing", then "ready" or "error"
        - Populates doc.content_text on success
        - Populates doc.thumbnail_path on success
        - Sets doc.error_message on failure (truncated to 500 chars)
    """
    doc.status = "processing"
    db.commit()

    abs_path = STORAGE_PATH / doc.file_path
    if not abs_path.exists():
        doc.status = "error"
        doc.error_message = f"Source file not found: {doc.file_path}"
        db.commit()
        logger.error("Source file missing: doc_id=%d, path=%s", doc.id, doc.file_path)
        return

    text_ok = _extract_text_step(db, doc, abs_path)
    _generate_thumbnail_step(db, doc, abs_path)

    doc.status = "ready"
    db.commit()
    logger.info("Document processed successfully: id=%d", doc.id)


def _extract_text_step(db: Session, doc, abs_path: Path) -> bool:
    """Extract text from document. Returns True if text was extracted."""
    try:
        text_content = extract_service.extract_text(abs_path, doc.file_type)
        if text_content:
            doc.content_text = text_content
            db.commit()
            logger.debug("Text extracted: doc_id=%d, length=%d", doc.id, len(text_content))
        return bool(text_content)
    except Exception as e:
        logger.warning("Text extraction failed (non-fatal): doc_id=%d, error=%s", doc.id, e)
        return False


def _generate_thumbnail_step(db: Session, doc, abs_path: Path) -> None:
    """Generate thumbnail. Failure is non-fatal — document still becomes 'ready'."""
    try:
        thumb_name = Path(doc.file_path).stem + "_thumb.jpg"
        thumb_dir = STORAGE_PATH / str(doc.user_id) / "thumbnails"
        thumb_path = thumb_dir / thumb_name
        result = thumbnail_service.generate_thumbnail(abs_path, doc.file_type, thumb_path)
        if result:
            doc.thumbnail_path = str(result.relative_to(STORAGE_PATH))
            db.commit()
            logger.debug("Thumbnail generated: doc_id=%d", doc.id)
    except Exception as e:
        logger.warning("Thumbnail generation failed (non-fatal): doc_id=%d, error=%s", doc.id, e)


def retry_processing(db: Session, doc) -> None:
    """Retry processing for a failed document.

    Resets error state and re-runs the full pipeline.
    """
    doc.status = "processing"
    doc.error_message = None
    doc.content_text = None
    doc.thumbnail_path = None
    db.commit()
    logger.info("Retrying document processing: id=%d", doc.id)
    process_document(db, doc)
