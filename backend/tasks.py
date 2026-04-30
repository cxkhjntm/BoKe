"""Celery tasks for document processing."""

from backend.celery_app import celery
from backend.database import SessionLocal
from backend.models.document import Document
from backend.services import processing_service
from backend.utils.logger import get_logger

logger = get_logger("tasks.processing")


@celery.task(name="process_document", bind=True, max_retries=0)
def process_document_task(self, document_id: int):
    """Process a document asynchronously.

    Creates its own DB session (not shared with request handler).
    Updates document status: queued -> processing -> ready / error.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error("Document not found for processing: id=%d", document_id)
            return

        processing_service.process_document(db, doc)
    except Exception as e:
        logger.exception("Celery task failed for document id=%d: %s", document_id, e)
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc and doc.status not in ("ready",):
                doc.status = "error"
                doc.error_message = "Internal processing error"
                db.commit()
        except Exception:
            logger.exception("Failed to mark document as error after task failure")
    finally:
        db.close()
