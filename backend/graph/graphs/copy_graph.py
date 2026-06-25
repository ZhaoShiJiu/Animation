"""
graphs/copy_graph.py — 主题 → 五幕文案。

路由: analyze_topic → generate_copy ⇄ validate_copy → END

对应 /generate/copy，只生成文案，不生成动画。
"""
from langgraph.graph import StateGraph, END

from backend.graph.state import AnimationState
from backend.graph.nodes.plan import analyze_topic
from backend.graph.nodes.generate_copy import generate_copy
from backend.graph.nodes.validate import validate_copy
from backend.graph.edges.routing import after_validate_copy

_copy_graph = None


def build_copy_graph() -> StateGraph:
    """构建 topic → copy 的 LangGraph 图。"""
    global _copy_graph
    if _copy_graph is not None:
        return _copy_graph

    graph = StateGraph(AnimationState)

    graph.add_node("analyze_topic", analyze_topic)
    graph.add_node("generate_copy", generate_copy)
    graph.add_node("validate_copy", validate_copy)

    graph.set_entry_point("analyze_topic")
    graph.add_edge("analyze_topic", "generate_copy")
    graph.add_edge("generate_copy", "validate_copy")

    graph.add_conditional_edges(
        "validate_copy",
        after_validate_copy,
        {
            "passed": END,                  # copy 通过 → 结束，返回文案
            "retry": "generate_copy",       # 校验失败 → 重试
            "abort": END,                   # 重试耗尽 → 终止
        },
    )

    _copy_graph = graph.compile()
    return _copy_graph
