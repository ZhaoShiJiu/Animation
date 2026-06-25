"""
prompts.py — LLM Prompt 构建函数。
"""
import json
import logging
import os
from typing import Optional, List, Dict, Any

from backend.config import DURATION_SECONDS_HINT

logger = logging.getLogger(__name__)


# ── Prompt builders ──
def build_generation_setting_instructions(settings: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    settings = settings or {}
    allowed_styles = {
        "cinematic": "电影级叙事：镜头感强、节奏完整、视觉层次丰富。",
        "minimal": "极简专业：留白克制、信息清晰、图形精准。",
        "academic": "教学讲解：结构严谨、步骤明确、适合课堂演示。",
        "futuristic": "未来科技：高对比、科技感视觉、动态 HUD 元素。",
    }
    allowed_durations = {
        "preview": "快速预览：只生成一页，用来快速展示整体视觉效果；不要制作完整视频流程，不需要多段转场或长时间动画。",
        "short": "约 30 秒，重点突出，快速讲清核心概念。",
        "medium": "约 60 秒，完整讲解主要过程。",
        "long": "约 90 秒，包含更细的铺垫、推演和总结。",
    }
    allowed_ratios = {
        "16:9": "16:9 横屏画布，适合网页和演示。",
        "9:16": "9:16 竖屏画布，适合移动端短视频。",
        "1:1": "1:1 方形画布，适合社交媒体展示。",
    }
    allowed_depths = {
        "starter": "入门深度：避免术语堆叠，适合第一次接触该主题的观众。",
        "standard": "标准深度：兼顾直观解释和关键专业细节。",
        "expert": "专业深度：加入必要术语、推导逻辑和边界条件。",
    }
    allowed_resolutions = {
        "720p": "1280 × 720 的 720p 容器。",
        "1080p": "1920 × 1080 的 1080p 容器。",
        "2k": "2048 × 1152 的 2K 容器。",
    }
    return {
        "style": allowed_styles.get(settings.get("style"), allowed_styles["cinematic"]),
        "duration": allowed_durations.get(settings.get("duration"), allowed_durations["medium"]),
        "ratio": allowed_ratios.get(settings.get("ratio"), allowed_ratios["16:9"]),
        "depth": allowed_depths.get(settings.get("depth"), allowed_depths["standard"]),
        "resolution": allowed_resolutions.get(settings.get("resolution"), allowed_resolutions["1080p"]),
        "narration": "旁白文案要更丰富，字幕节奏要清楚。" if settings.get("narration") else "旁白文字保持精炼，只保留关键解释。",
        "bilingual": "必须提供中英双语字幕。" if settings.get("bilingual", True) else "只使用用户当前语言输出字幕。",
        "mathjax": "需要使用 MathJax 渲染数学公式；请在生成的单文件 HTML 中引入 MathJax CDN，并用 LaTeX 语法书写公式。" if settings.get("mathjax") else "不要引入 MathJax，数学表达使用普通文本或 SVG 图形呈现。",
    }


def build_copy_system_prompt(topic: str, settings: Optional[Dict[str, Any]] = None) -> str:
    """Build the 5-act problem-conflict narrative copy generation prompt."""
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)
    duration_sec = DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60)

    prompt = f"""你是一个采用「问题冲突型」叙事结构的科学动画编剧。

## 用户概念
{topic}

## 生成规格
- 视觉风格：{setting_instructions['style']}
- 总时长：约 {duration_sec} 秒
- 画幅：{setting_instructions['ratio']}
- 讲解深度：{setting_instructions['depth']}
- 旁白要求：{setting_instructions['narration']}
- 字幕要求：{setting_instructions['bilingual']}

## 叙事结构约束
你必须严格按照以下五幕结构来组织文案，每幕一个场景：

**第一幕·认知爆破**（3秒抓注意力）
- 手法四选一：假设危机 / 反常识 / 数据震撼 / 身份代入
- 要求：第一句话就要让观众停下来
- 时长：约占总时长 10-15%
- 色彩基调：高对比红/橙/黑 → 制造紧张和冲击力 (--color-danger)
- 动效暗示：快速弹性入场，文字带"刹车回弹"感
- 画面情绪：紧张、震惊、不可置信

**第二幕·延迟满足**（制造疑问，不给答案）
- 手法：强化错误认知 + 暗示答案相反 + 留下更大疑问
- 要求：让观众产生「到底怎么回事」的焦虑感
- 时长：约占总时长 15-20%
- 色彩基调：冷紫/灰蓝 → 神秘、悬疑、未知 (--color-mystery)
- 动效暗示：缓慢揭示，文字从模糊到清晰，大量留白
- 画面情绪：困惑、好奇、被吊胃口

**第三幕·层层揭秘**（保持观看，逐步解锁）
- 手法：一问一答 + 连续小反转 + 信息量逐级递增
- 要求：每揭示一层就抛出一个新问题，形成信息阶梯
- 时长：约占总时长 30-40%
- 色彩基调：清爽蓝/青 → 理性、逻辑、清晰 (--color-reveal)
- 动效暗示：逐条 stagger 滑入，每层揭示后前层变暗聚焦新层
- 画面情绪：逐渐理解、跟上了思路

**第四幕·高潮揭晓**（产生「原来如此」）
- 手法：颠覆原有认知 + 揭示核心原理 + 放大对比
- 要求：用一个清晰的视觉类比或逻辑链条完成最终解释
- 时长：约占总时长 15-20%
- 色彩基调：从蓝色渐变过渡到亮绿 (--color-insight)
- 动效暗示：核心概念放大 + glow（外发光），旧认知淡出/缩小
- 画面情绪：恍然大悟、产生认知快感

**第五幕·记忆钉**（留下传播点）
- 手法：一句话总结 + 金句化表达 + 哲理升华
- 要求：让观众看完后能复述给别人的一句话
- 时长：约占总时长 10-15%
- 色彩基调：暖金/琥珀 → 温暖、沉淀、可传播 (--color-memory)
- 动效暗示：文字优雅居中放大，背景安静收束，logo 般定格
- 画面情绪：满足、想分享

## visual_description 编写规范
每个 act 的 visual_description 必须包含以下6个维度的具体描述：
1. **构图**：元素在画面中的位置（居中/偏左/偏右/网格分布），主次关系
2. **颜色**：背景色、主文字色、辅助图形色、强调色
3. **图形**：形状类型（圆形/矩形/连线/箭头/流程图）、数量、大小关系
4. **动效方向**：从哪个方向进入（下方/左侧/缩放/透明度）
5. **镜头运动**：模拟摄像机的运动感（推近/拉远/平移/固定）
6. **SVG建议**：如果适合用 SVG 图形表达——比如数据流向、公式图解、模型结构——请描述应该画什么

示例（好的 visual_description）：
"画面中央偏上是一个大号问号 SVG 图形，灰色半透明，缓缓旋转。背景是冷紫色调渐变。
文字从画面下方 60px 处弹入（弹性缓动），停在正中央，font-weight 900。
2秒后，问号淡出，背景渐变从紫色过渡到蓝色，暗示答案即将揭晓。"

## 输出格式（纯 JSON，不要任何其他内容）
{{
  "narrative_type": "problem_conflict",
  "title": "动画标题",
  "visual_style": "{settings.get('style', 'cinematic')}",
  "color_palette": "按五幕顺序描述色彩变化：第一幕红/橙→第二幕紫/灰→第三幕蓝→第四幕绿→第五幕暖金",
  "total_duration_hint": {duration_sec},
  "acts": [
    {{
      "act": 1,
      "name": "认知爆破",
      "goal": "3秒抓住注意力",
      "duration_hint": 8,
      "method_used": "反常识",
      "narration": "中文旁白文字",
      "narration_en": "English narration",
      "visual_description": "具体画面描述：必须包含构图、颜色、图形、动效方向、镜头运动、SVG建议六个维度",
      "on_screen_text": "画面上展示的关键大字（≤10字）"
    }}
  ]
}}

## 要求
- 旁白口语化，适合朗读，中文每句不超过 35 字
- 英文旁白为中文的准确翻译
- on_screen_text 是大字/金句，每屏 ≤10 字，与旁白互补不重复
- visual_description 必须包含构图+颜色+图形+动效方向+镜头运动+SVG建议六个维度
- color_palette 描述五幕的色彩流变
- 输出纯 JSON，不要 markdown 代码块包裹"""
    return prompt


def _build_design_system_spec(settings: Dict[str, Any], duration_sec: int) -> str:
    """构建共享的设计系统规范文本，供所有动画生成 prompt 复用。"""
    ratio = settings.get("ratio", "16:9")
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = _build_resolution_dims(resolution_key)

    return f"""## 🎨 设计系统（Design System）—— 必须严格遵循

### CSS 变量体系 —— 必须定义在 :root 中
```css
:root {{
  /* 主色调 —— 根据叙事阶段动态切换 */
  --color-danger:    #DC2626;   /* 危机/问题/警告 */
  --color-mystery:   #7C3AED;   /* 悬念/疑问/未知 */
  --color-reveal:    #2563EB;   /* 揭示/解释/逻辑 */
  --color-insight:   #059669;   /* 顿悟/答案/真相 */
  --color-memory:    #D97706;   /* 金句/记忆/总结 */
  --color-bg:        #FAFBFC;   /* 全局背景 */
  --color-surface:   #FFFFFF;   /* 卡片/面板背景 */
  --color-text:      #0F172A;   /* 主文字色 */
  --color-text-dim:  #64748B;   /* 次要文字/字幕 */
  --color-border:    #E2E8F0;   /* 细线/分割 */

  /* 排版层级 */
  --font-display:  'MiSans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-body:     'MiSans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --fs-hero:       clamp(3.5rem, 8vw, 7rem);    /* 主标题大字 */
  --fs-headline:   clamp(2rem, 5vw, 4rem);      /* 场景标题 */
  --fs-body:       1.25rem;                       /* 正文 */
  --fs-subtitle:   1.05rem;                       /* 字幕 */
  --fs-small:      0.85rem;                       /* 标注 */

  /* 间距网格 (8px 基准) */
  --space-xs:  8px;
  --space-sm:  16px;
  --space-md:  24px;
  --space-lg:  40px;
  --space-xl:  64px;
  --space-2xl: 96px;

  /* 缓动函数 —— 必须使用这些！*/
  --ease-smooth:   cubic-bezier(0.22, 0.61, 0.36, 1);     /* 常规过渡 */
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);     /* 弹性出场 */
  --ease-spring:   cubic-bezier(0.175, 0.885, 0.32, 1.275); /* 弹簧感 */
  --ease-slow:     cubic-bezier(0.25, 0.1, 0.25, 1);       /* 慢入慢出 */
}}

body {{
  margin: 0; padding: 0;
  width: {res_w}px; height: {res_h}px;
  overflow: hidden;
  font-family: var(--font-body);
  background: var(--color-bg);
  /* 抗锯齿 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}
```

### 背景层次架构 —— 每个场景必须包含三层背景
```html
<!-- L1: 渐变底色 -->
<div class="bg-base" style="position:absolute;inset:0;background:linear-gradient(135deg, var(--color-bg) 0%, #F1F5F9 100%);"></div>
<!-- L2: 纹理叠加（网格/噪点） -->
<svg class="bg-texture" style="position:absolute;inset:0;width:100%;height:100%;opacity:0.04;"><defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" stroke-width="1"/></pattern></defs><rect width="100%" height="100%" fill="url(#grid)"/></svg>
<!-- L3: 浮动光晕装饰 -->
<div class="bg-glow" style="position:absolute;width:600px;height:600px;border-radius:50%;background:radial-gradient(circle, var(--glow-color, rgba(37,99,235,0.06)) 0%, transparent 70%);filter:blur(60px);"></div>
```
根据每幕的情绪，.bg-glow 的 --glow-color 应该变化。

### GSAP 时间轴 —— 强制要求（不是建议！）

**必须**从 CDN 引入 GSAP：`<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>`

**必须**使用以下时间轴架构组织所有动画：
```javascript
// 全局时间轴 —— 所有场景动画必须挂载到这里
const masterTL = gsap.timeline({{ paused: false }});

// 每个场景的开始时间（秒），由 duration_hint 累加得出
let currentTime = 0;
const sceneDurations = [{{scene_durations}}]; // 从文案中提取的 duration_hint 数组

// 场景切换函数
function buildScene(sceneIndex, duration) {{
  const sceneStart = currentTime;
  const tl = gsap.timeline();

  // === 入场：元素从下往上淡入 ===
  tl.fromTo(`#scene-${{sceneIndex}} .entrance-el`,
    {{ y: 60, opacity: 0 }},
    {{ y: 0, opacity: 1, duration: 0.8, stagger: 0.12, ease: "power3.out" }}
  );

  // === 驻留：微妙呼吸感 ===
  tl.to(`#scene-${{sceneIndex}} .accent-shape`, {{
    scale: 1.04, duration: duration * 0.6, ease: "sine.inOut", yoyo: true, repeat: 1
  }}, "-=0.2");

  // === 退场 ===
  tl.to(`#scene-${{sceneIndex}}`, {{
    opacity: 0, scale: 0.97, duration: 0.5, ease: "power2.in"
  }}, `>+${{duration - 0.8}}`);

  masterTL.add(tl, sceneStart);
  currentTime += duration;
}}

// 注册到全局对象（视频导出需要）
window.__timelines = [masterTL];
```

**绝对禁止**：
- ❌ 使用 CSS @keyframes animation（视频导出时会丢帧）
- ❌ 使用 setTimeout/setInterval 控制动画时序
- ❌ 使用 Math.random() 或 Date.now() 影响动画行为
- ❌ 依赖 scroll、click、hover 等用户交互触发动画

### 五幕动效设计语言（Motion Design Language）

**第一幕「认知爆破」—— 冲击入场**
- easing: back.out(1.7) 或 elastic.out(1, 0.3)
- duration_per_element: 0.4–0.6s
- stagger: 0.05–0.08s（几乎同时，形成冲击感）
- scale: 0.8→1.0 或 y: 80→0
- 背景色: 深色或高饱和 → 快速切到明亮
- 特效: 大号文字 scale 轻微过冲回弹

**第二幕「延迟满足」—— 悬疑慢揭**
- easing: power2.inOut（缓慢、平滑）
- duration_per_element: 1.0–1.5s
- stagger: 0.3–0.5s（大量留白）
- opacity: 0→0.6→1（两次渐变）
- 背景色: 偏冷灰紫色调（--color-mystery）
- 特效: 文字从模糊到清晰（filter: blur→0）

**第三幕「层层揭秘」—— 信息阶梯**
- easing: power3.out
- duration_per_element: 0.5–0.8s
- stagger: 0.12–0.18s（逐条递进）
- transform: x: -30→0（从左侧滑入）
- 每层揭示后，前一层轻微变暗（opacity: 0.5），聚焦最新层
- 背景色: 清爽蓝白色（--color-reveal）
- 特效: 连接线/箭头随内容展开而延伸（stroke-dashoffset 动画）

**第四幕「高潮揭晓」—— 认知翻转**
- easing: power4.out（强烈加速→减速）
- duration: 0.6–1.0s
- 核心元素: scale: 1.0→1.15，glow 滤镜增强
- 背景色: 从蓝色渐变过渡到绿色（--color-insight）
- 特效: 旧认知画面 opacity→0 + scale→0.9；新认知画面 scale: 1.1→1.0 + opacity: 0→1
- 关键概念使用 SVG 外发光滤镜（<filter id="glow">）

**第五幕「记忆钉」—— 优雅定格**
- easing: power4.out（最舒缓）
- duration: 1.2–1.8s
- 金句文字: y: 30→0, scale: 0.95→1.0, 使用弹性缓动
- 背景色: 暖色调（--color-memory），画面逐渐安静
- 装饰元素缓慢收缩/淡出，画面只剩核心金句
- 最终定格至少 2 秒（纯静态，给观众消化时间）

### 排版层次铁律
```
┌─────────────────────────────────┐
│     (顶部留白 ≥ 画面高度 10%)     │
│                                 │
│   主文字 (on_screen_text)        │ ← font-size: var(--fs-hero)
│   font-weight: 900              │   居中，占画面高度 8-12%
│   letter-spacing: -0.03em       │
│                                 │
│   (主文字与字幕之间 ≥ 画面高度 15%)│
│                                 │
│   ┌──────────────────────┐      │
│   │ 中文字幕 (narration)   │      │ ← font-size: var(--fs-subtitle)
│   │ English subtitle     │      │   font-weight: 500
│   └──────────────────────┘      │   底部 8-12% 区域
│   (底部留白 ≥ 画面高度 6%)       │   半透明背景条包裹
└─────────────────────────────────┘
```
**铁律**：
1. 主文字和字幕之间必须有明显的视觉层级差（大小至少 3:1）
2. 字幕必须放在半透明背景条上（background: rgba(255,255,255,0.75) 或 rgba(0,0,0,0.6)），确保在任何背景上都可读
3. 每屏文字总量不超过 40 个中文字（含字幕）

### SVG 图形质量标准
- 所有 SVG 必须指定 viewBox，使用相对坐标
- 图标/图形使用 stroke-linecap="round" stroke-linejoin="round"
- 数据流程/连接线：使用 stroke-dasharray + stroke-dashoffset 动画（"画线"效果）
- 关键图形定义 <filter id="glow"> 外发光滤镜用于强调
- 渐变使用 <linearGradient> 而非纯色填充
- 图形变换优先使用 transform="translate(...) scale(...)" 而非修改坐标

### 场景过渡模式
场景之间**禁止**生硬跳切。使用以下过渡模式之一：
1. **叠化（推荐）**：前场景 opacity 1→0 + 后场景 opacity 0→1，重叠 0.3s
2. **推入**：后场景从右侧 translateX(100%)→0，前场景 0→translateX(-30%)
3. **缩放聚焦**：前场景 scale 1→1.2 + opacity 1→0；后场景 scale 0.9→1 + opacity 0→1

### 视频导出兼容性
- <meta name="animation-duration" content="{duration_sec}">
- window.__timelines 必须包含所有 GSAP timeline
- 动画总时长 = 各场景 duration_hint 之和 + 过渡时间
- 所有资源内联（无外部图片/字体请求，GSAP CDN 除外）"""


def _build_resolution_dims(resolution_key: str) -> tuple:
    """返回 (width, height) 像素值。"""
    mapping = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "2k": (2048, 1152),
    }
    return mapping.get(resolution_key, (1920, 1080))


def _resolution_width(resolution_key: str = "1080p") -> int:
    return _build_resolution_dims(resolution_key)[0]


def _resolution_height(resolution_key: str = "1080p") -> int:
    return _build_resolution_dims(resolution_key)[1]


def _load_animation_template() -> str:
    """加载动画 HTML 骨架模板。"""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "static", "animation-template.html")
    with open(template_path, "r", encoding="utf-8") as fh:
        return fh.read()


def _assemble_animation_html(
    segments: List[Dict[str, Any]],
    settings: Optional[Dict[str, Any]] = None,
    seg_durations: Optional[List[int]] = None,
) -> str:
    """将 LLM 输出的 JSON segment 数据填入模板，拼装完整动画 HTML。

    这是解决 LLM 输出截断问题的关键：LLM 只需输出 ~500 token 的 JSON，
    模板 ~15KB 的 CSS/JS/HTML 在服务端填入，彻底避免截断。
    """
    settings = settings or {}
    duration_sec = DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60)
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = _build_resolution_dims(resolution_key)

    if seg_durations is None:
        # 五幕「问题冲突型」叙事时长占比：认知爆破/悬念/揭秘/高潮/金句
        _ACT_RATIOS = (0.12, 0.18, 0.35, 0.20, 0.15)
        seg_durations = [round(duration_sec * r) for r in _ACT_RATIOS]
    # Ensure we have exactly 5 durations
    while len(seg_durations) < 5:
        seg_durations.append(10)

    template = _load_animation_template()
    template = template.replace("{{TOTAL_DURATION}}", str(duration_sec))
    template = template.replace("{{SCENE_W}}", str(res_w))
    template = template.replace("{{SCENE_H}}", str(res_h))
    template = template.replace("{{SEGMENT_DURATIONS}}", ", ".join(str(d) for d in seg_durations[:5]))
    template = template.replace("{{PRIMARY_COLOR}}", "#2563EB")
    template = template.replace("{{SECONDARY_COLOR}}", "#7C3AED")

    # Fill each segment placeholder with the JSON string
    for i in range(5):
        seg = segments[i] if i < len(segments) else {}
        placeholder = f"{{{{SEGMENT_{i}}}}}"
        template = template.replace(placeholder, json.dumps(seg, ensure_ascii=False))

    return template


def build_animation_from_copy_system_prompt(copy_json: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> str:
    """Build prompt asking LLM to output ONLY a JSON array of 5 segment objects.

    The LLM no longer outputs a full HTML template (~15KB). Instead it outputs
    ~500-1500 tokens of JSON. The server assembles the final HTML.
    This completely eliminates the LLM truncation problem.
    """
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)

    acts = copy_json.get("acts", [])
    copy_text = json.dumps(copy_json, ensure_ascii=False, indent=2)

    # Build act summaries as hints
    act_summaries = []
    color_hints = ["#DC2626", "#7C3AED", "#2563EB", "#059669", "#D97706"]
    for i, act in enumerate(acts):
        act_summaries.append(
            f"  第{i+1}幕「{act.get('name', '')}」({act.get('duration_hint', 10)}s): "
            f"大字={act.get('on_screen_text', '')} | "
            f"旁白={act.get('narration', '')[:50]}"
        )

    prompt = f"""你是动画内容填充专家。根据五幕文案，生成5个段落的视觉内容。

## 输出格式
**只输出一个 JSON 对象，不要 Markdown，不要解释，不要代码块。**

```json
{{{{
  "segments": [
    {{{{
      "title": "画面大字（≤12字）",
      "titleColor": "#DC2626",
      "subZh": "中文旁白",
      "subEn": "English subtitle",
      "visualSVG": "<svg viewBox='0 0 120 120'>...</svg>"
    }}}},
    ...
  ]
}}}}
```

## 每个对象的可选字段
- **title**（必填）：画面大字，≤12字
- **titleColor**：强调色（5段依次用 {", ".join(color_hints)}）
- **subZh**（必填）：中文旁白
- **subEn**：英文旁白
- **body**：补充说明小字
- **bigNum**：大号数字（数据震撼用）
- **visualSVG**：SVG 图形（段0/1/4推荐）
- **steps**：字符串数组（段2专用，3-5个步骤）
- **compareBefore / compareAfter / compareLabelBefore / compareLabelAfter**：对比新旧认知（段3专用）
- 不需要的字段省略。**visualSVG、steps、compareBefore 每段只能用一个！**

## SVG 规则
- viewBox 坐标系，stroke-linecap='round' stroke-linejoin='round'
- 颜色用 currentColor
- 需要入场动画的元素加 data-draw='true'
- **SVG 内部属性用单引号**（因为放在 JSON 双引号字符串中）

## 五幕文案
{copy_text}

## 段落提示
{chr(10).join(act_summaries)}

## 视觉风格
- 风格：{setting_instructions['style']}
- 时长节奏：{setting_instructions['duration']}
- 讲解深度：{setting_instructions['depth']}

只输出 JSON 对象，一个字都不要多。"""
    return prompt
