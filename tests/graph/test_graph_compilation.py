"""
test_graph_compilation.py — LangGraph StateGraph 编译结构验证。
"""
import pytest
from langgraph.graph import StateGraph

from backend.graph.state import AnimationState


class TestPaperGraph:
    """paper_graph 结构验证。"""

    @pytest.fixture
    def graph(self):
        from backend.graph.graphs.paper_graph import build_paper_graph
        return build_paper_graph()

    def test_compiles_successfully(self, graph):
        assert graph is not None

    def test_has_expected_nodes(self, graph):
        nodes = graph.nodes
        node_names = {name.split(":")[0] for name in nodes}
        expected = {"__start__", "analyze_paper", "generate_segments",
                     "validate_segments", "assemble", "postprocess"}
        assert expected.issubset(node_names)


class TestThreeStageGraph:
    """three_stage_graph 结构验证。"""

    @pytest.fixture
    def graph(self):
        from backend.graph.graphs.three_stage_graph import build_three_stage_graph
        return build_three_stage_graph()

    def test_compiles_successfully(self, graph):
        assert graph is not None

    def test_has_expected_nodes(self, graph):
        nodes = graph.nodes
        node_names = {name.split(":")[0] for name in nodes}
        expected = {
            "__start__", "analyze_topic",
            "generate_narrative", "validate_narrative",
            "generate_direction", "validate_direction",
            "generate_animation", "validate_animation",
            "assemble", "postprocess",
        }
        assert expected.issubset(node_names)

    def test_has_three_validation_layers(self):
        """三阶段图应有三层独立的校验。"""
        from backend.graph.graphs.three_stage_graph import build_three_stage_graph
        graph = build_three_stage_graph()
        nodes = {name.split(":")[0] for name in graph.nodes}
        assert "validate_narrative" in nodes
        assert "validate_direction" in nodes
        assert "validate_animation" in nodes


class TestStateTypedDict:
    """AnimationState TypedDict 测试。"""

    def test_state_fields_exist(self):
        """确保核心字段定义存在。"""
        state: AnimationState = {}
        state["topic"] = "test"
        state["retry_count"] = 0
        state["max_retries"] = 2
        assert state["topic"] == "test"

    def test_control_fields_default_behavior(self):
        """控制字段默认行为。"""
        state: AnimationState = {"topic": "AI"}
        assert state.get("retry_count", 0) == 0
        assert state.get("max_retries", 2) == 2
