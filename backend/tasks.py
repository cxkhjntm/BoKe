"""Celery tasks for document processing."""

from datetime import datetime, timedelta

from backend.celery_app import celery
from backend.database import SessionLocal
from backend.models.document import Document
from backend.services import processing_service
from backend.utils.logger import get_logger

logger = get_logger("tasks.processing")

# Documents stuck in "processing" longer than this are considered orphaned.
PROCESSING_TIMEOUT_MINUTES = 10


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
            logger.warning("Document not found (may have been deleted): id=%d", document_id)
            return

        processing_service.process_document(db, doc)

        # Re-check existence after processing — document may have been deleted
        # by a concurrent request while processing was in progress.
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning("Document deleted during processing: id=%d", document_id)
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


@celery.task(name="cleanup_stuck_documents")
def cleanup_stuck_documents():
    """Mark documents stuck in 'processing' status as 'error'.

    Scheduled to run periodically via Celery beat. Handles the case where
    a worker crashed mid-processing, leaving the document in a permanent
    'processing' state with no way to retry or delete.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES)
        stuck = (
            db.query(Document)
            .filter(
                Document.status == "processing",
                Document.updated_at < cutoff,
            )
            .all()
        )
        for doc in stuck:
            doc.status = "error"
            doc.error_message = f"Processing timed out after {PROCESSING_TIMEOUT_MINUTES} minutes"
            logger.warning("Marked stuck document as error: id=%d", doc.id)
        if stuck:
            db.commit()
            logger.info("Cleaned up %d stuck documents", len(stuck))
    except Exception:
        logger.exception("Failed to cleanup stuck documents")
    finally:
        db.close()
