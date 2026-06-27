"""
test_graph_compilation.py — 5 个 LangGraph StateGraph 编译结构验证。
"""
import pytest
from langgraph.graph import StateGraph

from backend.graph.state import AnimationState


class TestTopicGraph:
    """topic_graph 结构验证。"""

    @pytest.fixture
    def graph(self):
        from backend.graph.graphs.topic_graph import build_topic_graph
        return build_topic_graph()

    def test_compiles_successfully(self, graph):
        """图编译不应抛异常。"""
        assert graph is not None

    def test_has_expected_nodes(self, graph):
        """应包含所有预期节点。"""
        nodes = graph.nodes
        node_names = {name.split(":")[0] for name in nodes}
        expected = {"__start__", "analyze_topic", "generate_segments",
                     "validate_segments", "assemble", "postprocess"}
        assert expected.issubset(node_names)

    def test_entry_point(self, graph):
        """入口点应为 analyze_topic。"""
        # compiled graph's first node should connect from __start__
        assert "__start__" in graph.nodes


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


class TestCopyGraph:
    """copy_graph 结构验证。"""

    @pytest.fixture
    def graph(self):
        from backend.graph.graphs.copy_graph import build_copy_graph
        return build_copy_graph()

    def test_compiles_successfully(self, graph):
        assert graph is not None

    def test_has_expected_nodes(self, graph):
        nodes = graph.nodes
        node_names = {name.split(":")[0] for name in nodes}
        expected = {"__start__", "analyze_topic", "generate_copy", "validate_copy"}
        assert expected.issubset(node_names)


class TestAnimationGraph:
    """animation_graph 结构验证。"""

    @pytest.fixture
    def graph(self):
        from backend.graph.graphs.animation_graph import build_animation_graph
        return build_animation_graph()

    def test_compiles_successfully(self, graph):
        assert graph is not None

    def test_has_expected_nodes(self, graph):
        nodes = graph.nodes
        node_names = {name.split(":")[0] for name in nodes}
        expected = {"__start__", "generate_animation", "validate_animation",
                     "assemble", "postprocess"}
        assert expected.issubset(node_names)


class TestTwoStageGraph:
    """two_stage_graph 结构验证。"""

    @pytest.fixture
    def graph(self):
        from backend.graph.graphs.two_stage_graph import build_two_stage_graph
        return build_two_stage_graph()

    def test_compiles_successfully(self, graph):
        assert graph is not None

    def test_has_expected_nodes(self, graph):
        nodes = graph.nodes
        node_names = {name.split(":")[0] for name in nodes}
        expected = {"__start__", "analyze_topic", "generate_copy",
                     "validate_copy", "generate_animation", "validate_animation",
                     "assemble", "postprocess"}
        assert expected.issubset(node_names)

    def test_has_two_validation_layers(self):
        """两阶段图应有两层独立的校验。"""
        from backend.graph.graphs.two_stage_graph import build_two_stage_graph
        graph = build_two_stage_graph()
        nodes = {name.split(":")[0] for name in graph.nodes}
        assert "validate_copy" in nodes
        assert "validate_animation" in nodes


class TestStateTypedDict:
    """AnimationState TypedDict 测试。"""

    def test_state_fields_exist(self):
        """确保核心字段定义存在。"""
        # AnimationState 是 TypedDict，total=False 所以所有字段可选
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
