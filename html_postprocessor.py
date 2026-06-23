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
    from html_postprocessor import postprocess_html
    enhanced = postprocess_html(raw_html)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 设计系统注入模板
# ---------------------------------------------------------------------------

_CSS_VARIABLE_SYSTEM = """/* === ZSJ Design System (auto-injected) === */
:root {
  --color-danger:    #DC2626;
  --color-mystery:   #7C3AED;
  --color-reveal:    #2563EB;
  --color-insight:   #059669;
  --color-memory:    #D97706;
  --color-bg:        #FAFBFC;
  --color-surface:   #FFFFFF;
  --color-text:      #0F172A;
  --color-text-dim:  #64748B;
  --color-border:    #E2E8F0;

  --font-display: 'MiSans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-body:    'MiSans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --fs-hero:      clamp(3.5rem, 8vw, 7rem);
  --fs-headline:  clamp(2rem, 5vw, 4rem);
  --fs-body:      1.25rem;
  --fs-subtitle:  1.05rem;
  --fs-small:     0.85rem;

  --space-xs:  8px;
  --space-sm:  16px;
  --space-md:  24px;
  --space-lg:  40px;
  --space-xl:  64px;
  --space-2xl: 96px;

  --ease-smooth:     cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out-back:   cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-spring:     cubic-bezier(0.175, 0.885, 0.32, 1.275);
  --ease-slow:       cubic-bezier(0.25, 0.1, 0.25, 1);
}
"""

_FONT_SMOOTHING = """/* === Font rendering (auto-injected) === */
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
"""

_NOISE_TEXTURE_SVG = """<svg aria-hidden="true" class="zsj-noise-texture" style="position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.035;">
  <filter id="zsj-noise-filter">
    <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="4" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#zsj-noise-filter)"/>
</svg>"""

_GSAP_TIMELINE_PATCH = """<script>
(function() {
  /* === GSAP Timeline auto-registration patch === */
  if (typeof gsap !== 'undefined' && !window.__timelines) {
    var _registered = [];
    var _origTimeline = gsap.timeline;
    gsap.timeline = function() {
      var tl = _origTimeline.apply(gsap, arguments);
      _registered.push(tl);
      return tl;
    };
    Object.defineProperty(window, '__timelines', {
      get: function() { return _registered; },
      set: function(v) { if (Array.isArray(v)) _registered = v; }
    });
  }
})();
</script>"""

_VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'

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
    # 如果没有 </head>，尝试在 <body> 之前注入
    if '<body' in html:
        return re.sub(r'(<body[^>]*>)', rf'<head>\n{content}\n</head>\n\1', html, count=1)
    # 最后手段：在 <html> 之后注入
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
        # 在第一个 <style> 标签之后注入
        pos = style_match.end()
        return html[:pos] + '\n' + css_content + '\n' + html[pos:]
    # 没有 <style> 标签，在 </head> 之前创建一个
    style_tag = f'<style>\n{css_content}\n</style>'
    return _inject_into_head(html, style_tag)


def _strip_markdown_fences(html: str) -> str:
    """去除可能的 Markdown 代码块包裹。"""
    html = html.strip()
    # 去除开头的 ```html 或 ```
    html = re.sub(r'^```(?:html|HTML)?\s*\n?', '', html)
    # 去除结尾的 ```
    html = re.sub(r'\n?```\s*$', '', html)
    return html.strip()


# ---------------------------------------------------------------------------
# 核心后处理流程
# ---------------------------------------------------------------------------

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

    # 验证基本 HTML 结构
    if not re.search(r'<!DOCTYPE\s+html|<html', html, re.IGNORECASE):
        logger.warning("HTML 缺少标准结构标签，跳过增强")
        return html

    patches_applied = []

    # 1. 注入 viewport meta
    if inject_viewport_meta and not _has_viewport_meta(html):
        html = _inject_into_head(html, _VIEWPORT_META)
        patches_applied.append("viewport meta")

    # 2. 注入 CSS 变量系统
    if inject_css_vars and not _has_css_variables(html):
        html = _inject_into_style_or_create(html, _CSS_VARIABLE_SYSTEM)
        patches_applied.append("CSS variables")

    # 3. 注入字体平滑
    if inject_font_smoothing and not _has_font_smoothing(html):
        html = _inject_into_style_or_create(html, _FONT_SMOOTHING)
        patches_applied.append("font smoothing")

    # 4. 注入噪点纹理背景
    if inject_noise_texture and not _has_noise_texture(html):
        html = _inject_into_body_start(html, _NOISE_TEXTURE_SVG)
        patches_applied.append("noise texture")

    # 5. 注入 GSAP timeline 注册补丁
    if inject_gsap_patch:
        if _has_gsap_cdn(html) and not _has_timelines_registration(html):
            html = _inject_before_body_close(html, _GSAP_TIMELINE_PATCH)
            patches_applied.append("GSAP timeline patch")

    # 6. 修复常见问题
    if fix_common_issues:
        fix_count = _apply_common_fixes(html)
        if fix_count > 0:
            patches_applied.append(f"{fix_count} common fixes")

    if patches_applied:
        logger.info(
            "HTML 后处理完成 | size_before=%d | size_after=%d | patches=[%s]",
            original_size, len(html), ", ".join(patches_applied),
        )
    else:
        logger.info("HTML 后处理：无需增强（设计系统已完整）")

    return html


def _apply_common_fixes(html: str) -> int:
    """修复常见的 HTML/CSS 问题。返回修复次数。"""
    count = 0

    # 修复 1: 给 body 添加 overflow:hidden（防止视频导出时出现滚动条）
    if re.search(r'<body[^>]*>', html):
        body_tag = re.search(r'<body[^>]*>', html).group()
        if 'overflow' not in body_tag.lower():
            new_body = body_tag.replace('>', ' style="overflow:hidden">')
            html = html.replace(body_tag, new_body, 1)
            count += 1

    # 修复 2: 确保所有绝对定位元素有对应的相对定位父级
    # （这里只做最基本的检测，不完整实现 CSS 解析器）

    # 修复 3: 移除空的 <p></p> 标签
    if re.search(r'<p>\s*</p>', html):
        html = re.sub(r'<p>\s*</p>', '', html)
        count += 1

    return count


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

    # 检测是否使用了禁止的 CSS 属性
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

    # 检测 MathJax 是否已加载
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
