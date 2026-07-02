"""
nodes/assemble.py — HTML 拼装节点。

将校验后的 5 段 segments 数据填入 HTML 模板，产出完整的动画 HTML。
直接复用现有的 _assemble_animation_html()。
"""
import logging

from backend.graph.state import AnimationState
from backend.prompts import _assemble_animation_html

logger = logging.getLogger(__name__)


async def assemble_html(state: AnimationState) -> dict:
    """将 segments + settings 拼装为完整动画 HTML。

    这是解决 LLM 截断问题的关键：LLM 只输出 ~500-1500 token 的 JSON，
    模板 ~15KB 的 CSS/JS/HTML 在服务端填入。
    """
    segments = state.get("segments", [])
    settings = state.get("settings", {})
    narrative_json = state.get("narrative_json", {})

    if not segments or len(segments) < 3:
        return {"error": "没有足够的数据来拼装 HTML（segments 为空或过少）"}

    # 从 narrative_json 提取时长提示，否则用默认值
    seg_durations = state.get("seg_durations", None)
    if seg_durations is None and narrative_json:
        acts = narrative_json.get("acts", [])
        if acts:
            seg_durations = [act.get("duration_hint", 10) for act in acts[:5]]

    try:
        html_content = _assemble_animation_html(segments, settings, seg_durations)
        logger.info("assemble_html 完成 | html_size=%d", len(html_content))
        return {"html": html_content}
    except (KeyError, ValueError, TypeError, RuntimeError) as exc:
        logger.exception("assemble_html 模板拼装失败")
        return {"error": f"HTML 拼装失败: {exc}"}
