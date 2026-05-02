"""Tests for file serving Content-Disposition encoding."""
import pytest
from backend.routers.files import _content_disposition


class TestContentDisposition:
    def test_ascii_filename(self):
        """ASCII filename should use simple filename parameter."""
        result = _content_disposition("document.pdf")
        assert 'filename="document.pdf"' in result
        assert "inline" in result

    def test_chinese_filename(self):
        """Chinese filename should use RFC 5987 encoding."""
        result = _content_disposition("测试文档.pdf")
        assert "filename*=UTF-8''" in result
        assert "inline" in result
        # Should not contain raw Chinese in the filename= part
        assert "测试" not in result.split("filename=")[1].split(";")[0]

    def test_mixed_filename(self):
        """Mixed ASCII and unicode filename handles both."""
        result = _content_disposition("report_测试.pdf")
        assert "filename=" in result
        assert "filename*=UTF-8''" in result

    def test_empty_filename(self):
        """Empty filename should not crash."""
        result = _content_disposition("")
        assert "inline" in result

    def test_special_chars_filename(self):
        """Filename with special chars like spaces and parens."""
        result = _content_disposition("my document (1).pdf")
        assert "inline" in result
        assert "filename=" in result
