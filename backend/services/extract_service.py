"""Text extraction from documents.

Structure is designed for future async task queue (Celery/BackgroundTasks).
The function signatures remain the same; only the call site changes.
"""

from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger("services.extract")


def extract_text(file_path: Path, file_type: str, user_id: int | None = None, doc_id: int | None = None) -> str | None:
    """Extract text content from a document file.

    Returns extracted text or None if extraction is not applicable.
    Raises exception on extraction failure.

    Args:
        file_path: Path to the document file
        file_type: Document type (pdf, docx, md, png, jpg, jpeg)
        user_id: Owner user ID (required for docx image extraction)
        doc_id: Document ID (required for docx image extraction)
    """
    try:
        if file_type == "pdf":
            return _extract_pdf(file_path)
        elif file_type == "docx":
            return _extract_docx(file_path, user_id, doc_id)
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


def _extract_docx(file_path: Path, user_id: int | None = None, doc_id: int | None = None) -> str:
    from docx import Document

    doc = Document(str(file_path))

    # Build a map of image rId -> (extension_bytes, binary_data)
    _CT_EXT_MAP = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/webp": ".webp",
    }

    image_map = {}  # rId -> (extension, bytes)
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            try:
                img_bytes = rel.target_part.blob
                ct = rel.target_part.content_type
                ext = _CT_EXT_MAP.get(ct, ".png")
                image_map[rel.rId] = (ext, img_bytes)
            except Exception:
                continue

    # Collect paragraphs and inline shapes in document order
    result_parts = []
    shape_idx = 0
    shapes = list(doc.inline_shapes)
    extracted_images = []  # list of (extension, bytes) in document order

    for para in doc.paragraphs:
        if para.text.strip():
            result_parts.append(para.text)
        # Interleave inline shapes that belong to this paragraph
        while shape_idx < len(shapes):
            shape = shapes[shape_idx]
            try:
                rId = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
                if rId in image_map:
                    img_index = len(extracted_images)
                    extracted_images.append(image_map[rId])
                    result_parts.append(f"[image:{img_index}]")
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
                img_index = len(extracted_images)
                extracted_images.append(image_map[rId])
                result_parts.append(f"[image:{img_index}]")
        except Exception:
            pass
        shape_idx += 1

    # Save extracted images to disk if user_id and doc_id are provided
    if extracted_images and user_id is not None and doc_id is not None:
        from backend.services import file_service
        file_service.save_docx_images(user_id, doc_id, extracted_images)

    return "\n".join(result_parts).strip()


def _extract_markdown(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8")
    return content.strip()
