"""Text extraction from documents.

Structure is designed for future async task queue (Celery/BackgroundTasks).
The function signatures remain the same; only the call site changes.
"""

from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger("services.extract")


def extract_text(file_path: Path, file_type: str) -> str | None:
    """Extract text content from a document file.

    Returns extracted text or None if extraction is not applicable.
    Raises exception on extraction failure.
    """
    try:
        if file_type == "pdf":
            return _extract_pdf(file_path)
        elif file_type == "docx":
            return _extract_docx(file_path)
        elif file_type == "md":
            return _extract_markdown(file_path)
        else:
            # Images don't have extractable text
            return None
    except Exception as e:
        logger.error("Text extraction failed for %s: %s", file_path, e)
        raise


def _extract_pdf(file_path: Path) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(str(file_path))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def _extract_docx(file_path: Path) -> str:
    from docx import Document

    doc = Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs).strip()


def _extract_markdown(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8")
    return content.strip()
