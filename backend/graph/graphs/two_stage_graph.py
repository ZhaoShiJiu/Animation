"""
graphs/two_stage_graph.py — 主题 → 文案 → 动画 两阶段流程（合并为一个 API）。

路由: analyze_topic → generate_copy ⇄ validate_copy → generate_animation ⇄ validate_animation → assemble → postprocess → END

替换 /generate/copy + /generate/animation 两次请求，合并为单个 /generate/full 路由。
"""
from langgraph.graph import StateGraph, END

from backend.graph.state import AnimationState
from backend.graph.nodes.plan import analyze_topic
from backend.graph.nodes.generate_copy import generate_copy
from backend.graph.nodes.generate_segments import generate_animation
from backend.graph.nodes.validate import validate_copy, validate_segments
from backend.graph.nodes.assemble import assemble_html
from backend.graph.nodes.postprocess import postprocess_html_node
from backend.graph.edges.routing import after_validate_copy, after_validate_segments

_two_stage_graph = None


def build_two_stage_graph() -> StateGraph:
    """构建 topic → copy → animation 的两阶段 LangGraph 图。

    两层重试循环互不干扰：
    - 文案校验失败 → 重试 generate_copy
    - 动画校验失败 → 重试 generate_animation
    """
    global _two_stage_graph
    if _two_stage_graph is not None:
        return _two_stage_graph

    graph = StateGraph(AnimationState)

    graph.add_node("analyze_topic", analyze_topic)
    graph.add_node("generate_copy", generate_copy)
    graph.add_node("validate_copy", validate_copy)
    graph.add_node("generate_animation", generate_animation)
    graph.add_node("validate_animation", validate_segments)  # 复用同一个校验函数
    graph.add_node("assemble", assemble_html)
    graph.add_node("postprocess", postprocess_html_node)

    graph.set_entry_point("analyze_topic")

    graph.add_edge("analyze_topic", "generate_copy")
    graph.add_edge("generate_copy", "validate_copy")

    # 第一层重试：copy 校验
    graph.add_conditional_edges(
        "validate_copy",
        after_validate_copy,
        {
            "passed": "generate_animation",
            "retry": "generate_copy",
            "abort": END,
        },
    )

    graph.add_edge("generate_animation", "validate_animation")

    # 第二层重试：animation 校验
    graph.add_conditional_edges(
        "validate_animation",
        after_validate_segments,
        {
            "passed": "assemble",
            "retry": "generate_animation",
            "abort": END,
        },
    )

    graph.add_edge("assemble", "postprocess")
    graph.add_edge("postprocess", END)

    _two_stage_graph = graph.compile()
    return _two_stage_graph
