"""Tests for document text extraction."""
import pytest
from pathlib import Path
from backend.services.extract_service import extract_text


class TestExtractDocx:
    def test_extract_text_plain_docx(self, tmp_path):
        """Extract text from a DOCX with only text paragraphs."""
        from docx import Document

        doc = Document()
        doc.add_paragraph("Hello World")
        doc.add_paragraph("Second paragraph")
        fpath = tmp_path / "test.docx"
        doc.save(str(fpath))

        result = extract_text(fpath, "docx")
        assert "Hello World" in result
        assert "Second paragraph" in result

    def test_extract_docx_empty(self, tmp_path):
        """Extract from empty DOCX returns empty string."""
        from docx import Document

        doc = Document()
        fpath = tmp_path / "empty.docx"
        doc.save(str(fpath))

        result = extract_text(fpath, "docx")
        assert result == "" or result is None

    def test_extract_docx_with_image_placeholder(self, tmp_path):
        """DOCX with inline image includes image data marker."""
        from docx import Document
        from docx.shared import Inches
        from PIL import Image
        import io

        # Create a small test image
        img = Image.new("RGB", (10, 10), color="red")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        doc = Document()
        doc.add_paragraph("Before image")
        doc.add_picture(img_bytes, width=Inches(1))
        doc.add_paragraph("After image")
        fpath = tmp_path / "with_image.docx"
        doc.save(str(fpath))

        result = extract_text(fpath, "docx")
        assert "Before image" in result
        assert "After image" in result
        assert "[image:" in result

    def test_extract_unknown_type_returns_none(self, tmp_path):
        """Unknown file type returns None."""
        fpath = tmp_path / "test.xyz"
        fpath.write_text("hello")
        result = extract_text(fpath, "xyz")
        assert result is None


class TestExtractMarkdown:
    def test_extract_markdown(self, tmp_path):
        """Extract text from markdown file."""
        fpath = tmp_path / "test.md"
        fpath.write_text("# Title\n\nSome content", encoding="utf-8")
        result = extract_text(fpath, "md")
        assert "Title" in result
        assert "Some content" in result

    def test_extract_markdown_empty(self, tmp_path):
        """Extract from empty markdown returns empty string."""
        fpath = tmp_path / "empty.md"
        fpath.write_text("", encoding="utf-8")
        result = extract_text(fpath, "md")
        assert result == ""
