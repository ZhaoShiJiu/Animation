"""
nodes/generate_direction.py — 动画指导生成节点（三阶段拆分 Phase 2）。

根据纯文案（narrative_json）生成结构化的动画指导（DirectionOutput JSON）。
"""
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph import get_llm
from backend.graph.state import AnimationState
from backend.prompts import build_direction_system_prompt
from backend.thought_filter import ThoughtProcessFilter
from backend.graph.sse_adapter import get_stream_context

logger = logging.getLogger(__name__)


async def generate_direction(state: AnimationState) -> dict:
    """根据文案生成 5 幕结构化的动画指导（DirectionOutput JSON）。

    输入：narrative_json / settings / validation_feedback（如有）
    输出：direction_json
    """
    narrative_json = state.get("narrative_json", {})
    settings = state.get("settings", {})
    feedback = state.get("validation_feedback", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if not narrative_json or not narrative_json.get("acts"):
        return {
            "error": "文案数据为空，无法生成动画指导",
            "direction_valid": False,
        }

    if retry_count > max_retries:
        return {
            "error": f"动画指导生成重试次数超限（{retry_count}/{max_retries}）",
            "direction_valid": False,
        }

    system_prompt = build_direction_system_prompt(narrative_json, settings)
    messages = [SystemMessage(content=system_prompt)]

    title = narrative_json.get("title", "动画")
    user_content = f"请根据以上五幕文案生成动画指导：{title}"
    if feedback:
        user_content = (
            f"## ⚠️ 上次输出校验失败，请修正后重新输出\n"
            f"{feedback}\n\n"
            f"---\n\n"
            f"{user_content}"
        )
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(temperature=0.6)
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

        direction_json = json.loads(full_response)
        logger.info("generate_direction 完成 | style=%s | acts=%d",
                    direction_json.get("visual_style"),
                    len(direction_json.get("acts", [])))
        return {"direction_json": direction_json}

    except json.JSONDecodeError as exc:
        logger.error("generate_direction JSON 解析失败: %s", exc)
        return {
            "direction_json": {},
            "error": f"LLM 返回格式异常——非合法 JSON: {exc}",
        }
    except (ConnectionError, TimeoutError, ValueError) as exc:
        logger.error("generate_direction LLM 调用失败: %s", exc)
        return {
            "direction_json": {},
            "error": f"LLM 调用失败: {exc}",
        }
