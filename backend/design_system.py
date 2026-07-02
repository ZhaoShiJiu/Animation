"""
design_system.py — 设计系统常量，单一数据源。

CSS 变量体系、颜色提示、五幕时长比例、分辨率映射等，
所有模块从此处引用，避免多处重复定义。
"""

# ── 五幕叙事颜色提示 ──
ACT_COLOR_HINTS: tuple[str, ...] = ("#DC2626", "#7C3AED", "#2563EB", "#059669", "#D97706")

# ── 五幕时长占比（认知爆破 / 悬念 / 揭秘 / 高潮 / 金句）──
ACT_DURATION_RATIOS: tuple[float, ...] = (0.12, 0.18, 0.35, 0.20, 0.15)

# ── 五幕名称 ──
ACT_NAMES: tuple[str, ...] = ("认知爆破", "延迟满足", "层层揭秘", "高潮揭晓", "记忆钉")

# ── 五幕图标 ──
ACT_ICONS: tuple[str, ...] = ("💥", "🔮", "🔍", "💡", "📌")

# ── 五幕动效描述（用于 prompt）──
ACT_MOTION_DESCRIPTIONS: tuple[str, ...] = (
    "冲击入场 — back.out(1.7) 弹性缓动，0.4–0.6s，文字带刹车回弹感",
    "悬疑慢揭 — power2.inOut 缓慢平滑，1.0–1.5s，文字从模糊到清晰",
    "信息阶梯 — power3.out 逐条递进，0.5–0.8s，每层揭示后前层变暗",
    "认知翻转 — power4.out 强烈加速→减速，核心元素放大+外发光",
    "优雅定格 — power4.out 最舒缓，1.2–1.8s，金句居中放大后静止2s",
)

# ── CSS 设计系统变量 ──
CSS_VARIABLE_SYSTEM = """/* === ZSJ Design System (auto-injected) === */
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

FONT_SMOOTHING_CSS = """/* === Font rendering (auto-injected) === */
body {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
"""

NOISE_TEXTURE_SVG = """<svg aria-hidden="true" class="zsj-noise-texture" style="position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.035;">
  <filter id="zsj-noise-filter">
    <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="4" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <rect width="100%" height="100%" filter="url(#zsj-noise-filter)"/>
</svg>"""

GSAP_TIMELINE_PATCH = """<script>
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

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'

# ── 分辨率映射 ──
RESOLUTION_DIMS: dict[str, tuple[int, int]] = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "2k": (2048, 1152),
}

# ── 视觉风格映射 ──
ALLOWED_STYLES: dict[str, str] = {
    "cinematic": "电影级叙事：镜头感强、节奏完整、视觉层次丰富。",
    "minimal": "极简专业：留白克制、信息清晰、图形精准。",
    "academic": "教学讲解：结构严谨、步骤明确、适合课堂演示。",
    "futuristic": "未来科技：高对比、科技感视觉、动态 HUD 元素。",
}

# ── 时长映射 ──
ALLOWED_DURATIONS: dict[str, str] = {
    "preview": "快速预览：只生成一页，用来快速展示整体视觉效果；不要制作完整视频流程，不需要多段转场或长时间动画。",
    "short": "约 30 秒，重点突出，快速讲清核心概念。",
    "medium": "约 60 秒，完整讲解主要过程。",
    "long": "约 90 秒，包含更细的铺垫、推演和总结。",
}

# ── 画幅映射 ──
ALLOWED_RATIOS: dict[str, str] = {
    "16:9": "16:9 横屏画布，适合网页和演示。",
    "9:16": "9:16 竖屏画布，适合移动端短视频。",
    "1:1": "1:1 方形画布，适合社交媒体展示。",
}

# ── 讲解深度映射 ──
ALLOWED_DEPTHS: dict[str, str] = {
    "starter": "入门深度：避免术语堆叠，适合第一次接触该主题的观众。",
    "standard": "标准深度：兼顾直观解释和关键专业细节。",
    "expert": "专业深度：加入必要术语、推导逻辑和边界条件。",
}

# ── 分辨率描述映射 ──
ALLOWED_RESOLUTIONS: dict[str, str] = {
    "720p": "1280 × 720 的 720p 容器。",
    "1080p": "1920 × 1080 的 1080p 容器。",
    "2k": "2048 × 1152 的 2K 容器。",
}

# ── 时长（秒）映射 ──
DURATION_SECONDS_HINT: dict[str, int] = {
    "preview": 12,
    "short": 30,
    "medium": 60,
    "long": 90,
}
