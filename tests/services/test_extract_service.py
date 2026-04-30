"""Tests for backend.services.extract_service."""

import pytest

from backend.services import extract_service


class TestExtractText:
    def test_extract_pdf(self, sample_pdf):
        text = extract_service.extract_text(sample_pdf, "pdf")
        assert text is not None
        assert "Hello, test!" in text

    def test_extract_docx(self, sample_docx):
        text = extract_service.extract_text(sample_docx, "docx")
        assert text is not None
        assert "Hello, test!" in text

    def test_extract_markdown(self, sample_markdown):
        text = extract_service.extract_text(sample_markdown, "md")
        assert text is not None
        assert "Hello" in text

    def test_image_returns_none(self, sample_image):
        text = extract_service.extract_text(sample_image, "png")
        assert text is None

    def test_unsupported_type_returns_none(self, tmp_path):
        fake = tmp_path / "test.xyz"
        fake.write_bytes(b"data")
        text = extract_service.extract_text(fake, "xyz")
        assert text is None

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(Exception):
            extract_service.extract_text(tmp_path / "nope.pdf", "pdf")
