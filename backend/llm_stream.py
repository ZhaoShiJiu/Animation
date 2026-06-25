"""
llm_stream.py — PDF 文本提取。

AI 生成逻辑已迁移至 backend/graph/（LangGraph 编排）。
"""
import io
import logging
from typing import Dict, Any

from fastapi import UploadFile
from pypdf import PdfReader

from backend.config import MAX_PAPER_UPLOAD_BYTES, MAX_PAPER_TEXT_CHARS

logger = logging.getLogger(__name__)


async def extract_pdf_text(pdf_file: UploadFile) -> Dict[str, Any]:
    """从上传的 PDF 文件中提取文字内容。

    Returns:
        {"filename": str, "text": str, "page_count": int, "truncated": bool}
    """
    filename = pdf_file.filename or "paper.pdf"
    content_type = pdf_file.content_type or ""
    logger.info("PDF 提取开始 | filename=%s | size=%d", filename, pdf_file.size or 0)

    if not filename.lower().endswith(".pdf") and "pdf" not in content_type.lower():
        raise ValueError("请上传 PDF 文件")

    content = await pdf_file.read()
    if not content:
        raise ValueError("PDF 文件为空")
    if len(content) > MAX_PAPER_UPLOAD_BYTES:
        raise ValueError(
            f"PDF 文件过大，请上传不超过 {MAX_PAPER_UPLOAD_BYTES // 1024 // 1024}MB 的文件"
        )

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        logger.exception("PDF 解析失败 | filename=%s", filename)
        raise ValueError("PDF 解析失败，请确认文件未损坏") from exc

    page_texts = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            page_texts.append(f"[Page {index}]\n{text}")

    paper_text = "\n\n".join(page_texts).strip()
    if not paper_text:
        logger.warning(
            "PDF 未提取到文字 | filename=%s | pages=%d", filename, len(reader.pages)
        )
        raise ValueError("未能从 PDF 中提取文字，暂不支持扫描版或图片型论文")

    truncated = len(paper_text) > MAX_PAPER_TEXT_CHARS
    if truncated:
        paper_text = paper_text[:MAX_PAPER_TEXT_CHARS]

    logger.info(
        "PDF 提取完成 | filename=%s | pages=%d | chars=%d | truncated=%s",
        filename, len(reader.pages), len(paper_text), truncated,
    )
    return {
        "filename": filename,
        "text": paper_text,
        "page_count": len(reader.pages),
        "truncated": truncated,
    }
