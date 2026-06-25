"""
nodes/validate.py — Pydantic 校验节点 + 重试反馈生成。

validate_copy:      校验 copy_json（CopySchema）
validate_segments:  校验 segments_raw（AnimationOutput）

校验失败时生成精确的 validation_feedback，注入下一次 LLM 调用的 prompt。
"""
import json
import logging

from pydantic import ValidationError

from backend.graph.state import AnimationState
from backend.models import CopySchema, AnimationOutput

logger = logging.getLogger(__name__)


async def validate_copy(state: AnimationState) -> dict:
    """校验两阶段流程中 generate_copy 产出的文案 JSON。

    成功：copy_valid=True, retry_count 重置
    失败：copy_valid=False, validation_feedback 精确指出问题
    """
    copy_json = state.get("copy_json", {})
    retry_count = state.get("retry_count", 0)

    if not copy_json:
        return {
            "copy_valid": False,
            "validation_feedback": "上一次未输出任何 JSON，请输出完整的五幕文案 JSON 对象。",
            "retry_count": retry_count + 1,
        }

    try:
        CopySchema.model_validate(copy_json)
        logger.info("validate_copy 通过 | title=%s | acts=%d",
                    copy_json.get("title"), len(copy_json.get("acts", [])))
        return {
            "copy_valid": True,
            "validation_feedback": None,
            "retry_count": 0,
        }
    except ValidationError as exc:
        errors = exc.errors()
        details = []
        for err in errors[:8]:  # 最多报 8 个错误
            loc = " → ".join(str(l) for l in err["loc"])
            details.append(f"  - {loc}: {err['msg']}")

        feedback = f"""上一次输出校验失败，共 {len(errors)} 个错误：

{chr(10).join(details)}

请修正后重新输出完整 JSON 对象，特别注意：
- 顶层必须包含 title、acts 等字段
- acts 必须是数组，每个元素包含 act / name / narration / visual_description 等必填字段
- narration 中文旁白每句不超过 35 字"""

        logger.warning("validate_copy 失败 | errors=%d", len(errors))
        return {
            "copy_valid": False,
            "error": f"文案校验失败: {len(errors)} 个错误",
            "validation_feedback": feedback,
            "retry_count": retry_count + 1,
        }


async def validate_segments(state: AnimationState) -> dict:
    """校验 segments_raw（LLM 原始 JSON 输出）。

    用 AnimationOutput Pydantic 模型做严格校验，
    失败时生成精确到字段的修正指令。
    """
    segments_raw = state.get("segments_raw", "")
    retry_count = state.get("retry_count", 0)

    if not segments_raw.strip():
        return {
            "segments_valid": False,
            "validation_feedback": "上一次未输出任何 JSON，请输出完整的 segments JSON 对象。",
            "retry_count": retry_count + 1,
        }

    try:
        output = AnimationOutput.model_validate_json(segments_raw)
        logger.info("validate_segments 通过 | segments=%d", len(output.segments))
        return {
            "segments": [seg.model_dump() for seg in output.segments],
            "segments_valid": True,
            "validation_feedback": None,
            "retry_count": 0,
        }
    except ValidationError as exc:
        errors = exc.errors()
        details = []
        for err in errors[:8]:
            loc = " → ".join(str(l) for l in err["loc"])
            details.append(f"  - {loc}: {err['msg']}")

        feedback = f"""上一次输出校验失败，共 {len(errors)} 个错误：

{chr(10).join(details)}

请修正后重新输出完整 JSON 对象。特别注意：
- segments 数组必须恰好包含 5 个元素，不能多也不能少
- 每个元素必须包含 title（≤12字）和 subZh 字段
- visualSVG、steps、compareBefore 每个元素中只能出现其中一个
- titleColor 必须是合法的 hex 颜色值（如 #DC2626）
- SVG 内部属性必须使用单引号"""

        logger.warning("validate_segments 失败 | errors=%d", len(errors))
        return {
            "segments_valid": False,
            "error": f"动画校验失败: {len(errors)} 个错误",
            "validation_feedback": feedback,
            "retry_count": retry_count + 1,
        }
    except json.JSONDecodeError as exc:
        snippet = segments_raw[:200]
        logger.warning("validate_segments JSON 解析失败: %s | raw=%s", exc, snippet)
        return {
            "segments_valid": False,
            "error": f"JSON 解析失败: {exc}",
            "validation_feedback": (
                f"上一次输出不是合法的 JSON。请确保：\n"
                f"1. 输出的是纯 JSON 对象（不要 Markdown 代码块）\n"
                f"2. 所有字符串用双引号包裹\n"
                f"3. SVG 内部的属性用单引号\n"
                f"4. 没有多余的尾逗号\n\n"
                f"原始输出前200字符：{snippet}"
            ),
            "retry_count": retry_count + 1,
        }
