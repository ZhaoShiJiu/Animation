"""
graphs/animation_graph.py — 五幕文案 → 动画 HTML。

路由: generate_animation ⇄ validate → assemble → postprocess → END

对应 /generate/animation，从文案生成动画。
"""
from langgraph.graph import StateGraph, END

from backend.graph.state import AnimationState
from backend.graph.nodes.generate_segments import generate_animation
from backend.graph.nodes.validate import validate_segments
from backend.graph.nodes.assemble import assemble_html
from backend.graph.nodes.postprocess import postprocess_html_node
from backend.graph.edges.routing import after_validate_segments

_animation_graph = None


def build_animation_graph() -> StateGraph:
    """构建 copy → animation 的 LangGraph 图。"""
    global _animation_graph
    if _animation_graph is not None:
        return _animation_graph

    graph = StateGraph(AnimationState)

    graph.add_node("generate_animation", generate_animation)
    graph.add_node("validate_animation", validate_segments)
    graph.add_node("assemble", assemble_html)
    graph.add_node("postprocess", postprocess_html_node)

    graph.set_entry_point("generate_animation")
    graph.add_edge("generate_animation", "validate_animation")

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

    _animation_graph = graph.compile()
    return _animation_graph
