"""
test_models.py — Pydantic 模型校验测试。
"""
import pytest
from pydantic import ValidationError

from backend.models import (
    AnimationSegment,
    AnimationOutput,
    CopySchema,
    CopyAct,
    ChatRequest,
    PassphraseRequest,
    ShareRequest,
    VideoExportRequest,
    LogErrorRequest,
)


# ═══════════════════════════════════════════════════════════════════════════
# AnimationSegment
# ═══════════════════════════════════════════════════════════════════════════

class TestAnimationSegment:
    """AnimationSegment 的 Pydantic 校验测试。"""

    def test_minimal_valid_segment(self):
        """最小合法 segment：只需 title 和 subZh。"""
        seg = AnimationSegment(title="测试标题", subZh="中文旁白")
        assert seg.title == "测试标题"
        assert seg.subZh == "中文旁白"
        assert seg.titleColor == "#DC2626"  # default

    def test_title_max_length(self):
        """title 不能超过 12 字。"""
        with pytest.raises(ValidationError):
            AnimationSegment(title="这是一个超过十二个字的超长标题", subZh="旁白")

    def test_title_exactly_12_chars(self):
        """title 恰好 12 字应通过。"""
        seg = AnimationSegment(title="一二三四五六七八九十一二", subZh="旁白")
        assert len(seg.title) == 12

    def test_title_color_must_be_hex(self):
        """titleColor 必须是合法 hex 颜色。"""
        with pytest.raises(ValidationError):
            AnimationSegment(title="标题", subZh="旁白", titleColor="red")

    def test_title_color_valid_hex(self):
        """合法 hex 颜色通过。"""
        seg = AnimationSegment(title="标题", subZh="旁白", titleColor="#FF5733")
        assert seg.titleColor == "#FF5733"

    def test_mutually_exclusive_visual_svg_and_steps(self):
        """visualSVG 和 steps 不能同时出现。"""
        with pytest.raises(ValidationError) as exc_info:
            AnimationSegment(
                title="标题",
                subZh="旁白",
                visualSVG="<svg viewBox='0 0 10 10'></svg>",
                steps=["步骤1", "步骤2"],
            )
        assert "每段只能用一个" in str(exc_info.value)

    def test_mutually_exclusive_svg_and_compare(self):
        """visualSVG 和 compareBefore 不能同时出现。"""
        with pytest.raises(ValidationError):
            AnimationSegment(
                title="标题",
                subZh="旁白",
                visualSVG="<svg viewBox='0 0 10 10'></svg>",
                compareBefore="旧认知",
            )

    def test_mutually_exclusive_steps_and_compare(self):
        """steps 和 compareBefore 不能同时出现。"""
        with pytest.raises(ValidationError):
            AnimationSegment(
                title="标题",
                subZh="旁白",
                steps=["a", "b"],
                compareBefore="旧认知",
            )

    def test_only_one_visual_type_allowed(self):
        """三者全出现——报错。"""
        with pytest.raises(ValidationError):
            AnimationSegment(
                title="标题",
                subZh="旁白",
                visualSVG="<svg/>",
                steps=["a"],
                compareBefore="旧",
            )

    def test_all_optional_fields(self):
        """全部可选字段填充。"""
        seg = AnimationSegment(
            title="完整标题",
            titleColor="#7C3AED",
            subZh="中文旁白内容",
            subEn="English subtitle",
            body="补充说明小字",
            bigNum="99",
            visualSVG="<svg viewBox='0 0 100 100'><circle cx='50' cy='50' r='40'/></svg>",
        )
        assert seg.bigNum == "99"
        assert seg.body == "补充说明小字"
        assert seg.subEn == "English subtitle"

    def test_steps_field(self):
        """steps 字段包含 3-5 个步骤。"""
        seg = AnimationSegment(
            title="步骤标题",
            subZh="步骤说明",
            steps=["第一步", "第二步", "第三步"],
        )
        assert len(seg.steps) == 3

    def test_compare_fields(self):
        """compare 相关字段。"""
        seg = AnimationSegment(
            title="对比标题",
            subZh="对比说明",
            compareBefore="旧认知",
            compareAfter="新认知",
            compareLabelBefore="以前",
            compareLabelAfter="现在",
        )
        assert seg.compareBefore == "旧认知"
        assert seg.compareAfter == "新认知"


# ═══════════════════════════════════════════════════════════════════════════
# AnimationOutput
# ═══════════════════════════════════════════════════════════════════════════

class TestAnimationOutput:
    """AnimationOutput 校验测试。"""

    def test_valid_output(self, sample_segments):
        """恰好 5 段的合法输出。"""
        output = AnimationOutput(segments=sample_segments)
        assert len(output.segments) == 5

    def test_too_few_segments(self, sample_segments):
        """少于 5 段应报错。"""
        with pytest.raises(ValidationError):
            AnimationOutput(segments=sample_segments[:3])

    def test_too_many_segments(self):
        """多于 5 段应报错。"""
        with pytest.raises(ValidationError):
            AnimationOutput(segments=[
                AnimationSegment(title=f"段{i}", subZh=f"旁白{i}")
                for i in range(6)
            ])

    def test_validate_json_string(self, sample_segments):
        """通过 model_validate_json 从 JSON 字符串校验。"""
        import json
        json_str = json.dumps({"segments": sample_segments}, ensure_ascii=False)
        output = AnimationOutput.model_validate_json(json_str)
        assert len(output.segments) == 5


# ═══════════════════════════════════════════════════════════════════════════
# CopySchema / CopyAct
# ═══════════════════════════════════════════════════════════════════════════

class TestCopySchema:
    """CopySchema 校验测试。"""

    def test_valid_copy_schema(self, sample_copy_json):
        """合法文案应通过校验。"""
        copy = CopySchema.model_validate(sample_copy_json)
        assert copy.title == "测试动画标题"
        assert len(copy.acts) == 5

    def test_empty_acts_default(self):
        """acts 默认为空列表。"""
        copy = CopySchema(title="空文案", acts=[])
        assert copy.acts == []

    def test_missing_title(self):
        """缺少 title 应报错。"""
        with pytest.raises(ValidationError):
            CopySchema(acts=[])

    def test_default_narrative_type(self):
        """narrative_type 默认值。"""
        copy = CopySchema(title="标题", acts=[])
        assert copy.narrative_type == "problem_conflict"

    def test_act_fields(self):
        """CopyAct 各字段校验。"""
        act = CopyAct(
            act=1,
            name="测试幕",
            goal="测试目标",
            duration_hint=10,
            method_used="反常识",
            narration="这是一个测试旁白文案",
            narration_en="Test narration",
            visual_description="画面描述",
            on_screen_text="大字",
        )
        assert act.act == 1
        assert act.method_used == "反常识"


# ═══════════════════════════════════════════════════════════════════════════
# Request models
# ═══════════════════════════════════════════════════════════════════════════

class TestChatRequest:
    """ChatRequest 测试。"""

    def test_minimal_request(self):
        req = ChatRequest(topic="测试主题")
        assert req.topic == "测试主题"
        assert req.history is None
        assert req.settings is None

    def test_with_settings(self):
        req = ChatRequest(topic="主题", settings={"style": "cinematic"})
        assert req.settings["style"] == "cinematic"


class TestPassphraseRequest:
    """PassphraseRequest 测试。"""

    def test_valid_passphrase(self):
        req = PassphraseRequest(passphrase="test123")
        assert req.passphrase == "test123"


class TestShareRequest:
    """ShareRequest 测试。"""

    def test_valid_share_request(self):
        req = ShareRequest(
            html="<div>test</div>",
            expiresIn="1h",
            password="123456",
        )
        assert req.password == "123456"

    def test_password_too_short(self):
        """密码少于 4 位应报错。"""
        with pytest.raises(ValidationError):
            ShareRequest(html="<div>t</div>", expiresIn="1h", password="123")

    def test_password_too_long(self):
        """密码超过 20 位应报错。"""
        with pytest.raises(ValidationError):
            ShareRequest(html="<div>t</div>", expiresIn="1h", password="1" * 21)


class TestVideoExportRequest:
    """VideoExportRequest 测试。"""

    def test_minimal_request(self):
        req = VideoExportRequest(html="<div>test</div>")
        assert req.width == 1920
        assert req.height == 1080
        assert req.fps == 24

    def test_width_out_of_range(self):
        with pytest.raises(ValidationError):
            VideoExportRequest(html="<div>t</div>", width=100)

    def test_fps_out_of_range(self):
        with pytest.raises(ValidationError):
            VideoExportRequest(html="<div>t</div>", fps=120)

    def test_invalid_expires_in(self):
        with pytest.raises(ValidationError):
            VideoExportRequest(html="<div>t</div>", expires_in="2h")


class TestLogErrorRequest:
    """LogErrorRequest 测试。"""

    def test_empty_errors(self):
        req = LogErrorRequest()
        assert req.errors == []

    def test_with_errors(self):
        req = LogErrorRequest(errors=[{"message": "test error"}])
        assert len(req.errors) == 1
