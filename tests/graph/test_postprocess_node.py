"""
test_postprocess_node.py — postprocess 节点测试。
"""
import pytest

from backend.graph.nodes.postprocess import postprocess_html_node


class TestPostprocessHtmlNode:
    """postprocess_html_node 测试。"""

    @pytest.mark.asyncio
    async def test_empty_html_returns_error(self):
        """空 HTML 应返回 error。"""
        state = {"html": ""}
        result = await postprocess_html_node(state)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_valid_html_returns_enhanced(self, sample_html):
        """合法 HTML 应被增强。"""
        state = {"html": sample_html}
        result = await postprocess_html_node(state)

        assert "html" in result
        assert "error" not in result
        assert len(result["html"]) >= len(sample_html)

    @pytest.mark.asyncio
    async def test_injects_css_variables(self):
        """应注入 CSS 变量。"""
        html = "<!DOCTYPE html><html><head></head><body>test</body></html>"
        state = {"html": html}
        result = await postprocess_html_node(state)

        assert "--color-danger" in result["html"]

    @pytest.mark.asyncio
    async def test_exception_does_not_block(self, mocker):
        """后处理异常时降级返回原始 HTML。"""
        mocker.patch(
            "backend.graph.nodes.postprocess.postprocess_html",
            side_effect=RuntimeError("模拟后处理崩溃"),
        )
        html = "<!DOCTYPE html><html><head></head><body>test</body></html>"
        state = {"html": html}
        result = await postprocess_html_node(state)

        assert result["html"] == html  # 降级返回原始 HTML
