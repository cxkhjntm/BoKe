"""Thumbnail generation service.

- PDF: Render first page as image using PyMuPDF, then resize
- Images: Resize with Pillow
- DOCX/Markdown: Generate a styled icon with file type label
"""

from pathlib import Path

from backend.utils.logger import get_logger

logger = get_logger("services.thumbnail")

THUMBNAIL_SIZE = (200, 200)

# Colors for default thumbnails
_BG_COLOR = (230, 230, 230)  # Light gray
_TEXT_COLOR = (80, 80, 80)    # Dark gray
_ACCENT_COLORS = {
    "docx": (41, 128, 185),   # Blue
    "md": (39, 174, 96),      # Green
}


def generate_thumbnail(file_path: Path, file_type: str, output_path: Path) -> Path | None:
    """Generate thumbnail. Returns output path or None if not applicable."""
    try:
        if file_type == "pdf":
            return _pdf_thumbnail(file_path, output_path)
        elif file_type in ("png", "jpg", "jpeg"):
            return _image_thumbnail(file_path, output_path)
        elif file_type in ("docx", "md"):
            return _icon_thumbnail(file_type, output_path)
        else:
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
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(str(output_path), "JPEG", quality=85)
    return output_path


def _icon_thumbnail(file_type: str, output_path: Path) -> Path:
    """Generate a default icon thumbnail for DOCX/Markdown files."""
    from PIL import Image, ImageDraw, ImageFont

    size = THUMBNAIL_SIZE
    bg = _BG_COLOR
    accent = _ACCENT_COLORS.get(file_type, (120, 120, 120))

    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)

    # Draw accent bar at top
    draw.rectangle([(0, 0), (size[0], 8)], fill=accent)

    # Draw file type label centered
    label = file_type.upper()
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size[0] - text_w) // 2
    y = (size[1] - text_h) // 2
    draw.text((x, y), label, fill=_TEXT_COLOR, font=font)

    # Draw a subtle border
    draw.rectangle([(2, 2), (size[0] - 3, size[1] - 3)], outline=(200, 200, 200), width=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "JPEG", quality=85)
    return output_path
