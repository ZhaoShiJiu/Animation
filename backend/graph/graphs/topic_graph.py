"""
graphs/topic_graph.py — 主题 → 动画 单图流程。

路由: analyze_topic → generate_segments ⇄ validate_segments → assemble → postprocess → END

替换 /generate 路由。
"""
from langgraph.graph import StateGraph, END

from backend.graph.state import AnimationState
from backend.graph.nodes.plan import analyze_topic
from backend.graph.nodes.generate_segments import generate_segments
from backend.graph.nodes.validate import validate_segments
from backend.graph.nodes.assemble import assemble_html
from backend.graph.nodes.postprocess import postprocess_html_node
from backend.graph.edges.routing import after_validate_segments

# 编译一次，全局复用
_topic_graph = None


def build_topic_graph() -> StateGraph:
    """构建 topic → animation 的 LangGraph 图。"""
    global _topic_graph
    if _topic_graph is not None:
        return _topic_graph

    graph = StateGraph(AnimationState)

    graph.add_node("analyze_topic", analyze_topic)
    graph.add_node("generate_segments", generate_segments)
    graph.add_node("validate_segments", validate_segments)
    graph.add_node("assemble", assemble_html)
    graph.add_node("postprocess", postprocess_html_node)

    graph.set_entry_point("analyze_topic")

    graph.add_edge("analyze_topic", "generate_segments")
    graph.add_edge("generate_segments", "validate_segments")

    graph.add_conditional_edges(
        "validate_segments",
        after_validate_segments,
        {
            "passed": "assemble",
            "retry": "generate_segments",
            "abort": END,
        },
    )

    graph.add_edge("assemble", "postprocess")
    graph.add_edge("postprocess", END)

    _topic_graph = graph.compile()
    return _topic_graph
