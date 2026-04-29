"""Thumbnail generation service.

- PDF: Render first page as image using PyMuPDF, then resize
- Images: Resize with Pillow
- DOCX/Markdown: No thumbnail generated (use default icon)
"""

from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger("services.thumbnail")

THUMBNAIL_SIZE = (200, 200)


def generate_thumbnail(file_path: Path, file_type: str, output_path: Path) -> Path | None:
    """Generate thumbnail. Returns output path or None if not applicable."""
    try:
        if file_type == "pdf":
            return _pdf_thumbnail(file_path, output_path)
        elif file_type in ("png", "jpg", "jpeg"):
            return _image_thumbnail(file_path, output_path)
        else:
            # DOCX/Markdown: no thumbnail
            return None
    except Exception as e:
        logger.error("Thumbnail generation failed for %s: %s", file_path, e)
        return None


def _pdf_thumbnail(file_path: Path, output_path: Path) -> Path:
    import fitz
    from PIL import Image
    import io

    doc = fitz.open(str(file_path))
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    doc.close()

    img = Image.open(io.BytesIO(pix.tobytes("jpeg")))
    img.thumbnail(THUMBNAIL_SIZE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "JPEG", quality=85)
    return output_path


def _image_thumbnail(file_path: Path, output_path: Path) -> Path:
    from PIL import Image

    img = Image.open(str(file_path))
    img.thumbnail(THUMBNAIL_SIZE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Convert to JPEG for consistency
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(str(output_path), "JPEG", quality=85)
    return output_path
