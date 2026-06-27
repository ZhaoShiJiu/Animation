"""
test_validate.py — validate 节点测试。
"""
import json
import pytest
from unittest.mock import AsyncMock

from backend.graph.nodes.validate import validate_copy, validate_segments


# ═══════════════════════════════════════════════════════════════════════════
# validate_copy
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateCopy:
    """validate_copy 节点测试。"""

    @pytest.mark.asyncio
    async def test_valid_copy_passes(self, sample_copy_json):
        """合法文案应通过校验。"""
        state = {"copy_json": sample_copy_json, "retry_count": 0}
        result = await validate_copy(state)
        assert result["copy_valid"] is True
        assert result["validation_feedback"] is None
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_copy_json_fails(self):
        """空字典应不通过。"""
        state = {"copy_json": {}, "retry_count": 0}
        result = await validate_copy(state)
        assert result["copy_valid"] is False
        assert "validation_feedback" in result
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_missing_copy_json_fails(self):
        """完全缺失 copy_json 应不通过。"""
        state = {"retry_count": 0}
        result = await validate_copy(state)
        assert result["copy_valid"] is False
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_missing_title_fails(self):
        """缺少 title 字段应不通过。"""
        state = {
            "copy_json": {"narrative_type": "problem_conflict", "acts": []},
            "retry_count": 0,
        }
        result = await validate_copy(state)
        assert result["copy_valid"] is False

    @pytest.mark.asyncio
    async def test_bad_act_structure_fails(self):
        """act 结构不完整应不通过。"""
        state = {
            "copy_json": {
                "title": "测试",
                "acts": [{"act": 1, "name": "缺少必填字段"}],
            },
            "retry_count": 0,
        }
        result = await validate_copy(state)
        assert result["copy_valid"] is False

    @pytest.mark.asyncio
    async def test_retry_count_increments(self):
        """校验失败时 retry_count 递增。"""
        state = {"copy_json": {}, "retry_count": 2}
        result = await validate_copy(state)
        assert result["retry_count"] == 3

    @pytest.mark.asyncio
    async def test_pass_resets_retry_count(self):
        """校验通过时 retry_count 重置为 0。"""
        state = {
            "copy_json": {
                "title": "重置测试",
                "acts": [],
            },
            "retry_count": 5,
        }
        result = await validate_copy(state)
        assert result["retry_count"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# validate_segments
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateSegments:
    """validate_segments 节点测试。"""

    @pytest.mark.asyncio
    async def test_valid_segments_pass(self, sample_segments):
        """合法 segments 应通过校验。"""
        json_str = json.dumps({"segments": sample_segments}, ensure_ascii=False)
        state = {"segments_raw": json_str, "retry_count": 0}
        result = await validate_segments(state)

        assert result["segments_valid"] is True
        assert result["validation_feedback"] is None
        assert result["retry_count"] == 0
        assert len(result["segments"]) == 5

    @pytest.mark.asyncio
    async def test_empty_segments_raw_fails(self):
        """空字符串应不通过。"""
        state = {"segments_raw": "", "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False

    @pytest.mark.asyncio
    async def test_whitespace_only_fails(self):
        """仅有空白应不通过。"""
        state = {"segments_raw": "   ", "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False

    @pytest.mark.asyncio
    async def test_invalid_json_fails(self):
        """非法 JSON 应不通过。"""
        state = {"segments_raw": "not valid json", "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False
        assert "JSON" in result.get("error", "") or "JSON" in result.get("validation_feedback", "")

    @pytest.mark.asyncio
    async def test_too_few_segments_fails(self):
        """少于 5 段应不通过。"""
        json_str = json.dumps({"segments": [
            {"title": "段1", "subZh": "旁白1"},
        ]})
        state = {"segments_raw": json_str, "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False

    @pytest.mark.asyncio
    async def test_too_many_segments_fails(self):
        """多于 5 段应不通过。"""
        segs = [{"title": f"段{i}", "subZh": f"旁白{i}"} for i in range(6)]
        json_str = json.dumps({"segments": segs})
        state = {"segments_raw": json_str, "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False

    @pytest.mark.asyncio
    async def test_mutually_exclusive_violation_fails(self):
        """visualSVG/steps/compareBefore 互斥违规应不通过。"""
        seg = {
            "title": "违规段",
            "subZh": "同时有 SVG 和 steps",
            "visualSVG": "<svg viewBox='0 0 10 10'></svg>",
            "steps": ["步骤1", "步骤2"],
        }
        segs = [{"title": f"段{i}", "subZh": f"旁白{i}"} for i in range(4)]
        segs.insert(2, seg)  # 插入违规段，共5段
        json_str = json.dumps({"segments": segs})
        state = {"segments_raw": json_str, "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False

    @pytest.mark.asyncio
    async def test_title_too_long_fails(self):
        """title 超过 12 字应不通过。"""
        segs = [{"title": "这是一个超过十二个字的超长标题测试", "subZh": "旁白"}]
        segs += [{"title": f"段{i}", "subZh": f"旁白{i}"} for i in range(2, 6)]
        json_str = json.dumps({"segments": segs})
        state = {"segments_raw": json_str, "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False

    @pytest.mark.asyncio
    async def test_retry_count_increments(self):
        """校验失败时 retry_count 递增。"""
        state = {"segments_raw": "", "retry_count": 1}
        result = await validate_segments(state)
        assert result["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_missing_segments_key_fails(self):
        """JSON 顶层缺少 segments 键应不通过。"""
        json_str = json.dumps({"wrong_key": []})
        state = {"segments_raw": json_str, "retry_count": 0}
        result = await validate_segments(state)
        assert result["segments_valid"] is False
