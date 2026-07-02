"""
html_postprocessor.py —— 动画 HTML 后处理增强管道

对 LLM 生成的 HTML 进行自动增强：
  1. 注入 CSS 设计系统变量（如果缺失）
  2. 添加字体平滑 & 抗锯齿
  3. 注入背景噪点纹理（如果缺失）
  4. 确保 GSAP timeline 注册到 window.__timelines
  5. 修复常见布局/样式问题
  6. 注入无障碍 & 视频导出 meta 标签

用法：
    from backend.html_postprocessor import postprocess_html
    enhanced = postprocess_html(raw_html)
"""

import json
import re
import logging
from typing import Optional

from backend.design_system import (
    CSS_VARIABLE_SYSTEM,
    FONT_SMOOTHING_CSS,
    NOISE_TEXTURE_SVG,
    GSAP_TIMELINE_PATCH,
    VIEWPORT_META,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 检测与注入函数
# ---------------------------------------------------------------------------


def _has_css_variables(html: str) -> bool:
    """检查 HTML 是否已经定义了 CSS 自定义属性。"""
    return bool(re.search(r'--color-\w+\s*:', html))


def _has_font_smoothing(html: str) -> bool:
    """检查是否已有字体平滑设置。"""
    return bool(re.search(r'-webkit-font-smoothing|font-smooth', html))


def _has_noise_texture(html: str) -> bool:
    """检查是否已有噪点纹理。"""
    return bool(re.search(r'feTurbulence|noise-texture|zsj-noise', html))


def _has_gsap_cdn(html: str) -> bool:
    """检查是否引入了 GSAP CDN。"""
    return bool(re.search(r'gsap.*\.js|cdn.*gsap|greensock', html, re.IGNORECASE))


def _has_timelines_registration(html: str) -> bool:
    """检查是否注册了 window.__timelines。"""
    return bool(re.search(r'window\.__timelines', html))


def _has_viewport_meta(html: str) -> bool:
    """检查是否有 viewport meta 标签。"""
    return bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE))


def _has_animation_duration_meta(html: str) -> bool:
    """检查是否有 animation-duration meta 标签。"""
    return bool(re.search(r'animation-duration', html, re.IGNORECASE))


def _inject_into_head(html: str, content: str) -> str:
    """在 </head> 之前注入内容。"""
    if '</head>' in html:
        return html.replace('</head>', f'{content}\n</head>', 1)
    if '<body' in html:
        return re.sub(r'(<body[^>]*>)', rf'<head>\n{content}\n</head>\n\1', html, count=1)
    return re.sub(r'(<html[^>]*>)', rf'\1\n<head>\n{content}\n</head>', html, count=1)


def _inject_into_body_start(html: str, content: str) -> str:
    """在 <body> 开始标签之后注入内容。"""
    return re.sub(r'(<body[^>]*>)', rf'\1\n{content}', html, count=1)


def _inject_before_body_close(html: str, content: str) -> str:
    """在 </body> 之前注入内容。"""
    if '</body>' in html:
        return html.replace('</body>', f'{content}\n</body>', 1)
    if '</html>' in html:
        return html.replace('</html>', f'{content}\n</html>', 1)
    return html + '\n' + content


def _inject_into_style_or_create(html: str, css_content: str) -> str:
    """将 CSS 注入到现有的 <style> 标签中，如果没有则创建一个。"""
    style_match = re.search(r'<style[^>]*>', html, re.IGNORECASE)
    if style_match:
        pos = style_match.end()
        return html[:pos] + '\n' + css_content + '\n' + html[pos:]
    style_tag = f'<style>\n{css_content}\n</style>'
    return _inject_into_head(html, style_tag)


def _strip_markdown_fences(html: str) -> str:
    """去除可能的 Markdown 代码块包裹。"""
    html = html.strip()
    html = re.sub(r'^```(?:html|HTML)?\s*\n?', '', html)
    html = re.sub(r'\n?```\s*$', '', html)
    return html.strip()


def _validate_json_segments(html: str) -> int:
    """验证并报告 JSON segment 数据块的健康状态。返回无效 segment 数量。"""
    pattern = re.compile(
        r'<script\s+type=["\']application/json["\']\s+id=["\']seg-data-(\d+)["\']\s*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    bad_count = 0
    for match in pattern.finditer(html):
        seg_id = match.group(1)
        content = match.group(2).strip()
        if not content:
            logger.warning("JSON segment %s 为空", seg_id)
            bad_count += 1
            continue
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning("JSON segment %s 解析失败: %s | 内容前100字符: %s",
                          seg_id, exc, content[:100])
            bad_count += 1
    if bad_count > 0:
        logger.warning("共 %d 个 JSON segment 存在格式问题，动画可能无法完整渲染", bad_count)
    return bad_count


# ---------------------------------------------------------------------------
# 核心后处理流程
# ---------------------------------------------------------------------------

def _ensure_closing_tags(html: str):
    """如果 LLM 截断了 HTML（缺少闭合标签），自动补全。返回 (html, 补全列表)。"""
    closed = []

    if '</script>' not in html:
        last_script = html.rfind('<script>')
        if last_script == -1:
            last_script = html.rfind('<script ')
        if last_script != -1:
            html = html.rstrip() + '\n})();\n</script>'
            closed.append('</script>+IIFE')
            logger.warning("HTML 缺少 </script> 闭合标签，已自动补全（含 IIFE 闭合）")

    if '</body>' not in html:
        html = html.rstrip() + '\n</body>'
        closed.append('</body>')

    if '</html>' not in html:
        html = html.rstrip() + '\n</html>'
        closed.append('</html>')

    return html, closed


def postprocess_html(
    html: str,
    *,
    inject_css_vars: bool = True,
    inject_font_smoothing: bool = True,
    inject_noise_texture: bool = True,
    inject_gsap_patch: bool = True,
    inject_viewport_meta: bool = True,
    fix_common_issues: bool = True,
) -> str:
    """对动画 HTML 进行全面的后处理增强。

    Parameters
    ----------
    html : str
        原始 HTML 内容。
    inject_css_vars : bool
        如果缺失 CSS 变量，自动注入设计系统。
    inject_font_smoothing : bool
        注入字体抗锯齿 CSS。
    inject_noise_texture : bool
        注入 SVG 噪点纹理背景。
    inject_gsap_patch : bool
        注入 GSAP timeline 自动注册补丁。
    inject_viewport_meta : bool
        注入 viewport meta 标签。
    fix_common_issues : bool
        修复常见布局/样式问题。

    Returns
    -------
    str
        增强后的 HTML。
    """
    original_size = len(html)
    html = _strip_markdown_fences(html)

    if not re.search(r'<!DOCTYPE\s+html|<html', html, re.IGNORECASE):
        logger.warning("HTML 缺少标准结构标签，跳过增强")
        return html

    patches_applied = []

    # 1. 注入 viewport meta
    if inject_viewport_meta and not _has_viewport_meta(html):
        html = _inject_into_head(html, VIEWPORT_META)
        patches_applied.append("viewport meta")

    # 2. 注入 CSS 变量系统
    if inject_css_vars and not _has_css_variables(html):
        html = _inject_into_style_or_create(html, CSS_VARIABLE_SYSTEM)
        patches_applied.append("CSS variables")

    # 3. 注入字体平滑
    if inject_font_smoothing and not _has_font_smoothing(html):
        html = _inject_into_style_or_create(html, FONT_SMOOTHING_CSS)
        patches_applied.append("font smoothing")

    # 4. 注入噪点纹理背景
    if inject_noise_texture and not _has_noise_texture(html):
        html = _inject_into_body_start(html, NOISE_TEXTURE_SVG)
        patches_applied.append("noise texture")

    # 5. 注入 GSAP timeline 注册补丁
    if inject_gsap_patch:
        if _has_gsap_cdn(html) and not _has_timelines_registration(html):
            html = _inject_before_body_close(html, GSAP_TIMELINE_PATCH)
            patches_applied.append("GSAP timeline patch")

    # 6. 修复常见问题
    if fix_common_issues:
        html, fix_count = _apply_common_fixes(html)
        if fix_count > 0:
            patches_applied.append(f"{fix_count} common fixes")

    # 7. 验证 JSON segment 数据块
    bad_segments = _validate_json_segments(html)
    if bad_segments > 0:
        patches_applied.append(f"{bad_segments} bad JSON segments")

    # 8. 自动补全缺失的闭合标签（防止 LLM 截断导致 HTML 不完整）
    html, closed_tags = _ensure_closing_tags(html)
    if closed_tags:
        patches_applied.append(f"auto-closed: {', '.join(closed_tags)}")

    if patches_applied:
        logger.info(
            "HTML 后处理完成 | size_before=%d | size_after=%d | patches=[%s]",
            original_size, len(html), ", ".join(patches_applied),
        )
    else:
        logger.info("HTML 后处理：无需增强（设计系统已完整）")

    return html


def _apply_common_fixes(html: str):
    """修复常见的 HTML/CSS 问题。返回 (修改后的html, 修复次数)。"""
    count = 0

    if re.search(r'<body[^>]*>', html):
        body_tag = re.search(r'<body[^>]*>', html).group()
        if 'overflow' not in body_tag.lower():
            new_body = body_tag.replace('>', ' style="overflow:hidden">')
            html = html.replace(body_tag, new_body, 1)
            count += 1

    if re.search(r'<p>\s*</p>', html):
        html = re.sub(r'<p>\s*</p>', '', html)
        count += 1

    return html, count


# ---------------------------------------------------------------------------
# 快速诊断接口
# ---------------------------------------------------------------------------

def diagnose_html(html: str) -> dict:
    """诊断 HTML 的视觉质量，返回问题列表。"""
    issues = []

    if not _has_css_variables(html):
        issues.append({
            "level": "warning",
            "category": "design-system",
            "message": "缺少 CSS 自定义属性（--color-*, --fs-* 等），视觉一致性无法保证",
        })

    if not _has_gsap_cdn(html):
        issues.append({
            "level": "error",
            "category": "animation-engine",
            "message": "未引入 GSAP CDN，动画可能使用 CSS @keyframes（视频导出质量差）",
        })

    if not _has_timelines_registration(html):
        issues.append({
            "level": "warning",
            "category": "video-export",
            "message": "未注册 window.__timelines，视频导出可能无法正确捕获动画时长",
        })

    if not _has_animation_duration_meta(html):
        issues.append({
            "level": "warning",
            "category": "video-export",
            "message": "缺少 animation-duration meta 标签，视频导出时长将使用默认值",
        })

    if not _has_noise_texture(html):
        issues.append({
            "level": "info",
            "category": "visual-quality",
            "message": "缺少背景噪点纹理，画面可能显得过于平坦",
        })

    if not _has_font_smoothing(html):
        issues.append({
            "level": "info",
            "category": "typography",
            "message": "未设置字体抗锯齿（-webkit-font-smoothing），文字边缘可能不清晰",
        })

    if re.search(r'@keyframes\s+\w+', html):
        issues.append({
            "level": "warning",
            "category": "animation-engine",
            "message": "检测到 CSS @keyframes，视频导出可能丢帧，建议改用 GSAP",
        })

    if re.search(r'setTimeout|setInterval', html):
        issues.append({
            "level": "warning",
            "category": "animation-engine",
            "message": "检测到 setTimeout/setInterval，可能导致动画时序不可预测",
        })

    if re.search(r'mathjax|MathJax', html, re.IGNORECASE):
        if not re.search(r'mathjax.*\.js|MathJax.*\.js', html):
            issues.append({
                "level": "info",
                "category": "math-rendering",
                "message": "引用了 MathJax 但未加载 CDN 脚本",
            })

    return {
        "ok": len([i for i in issues if i["level"] == "error"]) == 0,
        "issue_count": len(issues),
        "issues": issues,
    }
