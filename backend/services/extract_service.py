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
    from docx.oxml.ns import qn

    doc = Document(str(file_path))

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
            except Exception as e:
                logger.warning("Failed to extract image from rel %s: %s", rel.rId, e)
                continue

    result_parts = []
    extracted_images = []  # list of (extension, bytes) in document order
    seen_rids = set()

    def _is_in_fallback(element):
        """Check if element is inside mc:Fallback."""
        parent = element.getparent()
        while parent is not None:
            tag = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
            if tag == 'Fallback':
                return True
            parent = parent.getparent()
        return False

    def _extract_images_from_element(element):
        """Extract images from XML element, skipping mc:Fallback images."""
        images = []
        for drawing in element.findall('.//' + qn('w:drawing')):
            if _is_in_fallback(drawing):
                continue
            for blip in drawing.findall('.//' + qn('a:blip')):
                embed = blip.get(qn('r:embed'))
                if embed and embed in image_map and embed not in seen_rids:
                    images.append(embed)
                    seen_rids.add(embed)
        return images

    def _get_paragraph_text(para_element):
        """Get text content from paragraph element."""
        text_parts = []
        for run in para_element.findall(qn('w:r')):
            for t in run.findall(qn('w:t')):
                if t.text:
                    text_parts.append(t.text)
        return ''.join(text_parts)

    def _process_paragraph(para_element):
        """Process a single paragraph, extracting text and images."""
        text = _get_paragraph_text(para_element)
        para_images = _extract_images_from_element(para_element)

        if para_images:
            if text.strip():
                result_parts.append(text)
            for rId in para_images:
                img_index = len(extracted_images)
                extracted_images.append(image_map[rId])
                result_parts.append(f"[image:{img_index}]")
        else:
            if text.strip():
                result_parts.append(text)

    def _process_table(table_element):
        """Recursively process all paragraphs in a table."""
        for row in table_element.findall(qn('w:tr')):
            for cell in row.findall(qn('w:tc')):
                for para in cell.findall(qn('w:p')):
                    _process_paragraph(para)
                for nested_tbl in cell.findall(qn('w:tbl')):
                    _process_table(nested_tbl)

    # Traverse w:body children in document order
    for child in doc.element.body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'p':
            _process_paragraph(child)
        elif tag == 'tbl':
            _process_table(child)

    # Save extracted images to disk if user_id and doc_id are provided
    if extracted_images and user_id is not None and doc_id is not None:
        from backend.services import file_service
        file_service.save_docx_images(user_id, doc_id, extracted_images)

    return "\n".join(result_parts).strip()


def _extract_markdown(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8")
    return content.strip()
