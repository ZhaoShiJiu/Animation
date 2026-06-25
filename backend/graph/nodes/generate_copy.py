"""
nodes/generate_copy.py — 文案生成节点（two_stage_graph 专用）。

根据 outline + topic + settings 生成 5 幕问题冲突型叙事文案。
"""
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph import get_llm
from backend.graph.state import AnimationState
from backend.prompts import build_copy_system_prompt
from backend.thought_filter import ThoughtProcessFilter
from backend.graph.sse_adapter import get_stream_context

logger = logging.getLogger(__name__)


async def generate_copy(state: AnimationState) -> dict:
    """生成 5 幕叙事文案（CopySchema JSON）。

    复用现有 build_copy_system_prompt()，并注入：
    - analyze_topic 产出的 outline（类别/难度/视觉隐喻）
    - validate_copy 产出的 validation_feedback（重试时修正指令）
    """
    topic = state.get("topic", "")
    settings = state.get("settings", {})
    outline = state.get("outline", {})
    feedback = state.get("validation_feedback", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count > max_retries:
        return {
            "error": f"文案生成重试次数超限（{retry_count}/{max_retries}），请简化主题后重试",
            "copy_valid": False,
        }

    # 构建 system prompt（复用现有函数）
    system_prompt = build_copy_system_prompt(topic, settings)

    # 注入 outline 上下文
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
        system_prompt += outline_block

    messages = [SystemMessage(content=system_prompt)]

    # 用户消息
    user_content = f"请为以下概念生成五幕文案：{topic}"
    if feedback:
        user_content = (
            f"## ⚠️ 上次输出校验失败，请修正后重新输出\n"
            f"{feedback}\n\n"
            f"---\n\n"
            f"{user_content}"
        )
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(temperature=0.8)
    full_response = ""
    thought_filter = ThoughtProcessFilter()
    stream_ctx = get_stream_context()

    try:
        async for chunk in llm.astream(
            messages,
            response_format={"type": "json_object"},
        ):
            visible = thought_filter.feed(chunk.content)
            if visible:
                full_response += visible
                # ★ 推送 token 到 SSE 流（绕过 astream_events 的 bug）
                if stream_ctx:
                    stream_ctx.push_token(visible)

        remaining = thought_filter.flush()
        if remaining:
            full_response += remaining
            if stream_ctx:
                stream_ctx.push_token(remaining)

        copy_json = json.loads(full_response)
        logger.info("generate_copy 完成 | title=%s | acts=%d",
                    copy_json.get("title"), len(copy_json.get("acts", [])))
        return {"copy_json": copy_json}
    except (json.JSONDecodeError, Exception) as exc:
        logger.error("generate_copy JSON 解析失败: %s", exc)
        return {
            "copy_json": {},
            "error": f"LLM 返回格式异常: {exc}",
        }
