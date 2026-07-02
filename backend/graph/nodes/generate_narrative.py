"""
nodes/generate_narrative.py — 纯文案生成节点（三阶段拆分 Phase 1）。

根据 outline + topic + settings 生成 5 幕纯文案（NarrativeOutput JSON）。
不含任何视觉描述——视觉指导由 generate_direction 节点单独产出。
"""
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph import get_llm
from backend.graph.state import AnimationState
from backend.prompts import build_narrative_system_prompt
from backend.thought_filter import ThoughtProcessFilter
from backend.graph.sse_adapter import get_stream_context

logger = logging.getLogger(__name__)


async def generate_narrative(state: AnimationState) -> dict:
    """生成 5 幕纯叙事文案（NarrativeOutput JSON）。

    输入：topic / settings / outline / validation_feedback（如有）
    输出：narrative_json
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
            "narrative_valid": False,
        }

    system_prompt = build_narrative_system_prompt(topic, settings, outline)
    messages = [SystemMessage(content=system_prompt)]

    user_content = f"请为以下概念生成五幕文案：{topic}"
    if feedback:
        user_content = (
            f"## ⚠️ 上次输出校验失败，请修正后重新输出\n"
            f"{feedback}\n\n"
            f"---\n\n"
            f"{user_content}"
        )
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(temperature=0.7)
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
                if stream_ctx:
                    stream_ctx.push_token(visible)

        remaining = thought_filter.flush()
        if remaining:
            full_response += remaining
            if stream_ctx:
                stream_ctx.push_token(remaining)

        narrative_json = json.loads(full_response)
        logger.info("generate_narrative 完成 | title=%s | acts=%d",
                    narrative_json.get("title"), len(narrative_json.get("acts", [])))
        return {"narrative_json": narrative_json}

    except json.JSONDecodeError as exc:
        logger.error("generate_narrative JSON 解析失败: %s", exc)
        return {
            "narrative_json": {},
            "error": f"LLM 返回格式异常——非合法 JSON: {exc}",
        }
    except (ConnectionError, TimeoutError, ValueError) as exc:
        logger.error("generate_narrative LLM 调用失败: %s", exc)
        return {
            "narrative_json": {},
            "error": f"LLM 调用失败: {exc}",
        }
