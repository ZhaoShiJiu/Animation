"""
test_html_postprocessor.py — HTML 后处理与诊断测试。
"""
import pytest
from backend.html_postprocessor import (
    postprocess_html,
    diagnose_html,
    _strip_markdown_fences,
    _ensure_closing_tags,
    _has_css_variables,
    _has_font_smoothing,
    _has_noise_texture,
    _has_gsap_cdn,
    _has_timelines_registration,
    _has_viewport_meta,
    _validate_json_segments,
)


# ═══════════════════════════════════════════════════════════════════════════
# 辅助检测函数
# ═══════════════════════════════════════════════════════════════════════════

class TestDetectionFunctions:
    """各 _has_* 检测函数测试。"""

    def test_has_css_variables_positive(self):
        assert _has_css_variables("--color-danger: #DC2626") is True

    def test_has_css_variables_negative(self):
        assert _has_css_variables("<div>no vars</div>") is False

    def test_has_font_smoothing_positive(self):
        assert _has_font_smoothing("-webkit-font-smoothing: antialiased") is True

    def test_has_font_smoothing_negative(self):
        assert _has_font_smoothing("body { color: red; }") is False

    def test_has_noise_texture_positive(self):
        assert _has_noise_texture("feTurbulence filter") is True

    def test_has_noise_texture_negative(self):
        assert _has_noise_texture("<div>clean</div>") is False

    def test_has_gsap_cdn_positive(self):
        assert _has_gsap_cdn("gsap.min.js") is True

    def test_has_gsap_cdn_negative(self):
        assert _has_gsap_cdn("<script src='app.js'></script>") is False

    def test_has_timelines_registration_positive(self):
        assert _has_timelines_registration("window.__timelines = []") is True

    def test_has_timelines_registration_negative(self):
        assert _has_timelines_registration("var tl = gsap.timeline()") is False

    def test_has_viewport_meta_positive(self):
        assert _has_viewport_meta('<meta name="viewport" content="width=device-width">') is True

    def test_has_viewport_meta_negative(self):
        assert _has_viewport_meta("<meta charset='utf-8'>") is False


# ═══════════════════════════════════════════════════════════════════════════
# Markdown 代码块剥离
# ═══════════════════════════════════════════════════════════════════════════

class TestStripMarkdownFences:
    """_strip_markdown_fences 测试。"""

    def test_no_fences(self):
        html = "<html><body>test</body></html>"
        assert _strip_markdown_fences(html) == html

    def test_strip_html_fence(self):
        result = _strip_markdown_fences("```html\n<div>test</div>\n```")
        assert result == "<div>test</div>"

    def test_strip_generic_fence(self):
        result = _strip_markdown_fences("```\n<div>test</div>\n```")
        assert result == "<div>test</div>"

    def test_strip_uppercase_html_fence(self):
        result = _strip_markdown_fences("```HTML\n<div>test</div>\n```")
        assert result == "<div>test</div>"


# ═══════════════════════════════════════════════════════════════════════════
# 闭合标签补全
# ═══════════════════════════════════════════════════════════════════════════

class TestEnsureClosingTags:
    """_ensure_closing_tags 测试。"""

    def test_already_complete(self):
        html = "<html><body><p>test</p></body></html>"
        result, closed = _ensure_closing_tags(html)
        assert result == html
        assert closed == []

    def test_missing_body_close(self):
        html = "<html><body><p>test</p>"
        result, closed = _ensure_closing_tags(html)
        assert "</body>" in result
        assert "</html>" in result
        assert "</body>" in closed

    def test_missing_html_close(self):
        html = "<html><body><p>test</p></body>"
        result, closed = _ensure_closing_tags(html)
        assert result.rstrip().endswith("</html>")
        assert "</html>" in closed

    def test_missing_both(self):
        html = "<html><body><p>test</p>"
        result, closed = _ensure_closing_tags(html)
        assert "</body>" in result
        assert "</html>" in result


# ═══════════════════════════════════════════════════════════════════════════
# JSON segment 验证
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateJsonSegments:
    """_validate_json_segments 测试。"""

    def test_no_segments(self):
        assert _validate_json_segments("<html></html>") == 0

    def test_valid_segment(self):
        html = '<script type="application/json" id="seg-data-0">{"title":"test"}</script>'
        assert _validate_json_segments(html) == 0

    def test_invalid_json_segment(self):
        html = '<script type="application/json" id="seg-data-0">{invalid json}</script>'
        assert _validate_json_segments(html) == 1

    def test_empty_segment(self):
        html = '<script type="application/json" id="seg-data-0"></script>'
        assert _validate_json_segments(html) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 完整后处理流程
# ═══════════════════════════════════════════════════════════════════════════

class TestPostprocessHtml:
    """postprocess_html 集成测试。"""

    def test_minimal_html_passthrough(self, sample_html):
        """完整 HTML 应正常处理。"""
        result = postprocess_html(sample_html)
        assert "<!DOCTYPE html>" in result
        assert "gsap" in result.lower()

    def test_no_html_structure(self):
        """无 HTML 结构的纯文本应原样返回。"""
        text = "just some plain text"
        result = postprocess_html(text)
        assert result == text

    def test_inject_css_vars(self):
        """缺失 CSS 变量时应注入。"""
        html = "<!DOCTYPE html><html><head></head><body><p>test</p></body></html>"
        result = postprocess_html(html)
        assert "--color-danger" in result

    def test_no_double_inject_css_vars(self):
        """已有 CSS 变量时不应重复注入。"""
        html = "<!DOCTYPE html><html><head><style>--color-danger: red;</style></head><body></body></html>"
        result = postprocess_html(html)
        # --color-danger 应只出现一次
        assert result.count("--color-danger:") == 1

    def test_inject_viewport_meta(self):
        """缺失 viewport meta 时应注入。"""
        html = "<!DOCTYPE html><html><head></head><body></body></html>"
        result = postprocess_html(html)
        assert 'name="viewport"' in result

    def test_inject_font_smoothing(self):
        """缺失字体平滑时应注入。"""
        html = "<!DOCTYPE html><html><head><style>body{}</style></head><body></body></html>"
        result = postprocess_html(html)
        assert "-webkit-font-smoothing" in result
        assert "antialiased" in result

    def test_inject_noise_texture(self):
        """应注入噪点纹理 SVG。"""
        html = "<!DOCTYPE html><html><head></head><body><div>test</div></body></html>"
        result = postprocess_html(html)
        assert "feTurbulence" in result

    def test_inject_gsap_patch(self):
        """有 GSAP CDN 但无 timeline 注册时应注入补丁。"""
        html = (
            "<!DOCTYPE html><html><head>"
            '<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>'
            "</head><body><div>test</div></body></html>"
        )
        result = postprocess_html(html)
        assert "window.__timelines" in result

    def test_no_gsap_patch_without_cdn(self):
        """无 GSAP CDN 时不注入补丁。"""
        html = "<!DOCTYPE html><html><head></head><body><div>test</div></body></html>"
        result = postprocess_html(html)
        assert "window.__timelines" not in result

    def test_disable_all_injections(self):
        """关闭所有注入选项后不应修改内容。"""
        html = "<!DOCTYPE html><html><head></head><body><p>test</p></body></html>"
        result = postprocess_html(
            html,
            inject_css_vars=False,
            inject_font_smoothing=False,
            inject_noise_texture=False,
            inject_gsap_patch=False,
            inject_viewport_meta=False,
            fix_common_issues=False,
        )
        # 应该只有空白差异
        assert "<p>test</p>" in result

    def test_markdown_fence_strip_in_postprocess(self):
        """后处理应自动剥离 markdown 代码块。"""
        html = "```html\n<!DOCTYPE html><html><head></head><body><p>test</p></body></html>\n```"
        result = postprocess_html(html)
        assert "```" not in result
        assert "<!DOCTYPE html>" in result

    def test_auto_close_tags(self):
        """应自动补全缺失的闭合标签。"""
        html = "<!DOCTYPE html><html><head></head><body><p>test</p>"
        result = postprocess_html(html)
        assert "</body>" in result
        assert "</html>" in result

    def test_common_fix_empty_paragraphs(self):
        """应移除空 <p></p> 标签。"""
        html = "<!DOCTYPE html><html><head></head><body><p></p><p>real</p></body></html>"
        result = postprocess_html(html)
        assert result.count("<p>") <= 1


# ═══════════════════════════════════════════════════════════════════════════
# 诊断
# ═══════════════════════════════════════════════════════════════════════════

class TestDiagnoseHtml:
    """diagnose_html 测试。"""

    def test_complete_html_no_issues(self, sample_html):
        """完整 HTML 应该没有 error 级别问题。"""
        result = diagnose_html(sample_html)
        assert result["ok"] is True
        # 没有 CSS 变量——会有 warning
        css_var_issues = [i for i in result["issues"] if i["category"] == "design-system"]
        assert len(css_var_issues) > 0

    def test_missing_gsap_is_error(self):
        """缺失 GSAP CDN 是 error 级别。"""
        html = "<!DOCTYPE html><html><head></head><body></body></html>"
        result = diagnose_html(html)
        gsap_issues = [i for i in result["issues"] if i["category"] == "animation-engine" and i["level"] == "error"]
        assert len(gsap_issues) > 0
        assert result["ok"] is False

    def test_keyframes_warning(self):
        """CSS @keyframes 触发 warning。"""
        html = (
            "<!DOCTYPE html><html><head><style>@keyframes slide {}</style></head>"
            '<body><script src="gsap.min.js"></script></body></html>'
        )
        result = diagnose_html(html)
        keyframe_issues = [i for i in result["issues"] if "@keyframes" in i.get("message", "")]
        assert len(keyframe_issues) > 0

    def test_settimeout_warning(self):
        """setTimeout/setInterval 触发 warning。"""
        html = (
            "<!DOCTYPE html><html><head></head>"
            "<body><script>setTimeout(function(){}, 1000)</script></body></html>"
        )
        result = diagnose_html(html)
        timeout_issues = [
            i for i in result["issues"]
            if "setTimeout" in i.get("message", "")
        ]
        assert len(timeout_issues) > 0
