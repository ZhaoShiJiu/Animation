"""
nodes/postprocess.py — HTML 后处理节点。

注入 CSS 变量、GSAP 补丁、字体平滑、噪点纹理等。
直接复用现有的 postprocess_html()。
最终 HTML 通过 return state 传递，由 SSE adapter 的 accumulated_state 路径捕获。
"""
import logging

from backend.graph.state import AnimationState
from backend.html_postprocessor import postprocess_html

logger = logging.getLogger(__name__)


async def postprocess_html_node(state: AnimationState) -> dict:
    """对拼装后的 HTML 进行后处理增强。

    注入内容：
    - CSS 设计系统变量（如果缺失）
    - 字体平滑 + 抗锯齿
    - SVG 噪点纹理背景
    - GSAP timeline 注册补丁
    - 自动补全截断的闭合标签
    """
    html = state.get("html", "")

    if not html:
        return {"error": "HTML 为空，无法后处理"}

    try:
        enhanced = postprocess_html(html)
        logger.info("postprocess_html 完成 | size_before=%d | size_after=%d",
                    len(html), len(enhanced))
        return {"html": enhanced}
    except Exception:
        logger.exception("postprocess_html 失败")
        # 后处理失败不阻塞流程，用原始 HTML
        return {"html": html}
