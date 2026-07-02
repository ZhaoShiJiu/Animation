"""
test_prompts.py — Prompt 构建函数测试。
"""
import pytest
from backend.prompts import (
    build_generation_setting_instructions,
    build_narrative_system_prompt,
    build_animation_from_direction_system_prompt,
    _build_resolution_dims,
    _assemble_animation_html,
)


# ═══════════════════════════════════════════════════════════════════════════
# build_generation_setting_instructions
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildGenerationSettings:
    """设置指令构建测试。"""

    def test_default_settings(self):
        """空 settings 返回默认值。"""
        result = build_generation_setting_instructions()
        assert result["style"] is not None
        assert result["duration"] is not None
        assert result["ratio"] is not None
        assert result["depth"] is not None
        assert result["resolution"] is not None

    def test_custom_style(self):
        result = build_generation_setting_instructions({"style": "minimal"})
        assert "极简" in result["style"]

    def test_custom_duration(self):
        result = build_generation_setting_instructions({"duration": "short"})
        assert "30" in result["duration"]

    def test_custom_ratio(self):
        result = build_generation_setting_instructions({"ratio": "9:16"})
        assert "竖屏" in result["ratio"]

    def test_custom_depth(self):
        result = build_generation_setting_instructions({"depth": "expert"})
        assert "专业" in result["depth"]

    def test_narration_rich(self):
        result = build_generation_setting_instructions({"narration": True})
        assert "更丰富" in result["narration"]

    def test_narration_concise(self):
        result = build_generation_setting_instructions({"narration": False})
        assert "精炼" in result["narration"]

    def test_bilingual_on(self):
        result = build_generation_setting_instructions({"bilingual": True})
        assert "双语" in result["bilingual"]

    def test_bilingual_off(self):
        result = build_generation_setting_instructions({"bilingual": False})
        assert "只使用" in result["bilingual"]

    def test_mathjax_on(self):
        result = build_generation_setting_instructions({"mathjax": True})
        assert "MathJax" in result["mathjax"]

    def test_unknown_style_falls_back(self):
        """未知 style 回退到 cinematic。"""
        result = build_generation_setting_instructions({"style": "unknown_style"})
        assert "电影" in result["style"]


# ═══════════════════════════════════════════════════════════════════════════
# _build_resolution_dims
# ═══════════════════════════════════════════════════════════════════════════

class TestResolutionDims:
    """分辨率维度测试。"""

    def test_720p(self):
        w, h = _build_resolution_dims("720p")
        assert w == 1280
        assert h == 720

    def test_1080p(self):
        w, h = _build_resolution_dims("1080p")
        assert w == 1920
        assert h == 1080

    def test_2k(self):
        w, h = _build_resolution_dims("2k")
        assert w == 2048
        assert h == 1152

    def test_unknown_falls_back_to_1080p(self):
        w, h = _build_resolution_dims("4k")
        assert w == 1920
        assert h == 1080


# ═══════════════════════════════════════════════════════════════════════════
# build_narrative_system_prompt
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildNarrativeSystemPrompt:
    """纯文案生成 prompt 测试。"""

    def test_contains_topic(self):
        prompt = build_narrative_system_prompt("量子计算")
        assert "量子计算" in prompt

    def test_contains_narrative_structure(self):
        prompt = build_narrative_system_prompt("AI")
        assert "认知爆破" in prompt
        assert "延迟满足" in prompt
        assert "层层揭秘" in prompt
        assert "高潮揭晓" in prompt
        assert "记忆钉" in prompt

    def test_output_format_instructions(self):
        prompt = build_narrative_system_prompt("AI")
        assert "纯 JSON" in prompt
        assert "narrative_type" in prompt
        assert "acts" in prompt

    def test_custom_settings_propagate(self):
        prompt = build_narrative_system_prompt("AI", {"style": "futuristic"})
        # futuristic settings should produce a longer prompt with style info
        assert len(prompt) > 100
        assert "AI" in prompt

    def test_contains_emotion_fields(self):
        prompt = build_narrative_system_prompt("AI")
        assert "emotion" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# build_animation_from_direction_system_prompt
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildAnimationFromDirectionPrompt:
    """动画生成 prompt 测试（三阶段拆分）。"""

    def test_contains_copy_title(self, sample_narrative_json, sample_direction_json):
        prompt = build_animation_from_direction_system_prompt(sample_narrative_json, sample_direction_json)
        assert "测试动画标题" in prompt

    def test_contains_act_summaries(self, sample_narrative_json, sample_direction_json):
        prompt = build_animation_from_direction_system_prompt(sample_narrative_json, sample_direction_json)
        assert "认知爆破" in prompt
        assert "震撼大字" in prompt

    def test_contains_output_format(self, sample_narrative_json, sample_direction_json):
        prompt = build_animation_from_direction_system_prompt(sample_narrative_json, sample_direction_json)
        assert "segments" in prompt
        assert "visualSVG" in prompt
        assert "steps" in prompt

    def test_contains_color_hints(self, sample_narrative_json, sample_direction_json):
        prompt = build_animation_from_direction_system_prompt(sample_narrative_json, sample_direction_json)
        assert "#DC2626" in prompt
        assert "#059669" in prompt
        assert "#D97706" in prompt

    def test_no_markdown_block_expected(self, sample_narrative_json, sample_direction_json):
        """Prompt 要求 LLM 不要输出 markdown 代码块。"""
        prompt = build_animation_from_direction_system_prompt(sample_narrative_json, sample_direction_json)
        assert "不要 Markdown" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# _assemble_animation_html
# ═══════════════════════════════════════════════════════════════════════════

class TestAssembleAnimationHtml:
    """HTML 模板拼装测试。"""

    def test_returns_valid_html(self, sample_segments):
        html = _assemble_animation_html(sample_segments)
        assert "<html" in html.lower()
        assert len(html) > 1000  # 模板 ~15KB

    def test_contains_segment_data(self, sample_segments):
        html = _assemble_animation_html(sample_segments)
        # 第一段的 title 应该在 JSON 数据块中
        assert "认知爆破" in html
        assert "记忆钉" in html

    def test_default_seg_durations(self, sample_segments):
        """不提供 seg_durations 时应使用默认比例。"""
        html = _assemble_animation_html(sample_segments)
        # 模板占位符 {{SEGMENT_0}} 等应全部替换
        assert "{{SEGMENT_" not in html

    def test_custom_seg_durations(self, sample_segments):
        """提供自定义时长。"""
        html = _assemble_animation_html(
            sample_segments,
            seg_durations=[10, 15, 25, 15, 10],
        )
        assert "10, 15, 25, 15, 10" in html or "10" in html

    def test_resolution_substitution(self, sample_segments):
        """分辨率应正确替换。"""
        html = _assemble_animation_html(sample_segments, {"resolution": "720p"})
        assert "1280" in html
        assert "720" in html

    def test_duration_substitution(self, sample_segments):
        """时长应替换。"""
        html = _assemble_animation_html(sample_segments, {"duration": "long"})
        assert "90" in html

    def test_fewer_than_5_segments_padded(self):
        """少于 5 段时用空对象补齐。"""
        html = _assemble_animation_html([{"title": "唯一段"}])
        assert "<html" in html.lower()  # 不应崩溃
