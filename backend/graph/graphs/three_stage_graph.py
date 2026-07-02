"""
graphs/three_stage_graph.py — 主题 → 文案 → 动画指导 → 动画 三阶段流程。

路由:
  analyze_topic → generate_narrative ⇄ validate_narrative
                   ↓
                 generate_direction ⇄ validate_direction
                   ↓
                 generate_animation ⇄ validate_animation
                   ↓
                 assemble → postprocess → END

三层独立重试循环，互不干扰。
"""
from langgraph.graph import StateGraph, END

from backend.graph.state import AnimationState
from backend.graph.nodes.plan import analyze_topic
from backend.graph.nodes.generate_narrative import generate_narrative
from backend.graph.nodes.generate_direction import generate_direction
from backend.graph.nodes.generate_segments import generate_animation
from backend.graph.nodes.validate import validate_narrative, validate_direction, validate_segments
from backend.graph.nodes.assemble import assemble_html
from backend.graph.nodes.postprocess import postprocess_html_node
from backend.graph.edges.routing import (
    after_validate_narrative,
    after_validate_direction,
    after_validate_segments,
)


def build_three_stage_graph():
    """构建 topic → narrative → direction → animation 的三阶段 LangGraph 图。

    三层独立重试循环：
    - 文案校验失败 → 重试 generate_narrative
    - 指导校验失败 → 重试 generate_direction
    - 动画校验失败 → 重试 generate_animation
    """
    graph = StateGraph(AnimationState)

    graph.add_node("analyze_topic", analyze_topic)
    graph.add_node("generate_narrative", generate_narrative)
    graph.add_node("validate_narrative", validate_narrative)
    graph.add_node("generate_direction", generate_direction)
    graph.add_node("validate_direction", validate_direction)
    graph.add_node("generate_animation", generate_animation)
    graph.add_node("validate_animation", validate_segments)
    graph.add_node("assemble", assemble_html)
    graph.add_node("postprocess", postprocess_html_node)

    graph.set_entry_point("analyze_topic")

    # 阶段一：文案
    graph.add_edge("analyze_topic", "generate_narrative")
    graph.add_edge("generate_narrative", "validate_narrative")
    graph.add_conditional_edges(
        "validate_narrative",
        after_validate_narrative,
        {
            "passed": "generate_direction",
            "retry": "generate_narrative",
            "abort": END,
        },
    )

    # 阶段二：动画指导
    graph.add_edge("generate_direction", "validate_direction")
    graph.add_conditional_edges(
        "validate_direction",
        after_validate_direction,
        {
            "passed": "generate_animation",
            "retry": "generate_direction",
            "abort": END,
        },
    )

    # 阶段三：动画实现
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

    return graph.compile()
