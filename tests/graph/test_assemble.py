"""
test_assemble.py — assemble 节点测试。
"""
import pytest

from backend.graph.nodes.assemble import assemble_html


class TestAssembleHtml:
    """assemble_html 节点测试。"""

    @pytest.mark.asyncio
    async def test_valid_segments_produce_html(self, sample_segments):
        """合法 segments 应产出完整 HTML。"""
        state = {"segments": sample_segments, "settings": {}}
        result = await assemble_html(state)

        assert "html" in result
        assert "error" not in result
        assert "<!DOCTYPE html>" in result["html"]
        assert len(result["html"]) > 1000

    @pytest.mark.asyncio
    async def test_empty_segments_error(self):
        """segments 为空时返回错误。"""
        state = {"segments": [], "settings": {}}
        result = await assemble_html(state)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_too_few_segments_error(self):
        """segments 少于 3 段时返回错误。"""
        state = {
            "segments": [
                {"title": "段1", "subZh": "旁白1"},
                {"title": "段2", "subZh": "旁白2"},
            ],
            "settings": {},
        }
        result = await assemble_html(state)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_custom_settings_propagate(self, sample_segments):
        """settings 应传递到模板替换。"""
        state = {
            "segments": sample_segments,
            "settings": {"duration": "short", "resolution": "720p"},
        }
        result = await assemble_html(state)
        assert "error" not in result
        assert "1280" in result["html"]
        assert "720" in result["html"]

    @pytest.mark.asyncio
    async def test_narrative_json_extracts_durations(self, sample_segments, sample_narrative_json):
        """从 narrative_json 提取时长。"""
        state = {
            "segments": sample_segments,
            "settings": {},
            "narrative_json": sample_narrative_json,
        }
        result = await assemble_html(state)
        assert "error" not in result
        # 第一幕 8s 应在 HTML 中
        assert "8" in result["html"]

    @pytest.mark.asyncio
    async def test_explicit_seg_durations_override(self, sample_segments, sample_narrative_json):
        """显式 seg_durations 优先于 narrative_json 推算。"""
        state = {
            "segments": sample_segments,
            "settings": {},
            "narrative_json": sample_narrative_json,
            "seg_durations": [5, 5, 5, 5, 5],
        }
        result = await assemble_html(state)
        assert "error" not in result
        assert "5, 5, 5, 5, 5" in result["html"]

    @pytest.mark.asyncio
    async def test_exception_handling(self, mocker):
        """拼装异常时应返回 error 而非崩溃。"""
        mocker.patch(
            "backend.graph.nodes.assemble._assemble_animation_html",
            side_effect=RuntimeError("模拟拼装崩溃"),
        )
        state = {
            "segments": [
                {"title": f"段{i}", "subZh": f"旁白{i}"} for i in range(5)
            ],
            "settings": {},
        }
        result = await assemble_html(state)
        assert "error" in result
        assert "模拟拼装崩溃" in result["error"]
