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
    import base64
    from docx import Document

    doc = Document(str(file_path))

    # Build a map of image rId -> (content_type, base64 data)
    image_map = {}
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                img_bytes = rel.target_part.blob
                ct = rel.target_part.content_type
                b64 = base64.b64encode(img_bytes).decode("ascii")
                image_map[rel.rId] = (ct, b64)
            except Exception:
                continue

    # Collect paragraphs and inline shapes in document order
    result_parts = []
    shape_idx = 0
    shapes = list(doc.inline_shapes)

    for para in doc.paragraphs:
        if para.text.strip():
            result_parts.append(para.text)
        # Interleave inline shapes that belong to this paragraph
        while shape_idx < len(shapes):
            shape = shapes[shape_idx]
            try:
                rId = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
                if rId in image_map:
                    ct, b64 = image_map[rId]
                    result_parts.append(f"[image: data:{ct};base64,{b64}]")
                shape_idx += 1
            except Exception:
                shape_idx += 1
                continue
            break

    # Add any remaining images
    while shape_idx < len(shapes):
        shape = shapes[shape_idx]
        try:
            rId = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            if rId in image_map:
                ct, b64 = image_map[rId]
                result_parts.append(f"[image: data:{ct};base64,{b64}]")
        except Exception:
            pass
        shape_idx += 1

    return "\n".join(result_parts).strip()


def _extract_markdown(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8")
    return content.strip()
