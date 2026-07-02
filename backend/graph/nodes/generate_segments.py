"""
nodes/generate_segments.py — 动画视觉内容生成节点（三张图共用）。

generate_segments:  topic_graph / paper_graph 使用（从 outline + topic 生成 5 段 JSON）
generate_animation:  two_stage_graph 使用（从 copy_json 生成 5 段 JSON）
"""
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph import get_llm
from backend.graph.state import AnimationState
from backend.models import AnimationSegment
from backend.thought_filter import ThoughtProcessFilter
from backend.graph.sse_adapter import get_stream_context
from backend.design_system import ACT_COLOR_HINTS
from backend.prompts import (
    build_generation_setting_instructions,
    build_animation_from_direction_system_prompt,
)

logger = logging.getLogger(__name__)

# ── 从 Pydantic 模型自动生成 JSON 格式说明 ──

def _build_json_format_prompt() -> str:
    """从 AnimationSegment Pydantic 模型生成人类可读的 JSON 格式说明。

    单一数据源原则：改了模型字段，prompt 自动同步。
    """
    schema = AnimationSegment.model_json_schema()
    props = schema["properties"]
    required = set(schema.get("required", []))

    lines = [
        "## 输出格式",
        '输出一个 JSON 对象：{"segments": [5个对象的数组]}',
        "",
        "每个对象的字段：",
    ]
    for name, info in props.items():
        desc = info.get("description", "")
        req_tag = "（必填）" if name in required else "（可选）"
        type_str = _type_label(info)
        lines.append(f"- **{name}**{req_tag}：{desc} | 类型：{type_str}")

    lines.extend([
        "",
        "## 字段约束",
        "- visualSVG、steps、compareBefore 每段只能用一个！",
        "- titleColor 必须是合法 hex 颜色值（如 #DC2626）",
        "- SVG 内部属性用单引号（在 JSON 双引号字符串内）",
        "- 只输出 JSON 对象，不要 Markdown，不要解释，不要代码块",
    ])
    return "\n".join(lines)


def _type_label(info: dict) -> str:
    t = info.get("type", "")
    # 处理 Optional 字段（Pydantic 输出 anyOf: [type, null]）
    if not t and "anyOf" in info:
        types = [o.get("type", "") for o in info["anyOf"] if o.get("type") != "null"]
        t = types[0] if types else ""
    if t == "array":
        items_type = info.get("items", {}).get("type", "string")
        return f"array[{items_type}]"
    if t == "string":
        return "string"
    return t or "string"


# ── generate_segments（topic_graph / paper_graph 使用）──

async def generate_segments(state: AnimationState) -> dict:
    """从 topic/paper outline 生成 5 段动画视觉内容。

    输入：topic / outline / settings / validation_feedback（如有）
    输出：segments_raw（LLM 原始 JSON 字符串）
    """
    topic = state.get("topic", "")
    settings = state.get("settings", {})
    outline = state.get("outline", {})
    feedback = state.get("validation_feedback", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    is_paper = bool(state.get("pdf_text", ""))

    if retry_count > max_retries:
        return {
            "error": f"动画生成重试次数超限（{retry_count}/{max_retries}）",
            "segments_valid": False,
        }

    si = build_generation_setting_instructions(settings)

    # 构建 system prompt
    if is_paper:
        system_prompt = _build_paper_segments_prompt(outline, si)
    else:
        system_prompt = _build_topic_segments_prompt(topic, outline, si)

    # 追加 JSON 格式说明
    system_prompt += "\n\n" + _build_json_format_prompt()

    messages = [SystemMessage(content=system_prompt)]

    # 用户消息
    if is_paper:
        paper_summary = outline.get("paper_summary", topic)
        user_content = (
            f"论文概要：{paper_summary}\n"
            f"核心贡献：{outline.get('core_idea', '')}\n"
            f"方法亮点：{', '.join(outline.get('method_highlights', []))}\n"
            f"关键结果：{outline.get('key_result', '')}"
        )
    else:
        user_content = f"请为以下概念生成5段动画视觉内容：{topic}"

    if feedback:
        user_content = (
            f"## ⚠️ 上次输出校验失败，请修正后重新输出\n{feedback}\n\n---\n\n{user_content}"
        )
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(temperature=0.8)
    stream_ctx = get_stream_context()

    try:
        full_response = ""
        thought_filter = ThoughtProcessFilter()
        async for chunk in llm.astream(
            messages,
            response_format={"type": "json_object"},
        ):
            visible = thought_filter.feed(chunk.content)
            if visible:
                full_response += visible
                if stream_ctx:
                    stream_ctx.push_token(visible)

        remaining = thought_filter.flush()
        if remaining:
            full_response += remaining
            if stream_ctx:
                stream_ctx.push_token(remaining)

        logger.info("generate_segments 完成 | raw_len=%d", len(full_response))
        return {"segments_raw": full_response}
    except (ConnectionError, TimeoutError, ValueError) as exc:
        logger.error("generate_segments LLM 调用失败: %s", exc)
        return {
            "segments_raw": "",
            "error": f"LLM 调用失败: {exc}",
        }
    except Exception as exc:
        logger.exception("generate_segments 未知错误")
        return {
            "segments_raw": "",
            "error": f"生成失败: {exc}",
        }


# ── generate_animation（three_stage_graph 使用）──

async def generate_animation(state: AnimationState) -> dict:
    """从 narrative_json + direction_json 生成 5 段动画视觉内容。

    输入：narrative_json / direction_json / settings / validation_feedback（如有）
    输出：segments_raw（LLM 原始 JSON 字符串）
    """
    narrative_json = state.get("narrative_json", {})
    direction_json = state.get("direction_json", {})
    settings = state.get("settings", {})
    feedback = state.get("validation_feedback", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count > max_retries:
        return {
            "error": f"动画生成重试次数超限（{retry_count}/{max_retries}）",
            "segments_valid": False,
        }

    system_prompt = build_animation_from_direction_system_prompt(
        narrative_json, direction_json, settings
    )

    # 追加 JSON 格式说明
    system_prompt += "\n\n" + _build_json_format_prompt()

    anim_title = narrative_json.get("title", "动画")
    messages = [
        SystemMessage(content=system_prompt),
    ]

    user_content = f"请根据以上文案和动画指导生成5段视觉内容：{anim_title}"
    if feedback:
        user_content = (
            f"## ⚠️ 上次输出校验失败，请修正后重新输出\n{feedback}\n\n---\n\n{user_content}"
        )
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(temperature=0.8)
    stream_ctx = get_stream_context()

    try:
        full_response = ""
        thought_filter = ThoughtProcessFilter()
        async for chunk in llm.astream(
            messages,
            response_format={"type": "json_object"},
        ):
            visible = thought_filter.feed(chunk.content)
            if visible:
                full_response += visible
                if stream_ctx:
                    stream_ctx.push_token(visible)

        remaining = thought_filter.flush()
        if remaining:
            full_response += remaining
            if stream_ctx:
                stream_ctx.push_token(remaining)

        logger.info("generate_animation 完成 | raw_len=%d", len(full_response))
        return {"segments_raw": full_response}
    except (ConnectionError, TimeoutError, ValueError) as exc:
        logger.error("generate_animation LLM 调用失败: %s", exc)
        return {
            "segments_raw": "",
            "error": f"LLM 调用失败: {exc}",
        }
    except Exception as exc:
        logger.exception("generate_animation 未知错误")
        return {
            "segments_raw": "",
            "error": f"生成失败: {exc}",
        }


# ── Prompt 构建辅助 ──

def _build_topic_segments_prompt(topic: str, outline: dict, si: dict) -> str:
    """构建 topic 模式下的 segments 生成 prompt。"""
    return f"""你是动画内容填充专家。为概念「{topic}」创作动画视觉内容。

## 概念分析
- 类别：{outline.get('category', '未分类')}
- 难度：{outline.get('difficulty', '标准')}
- 核心概念：{outline.get('core_idea', topic)}
- 推荐视觉隐喻：{', '.join(outline.get('visual_metaphors', []))}
- 叙事角度：{outline.get('narrative_angle', '好奇心驱动')}

## 5 段落结构
- 段0（6s）：开场冲击 — 反常识/数据震撼 → 推荐使用 visualSVG
- 段1（10s）：悬念铺垫 → 推荐使用 visualSVG
- 段2（22s）：层层解释 → 使用 steps 字符串数组（3-5个步骤）
- 段3（14s）：高潮揭晓 → 使用 compareBefore/compareAfter 对比新旧认知
- 段4（8s）：金句收尾 → 推荐使用 visualSVG

## 颜色分配
5段依次使用：{", ".join(ACT_COLOR_HINTS)}

## SVG 规则
- viewBox 坐标系，stroke-linecap='round' stroke-linejoin='round'
- 颜色用 currentColor
- 需要入场动画的元素加 data-draw='true'
- SVG 内部属性用单引号

## 内容规格
- 视觉风格：{si['style']}
- 讲解深度：{si['depth']}
- 旁白：{si['narration']}
- 字幕：{si['bilingual']}"""


def _build_paper_segments_prompt(outline: dict, si: dict) -> str:
    """构建 paper 模式下的 segments 生成 prompt。"""
    return f"""你是论文讲解动画的内容填充专家。根据论文概要创作动画视觉内容。

## 论文概要
- 领域：{outline.get('category', '未分类')}
- 核心贡献：{outline.get('core_idea', '')}
- 内容摘要：{outline.get('paper_summary', '')}
- 方法亮点：{', '.join(outline.get('method_highlights', []))}
- 关键结果：{outline.get('key_result', '')}
- 推荐视觉隐喻：{', '.join(outline.get('visual_metaphors', []))}

## 论文内容组织（5 段）
- 段0（8s）：研究背景与问题 → 推荐使用 visualSVG
- 段1（12s）：核心洞察/假设 → 推荐使用 visualSVG
- 段2（20s）：方法框架 → 使用 steps 步骤列表
- 段3（14s）：关键实验/结果 → 使用 compareBefore/compareAfter
- 段4（6s）：结论与启发 → 推荐使用 visualSVG

## 论文特别要求
- 准确呈现核心贡献、关键术语、方法流程
- 公式概念用 SVG 图形表达
- 不要捏造论文中没有的数据

## SVG 规则
- viewBox 坐标系，stroke-linecap='round' stroke-linejoin='round'
- 颜色用 currentColor
- 需要入场动画的元素加 data-draw='true'
- SVG 内部属性用单引号

## 内容规格
- 视觉风格：{si['style']}
- 讲解深度：{si['depth']}
- 旁白：{si['narration']}
- 字幕：{si['bilingual']}"""
