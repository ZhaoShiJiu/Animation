"""
test_pdf.py — PDF 文本提取测试。
"""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.llm_stream import extract_pdf_text


class TestExtractPdfText:
    """PDF 文本提取测试。"""

    @pytest.mark.asyncio
    async def test_valid_pdf_extraction(self, mocker):
        """模拟 pypdf 提取文本。"""
        # Mock PdfReader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "  This is page one content.  "

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        mocker.patch("backend.llm_stream.PdfReader", return_value=mock_reader)

        # 创建 mock UploadFile
        mock_file = AsyncMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024
        mock_file.read.return_value = b"%PDF-1.4 fake pdf content"

        result = await extract_pdf_text(mock_file)

        assert result["filename"] == "test.pdf"
        assert "page one" in result["text"].lower()
        assert result["page_count"] == 1
        assert result["truncated"] is False

    @pytest.mark.asyncio
    async def test_not_pdf_extension_raises(self):
        """非 PDF 文件应报错。"""
        mock_file = AsyncMock()
        mock_file.filename = "image.png"
        mock_file.content_type = "image/png"
        mock_file.size = 100

        with pytest.raises(ValueError, match="PDF"):
            await extract_pdf_text(mock_file)

    @pytest.mark.asyncio
    async def test_empty_file_raises(self):
        """空文件应报错。"""
        mock_file = AsyncMock()
        mock_file.filename = "empty.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 0
        mock_file.read.return_value = b""

        with pytest.raises(ValueError, match="空"):
            await extract_pdf_text(mock_file)

    @pytest.mark.asyncio
    async def test_too_large_file_raises(self, monkeypatch):
        """超大文件应报错。"""
        # 设置更小的限制
        monkeypatch.setattr("backend.llm_stream.MAX_PAPER_UPLOAD_BYTES", 1024)

        mock_file = AsyncMock()
        mock_file.filename = "large.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 10 * 1024 * 1024  # 远大于 1KB
        mock_file.read.return_value = b"x" * (10 * 1024 * 1024)

        with pytest.raises(ValueError, match="过大"):
            await extract_pdf_text(mock_file)

    @pytest.mark.asyncio
    async def test_corrupt_pdf_raises(self, mocker):
        """损坏的 PDF 应报错。"""
        mocker.patch(
            "backend.llm_stream.PdfReader",
            side_effect=Exception("Invalid PDF structure"),
        )

        mock_file = AsyncMock()
        mock_file.filename = "corrupt.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 500
        mock_file.read.return_value = b"not a real pdf"

        with pytest.raises(ValueError, match="PDF 解析失败"):
            await extract_pdf_text(mock_file)

    @pytest.mark.asyncio
    async def test_no_text_extracted_raises(self, mocker):
        """无法提取文字时应报错。"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "   "  # 全空白

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        mocker.patch("backend.llm_stream.PdfReader", return_value=mock_reader)

        mock_file = AsyncMock()
        mock_file.filename = "blank.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 100
        mock_file.read.return_value = b"%PDF-1.4"

        with pytest.raises(ValueError, match="未能从 PDF 中提取文字"):
            await extract_pdf_text(mock_file)

    @pytest.mark.asyncio
    async def test_text_truncation(self, mocker, monkeypatch):
        """超长文本应截断并标记 truncated=True。"""
        monkeypatch.setattr("backend.llm_stream.MAX_PAPER_TEXT_CHARS", 50)

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "A" * 100  # 比限制长

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        mocker.patch("backend.llm_stream.PdfReader", return_value=mock_reader)

        mock_file = AsyncMock()
        mock_file.filename = "long.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.size = 100
        mock_file.read.return_value = b"%PDF-1.4 long content"

        result = await extract_pdf_text(mock_file)
        assert result["truncated"] is True
        assert len(result["text"]) == 50
