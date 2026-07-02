"""
prompts.py — LLM Prompt 构建函数。
"""
import json
import logging
import os
from typing import Optional, List, Dict, Any

from backend.design_system import (
    DURATION_SECONDS_HINT,
    ACT_COLOR_HINTS,
    ACT_DURATION_RATIOS,
    ALLOWED_STYLES,
    ALLOWED_DURATIONS,
    ALLOWED_RATIOS,
    ALLOWED_DEPTHS,
    ALLOWED_RESOLUTIONS,
    RESOLUTION_DIMS,
)

logger = logging.getLogger(__name__)


# ── Prompt builders ──
def build_generation_setting_instructions(settings: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    settings = settings or {}
    return {
        "style": ALLOWED_STYLES.get(settings.get("style"), ALLOWED_STYLES["cinematic"]),
        "duration": ALLOWED_DURATIONS.get(settings.get("duration"), ALLOWED_DURATIONS["medium"]),
        "ratio": ALLOWED_RATIOS.get(settings.get("ratio"), ALLOWED_RATIOS["16:9"]),
        "depth": ALLOWED_DEPTHS.get(settings.get("depth"), ALLOWED_DEPTHS["standard"]),
        "resolution": ALLOWED_RESOLUTIONS.get(settings.get("resolution"), ALLOWED_RESOLUTIONS["1080p"]),
        "narration": "旁白文案要更丰富，字幕节奏要清楚。" if settings.get("narration") else "旁白文字保持精炼，只保留关键解释。",
        "bilingual": "必须提供中英双语字幕。" if settings.get("bilingual", True) else "只使用用户当前语言输出字幕。",
        "mathjax": "需要使用 MathJax 渲染数学公式；请在生成的单文件 HTML 中引入 MathJax CDN，并用 LaTeX 语法书写公式。" if settings.get("mathjax") else "不要引入 MathJax，数学表达使用普通文本或 SVG 图形呈现。",
    }



def _build_design_system_spec(settings: Dict[str, Any], duration_sec: int) -> str:
    """构建精简的设计系统规范文本，供所有动画生成 prompt 复用。

    v2: 大幅精简——LLM 只需遵守核心规则，模板细节由服务端拼装。
    """
    ratio = settings.get("ratio", "16:9")
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = RESOLUTION_DIMS.get(resolution_key, (1920, 1080))

    return f"""## 🎨 核心设计规则（必须遵守）

### CSS 变量（如使用，引用以下变量名）
--color-danger:#DC2626 / --color-mystery:#7C3AED / --color-reveal:#2563EB
--color-insight:#059669 / --color-memory:#D97706
--color-bg:#FAFBFC / --color-text:#0F172A / --color-text-dim:#64748B

### 画布规格
width={res_w}px height={res_h}px overflow:hidden
body {{ margin:0; padding:0; font-family:'MiSans','PingFang SC','Microsoft YaHei',sans-serif; }}

### 动画引擎（强制）
**必须**从 CDN 引入 GSAP：`<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>`
**必须**使用 GSAP timeline 组织所有动画：`const tl = gsap.timeline();`
**必须**将 timeline 注册到全局：`window.__timelines = [tl];`
**绝对禁止**：CSS @keyframes / setTimeout 控制时序 / 用户交互触发动画

### 排版铁律
- 主文字 font-size ≥ 3.5rem，居中，占画面高度 8-12%
- 字幕放在半透明背景条上，底部 8-12% 区域
- 每屏文字总量 ≤ 40 中文字
- 主文字与字幕视觉层级差 ≥ 3:1

### 场景过渡
使用叠化（opacity 交叉淡入淡出 0.3s）、推入（translateX）或缩放聚焦
禁止生硬跳切

### SVG 规则
- viewBox 坐标系，stroke-linecap='round' stroke-linejoin='round'
- 内部属性用单引号（在 JSON 字符串内）
- 需要入场动画的元素加 data-draw='true'

### 视频导出兼容
- <meta name="animation-duration" content="{duration_sec}">
- window.__timelines 包含所有 GSAP timeline
- 所有资源内联（GSAP CDN 除外）"""


def _build_resolution_dims(resolution_key: str) -> tuple:
    """返回 (width, height) 像素值。"""
    return RESOLUTION_DIMS.get(resolution_key, (1920, 1080))


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
    res_w, res_h = RESOLUTION_DIMS.get(resolution_key, (1920, 1080))

    if seg_durations is None:
        seg_durations = [round(duration_sec * r) for r in ACT_DURATION_RATIOS]
    while len(seg_durations) < 5:
        seg_durations.append(10)

    template = _load_animation_template()
    template = template.replace("{{TOTAL_DURATION}}", str(duration_sec))
    template = template.replace("{{SCENE_W}}", str(res_w))
    template = template.replace("{{SCENE_H}}", str(res_h))
    template = template.replace("{{SEGMENT_DURATIONS}}", ", ".join(str(d) for d in seg_durations[:5]))
    template = template.replace("{{PRIMARY_COLOR}}", "#2563EB")
    template = template.replace("{{SECONDARY_COLOR}}", "#7C3AED")

    for i in range(5):
        seg = segments[i] if i < len(segments) else {}
        placeholder = f"{{{{SEGMENT_{i}}}}}"
        template = template.replace(placeholder, json.dumps(seg, ensure_ascii=False))

    return template


def build_animation_from_direction_system_prompt(
    narrative_json: Dict[str, Any],
    direction_json: Dict[str, Any],
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Build prompt for LLM to generate 5 segment visual content
    based on narrative copy + structured direction specs.
    """
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)
    acts = narrative_json.get("acts", [])
    dir_acts = direction_json.get("acts", [])
    narrative_text = json.dumps(narrative_json, ensure_ascii=False, indent=2)
    direction_text = json.dumps(direction_json, ensure_ascii=False, indent=2)
    colors_str = ", ".join(ACT_COLOR_HINTS)

    # Build per-act hints combining narrative + direction
    act_summaries = []
    for i in range(5):
        act = acts[i] if i < len(acts) else {}
        d_act = dir_acts[i] if i < len(dir_acts) else {}
        color = ACT_COLOR_HINTS[i] if i < len(ACT_COLOR_HINTS) else "#2563EB"
        act_summaries.append(
            f"  第{i+1}幕「{act.get("name", "")}」({act.get("duration_hint", 10)}s) | "
            f"大字={act.get("on_screen_text", "")} | "
            f"动效={d_act.get("easing", "")} {d_act.get("entrance_direction", "")} | "
            f"颜色={color}"
        )

    prompt = f"""你是动画内容填充专家。根据文案和动画指导，生成5个段落的最终视觉内容。

## 输出格式
**只输出一个 JSON 对象，不要 Markdown，不要解释，不要代码块。**

```json
{{
  "segments": [
    {{
      "title": "画面大字（≤12字）",
      "titleColor": "#DC2626",
      "subZh": "中文旁白",
      "subEn": "English subtitle",
      "visualSVG": "<svg viewBox='0 0 120 120'>...</svg>"
    }},
    ...
  ]
}}
```

## 每个对象的可选字段
- **title**（必填）：画面大字，≤12字
- **titleColor**：强调色（5段依次用 {colors_str}）
- **subZh**（必填）：中文旁白
- **subEn**：英文旁白
- **body**：补充说明小字
- **bigNum**：大号数字
- **visualSVG**：SVG 图形（段0/1/4推荐）
- **steps**：字符串数组（段2专用，3-5个步骤）
- **compareBefore / compareAfter / compareLabelBefore / compareLabelAfter**：对比新旧认知（段3专用）
- 不需要的字段省略。**visualSVG、steps、compareBefore 每段只能用一个！**

## SVG 规则
- viewBox 坐标系，stroke-linecap='round' stroke-linejoin='round'
- 颜色用 currentColor
- 需要入场动画的元素加 data-draw='true'
- **SVG 内部属性用单引号**（在 JSON 双引号字符串中）

## 五幕文案
{narrative_text}

## 动画指导
{direction_text}

## 段落提示
{chr(10).join(act_summaries)}

## 视觉风格
- 风格：{setting_instructions['style']}
- 时长节奏：{setting_instructions['duration']}
- 讲解深度：{setting_instructions['depth']}

只输出 JSON 对象，一个字都不要多。"""
    return prompt



# ── 三阶段拆分 Prompt：纯文案 ──

def build_narrative_system_prompt(
    topic: str,
    settings: Optional[Dict[str, Any]] = None,
    outline: Optional[Dict[str, Any]] = None,
) -> str:
    """构建纯文案生成的 system prompt。

    只做文案，引用五幕模板但不涉及任何视觉设计内容。
    """
    settings = settings or {}
    outline = outline or {}
    setting_instructions = build_generation_setting_instructions(settings)
    duration_sec = DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60)

    # 注入 outline 上下文
    outline_block = ""
    if outline:
        outline_block = (
            f"\n\n## 概念分析（辅助策划参考）\n"
            f"- 类别：{outline.get('category', '未分类')}\n"
            f"- 难度：{outline.get('difficulty', '标准')}\n"
            f"- 核心概念：{outline.get('core_idea', topic)}\n"
            f"- 推荐视觉隐喻：{', '.join(outline.get('visual_metaphors', []))}\n"
            f"- 推荐叙事角度：{outline.get('narrative_angle', '好奇心驱动')}\n"
            f"- 关键术语：{', '.join(outline.get('key_terms', []))}"
        )

    colors_str = ", ".join(ACT_COLOR_HINTS)

    prompt = f"""你是采用「问题冲突型」叙事结构的科学动画编剧。只输出纯文案，不涉及视觉设计。

## 用户概念
{topic}{outline_block}

## 生成规格
- 总时长：约 {duration_sec} 秒
- 讲解深度：{setting_instructions['depth']}
- 字幕要求：{setting_instructions['bilingual']}

## 五幕叙事模板

**第一幕·认知爆破**（3秒抓注意力）
- 手法四选一：假设危机 / 反常识 / 数据震撼 / 身份代入
- 要求：第一句话就要让观众停下来
- 时长：约占总时长 10-15%
- 画面情绪：紧张、震惊、不可置信

**第二幕·延迟满足**（制造疑问，不给答案）
- 手法：强化错误认知 + 暗示答案相反 + 留下更大疑问
- 要求：让观众产生「到底怎么回事」的焦虑感
- 时长：约占总时长 15-20%
- 画面情绪：困惑、好奇、被吊胃口

**第三幕·层层揭秘**（保持观看，逐步解锁）
- 手法：一问一答 + 连续小反转 + 信息量逐级递增
- 要求：每揭示一层就抛出一个新问题，形成信息阶梯
- 时长：约占总时长 30-40%
- 画面情绪：逐渐理解、跟上了思路

**第四幕·高潮揭晓**（产生「原来如此」）
- 手法：颠覆原有认知 + 揭示核心原理 + 放大对比
- 要求：用一个清晰的视觉类比或逻辑链条完成最终解释
- 时长：约占总时长 15-20%
- 画面情绪：恍然大悟、产生认知快感

**第五幕·记忆钉**（留下传播点）
- 手法：一句话总结 + 金句化表达 + 哲理升华
- 要求：让观众看完后能复述给别人的一句话
- 时长：约占总时长 10-15%
- 画面情绪：满足、想分享

## 输出格式（纯 JSON，不要任何其他内容）
{{{{
  "narrative_type": "problem_conflict",
  "title": "动画标题",
  "total_duration_hint": {duration_sec},
  "acts": [
    {{{{
      "act": 1,
      "name": "认知爆破",
      "goal": "3秒抓住注意力",
      "duration_hint": 8,
      "method_used": "反常识",
      "narration": "中文旁白文字",
      "narration_en": "English narration",
      "on_screen_text": "画面大字≤10字",
      "emotion": "紧张、震惊"
    }}}},
    ...
  ]
}}}}

## 要求
- 旁白口语化，适合朗读，中文每句不超过 35 字
- 英文旁白为中文的准确翻译
- on_screen_text 是大字/金句，每屏 ≤10 字，与旁白互补不重复
- emotion 简洁描述该幕画面情绪（4-10字）
- 输出纯 JSON，不要 markdown 代码块包裹"""
    return prompt


# ── 三阶段拆分 Prompt：动画指导 ──

def build_direction_system_prompt(
    narrative_json: Dict[str, Any],
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """构建动画指导的 system prompt。

    基于纯文案产出结构化的动画指导，严格遵循五幕动效设计语言。
    """
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)
    narrative_text = json.dumps(narrative_json, ensure_ascii=False, indent=2)

    acts = narrative_json.get("acts", [])
    act_hints = []
    for i, act in enumerate(acts):
        color = ACT_COLOR_HINTS[i] if i < len(ACT_COLOR_HINTS) else "#2563EB"
        act_hints.append(
            f"  第{i+1}幕「{act.get('name', '')}」({act.get('duration_hint', 10)}s): "
            f"大字={act.get('on_screen_text', '')} | "
            f"情绪={act.get('emotion', '')} | "
            f"手法={act.get('method_used', '')} | "
            f"推荐色系={color}"
        )

    colors_str = ", ".join(ACT_COLOR_HINTS)

    prompt = f"""你是动画视觉导演。根据已有文案，为每一幕设计具体的动画方案。
请严格遵守对应的五幕动效设计语言。

## 五幕动效设计语言（Motion Design Language）

**第一幕「认知爆破」— 冲击入场**
- easing: back.out(1.7) 或 elastic.out(1, 0.3)
- entrance_direction: 下方弹入（y:80→0, scale:0.8→1.0）
- entrance_duration_range: 0.4–0.6s
- stagger: 0.05s（几乎同时，制造冲击感）
- camera_movement: 推近（scale 1.0→1.05）
- visual_technique: 大号文字过冲回弹
- 颜色: {ACT_COLOR_HINTS[0]} 系，高对比，深色→快速切明亮

**第二幕「延迟满足」— 悬疑慢揭**
- easing: power2.inOut（缓慢、平滑）
- entrance_direction: 透明度渐变（opacity: 0→0.6→1），模糊到清晰
- entrance_duration_range: 1.0–1.5s
- stagger: 0.3s（大量留白）
- camera_movement: 固定
- visual_technique: filter:blur→0
- 颜色: {ACT_COLOR_HINTS[1]} 系，偏冷灰紫

**第三幕「层层揭秘」— 信息阶梯**
- easing: power3.out
- entrance_direction: 左侧滑入（x:-30→0）
- entrance_duration_range: 0.5–0.8s
- stagger: 0.12s（逐条递进）
- camera_movement: 微平移
- visual_technique: 每层揭示后前层暗（opacity:0.5），聚焦最新层；连接线/箭头延伸
- 颜色: {ACT_COLOR_HINTS[2]} 系，清爽蓝白

**第四幕「高潮揭晓」— 认知翻转**
- easing: power4.out（强烈加速→减速）
- entrance_direction: 缩放（1.0→1.15）+ glow 外发光增强
- entrance_duration_range: 0.6–1.0s
- stagger: 不适用（同时动画）
- camera_movement: 推近聚焦核心元素
- visual_technique: 旧认知画面 opacity→0+scale→0.9；新认知 scale:1.1→1.0+opacity:0→1；SVG 外发光滤镜 <filter id="glow">
- 颜色: {ACT_COLOR_HINTS[3]} 系，蓝→绿渐变过渡

**第五幕「记忆钉」— 优雅定格**
- easing: power4.out（最舒缓）
- entrance_direction: 缩放+上浮（scale:0.95→1.0, y:30→0）
- entrance_duration_range: 1.2–1.8s
- stagger: 不适用
- camera_movement: 拉远收束
- visual_technique: 金句居中放大，装饰元素收缩淡出，最终定格≥2s 静态
- 颜色: {ACT_COLOR_HINTS[4]} 系，暖金/琥珀

## 文案内容
{narrative_text}

## 幕次提示
{chr(10).join(act_hints)}

## 输出格式（纯 JSON）
{{{{
  "visual_style": "{settings.get('style', 'cinematic')}",
  "color_palette_flow": "按五幕顺序：{colors_str}",
  "acts": [
    {{{{
      "act": 1,
      "composition": "元素位置描述（居中/偏左/网格）",
      "main_element": "核心视觉元素",
      "bg_color": "#FAFBFC",
      "primary_color": "#DC2626",
      "accent_color": "#F97316",
      "easing": "back.out(1.7)",
      "entrance_direction": "下方弹入",
      "entrance_duration_range": "0.4–0.6s",
      "stagger": "0.05s",
      "camera_movement": "推近",
      "visual_technique": "大号文字过冲回弹",
      "svg_suggestion": "需要的 SVG 形状/结构描述",
      "transition_from_previous": ""
    }}}},
    ...
  ]
}}}}

## 要求
- 每幕必须严格使用对应幕号的动效语言（easing / entrance / camera）
- 颜色使用指定的 hex 色系
- composition 描述元素在画面中的位置和布局
- svg_suggestion 是具体可画的 SVG 描述（形状、结构、数量关系）
- transition_from_previous 描述与前一幕的过渡方式（叠化/推入/缩放聚焦），第一幕可为空
- 输出纯 JSON，不要 Markdown"""
    return prompt

