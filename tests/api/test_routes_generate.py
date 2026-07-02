"""
test_routes_generate.py — AI 生成路由测试（需要 mock LLM）。

这些路由是 SSE (Server-Sent Events) 流式端点，需要 mock LLM 避免真实 API 调用。
"""
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def client(mock_llm):
    """FastAPI TestClient（已 mock LLM）。"""
    from app import app
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# Mock helpers
# ═══════════════════════════════════════════════════════════════════════════

def _setup_mock_analyze_topic():
    """Mock analyze_topic 节点输出 outline。"""
    async def _mock(state):
        return {"outline": {"key_concepts": ["概念A", "概念B"], "summary": "测试分析"}}
    return _mock


def _setup_mock_generate_segments():
    """Mock generate_segments 节点输出合法 segments JSON。"""
    async def _mock(state):
        segments = {
            "segments": [
                {"title": f"段{i+1}", "subZh": f"第{i+1}段旁白"}
                for i in range(5)
            ]
        }
        return {"segments_raw": json.dumps(segments, ensure_ascii=False)}
    return _mock


class TestPaperGenerateRoute:
    """POST /paper/generate 路由测试。"""

    def test_missing_pdf_file_returns_422(self, client):
        """缺少 PDF 文件应返回 422。"""
        response = client.post("/paper/generate", data={"focus": "", "settings": "{}"})
        assert response.status_code == 422


class TestGenerateFullRoute:
    """POST /generate/full 测试（三阶段）。"""

    def test_generate_full_returns_sse_stream(self, client, mocker):
        """有效 topic + mock LLM 应流式返回 SSE。"""
        mocker.patch(
            "backend.graph.nodes.plan.analyze_topic",
            return_value={"outline": {"core_idea": "test"}},
        )
        mocker.patch(
            "backend.graph.nodes.generate_narrative.generate_narrative",
            return_value={"narrative_valid": True, "narrative_json": {"title": "test", "acts": []}},
        )
        mocker.patch(
            "backend.graph.nodes.generate_direction.generate_direction",
            return_value={"direction_valid": True, "direction_json": {"acts": []}},
        )
        mocker.patch(
            "backend.graph.nodes.generate_segments.generate_animation",
            return_value={"segments_raw": "{}"},
        )
        mocker.patch(
            "backend.graph.nodes.assemble.assemble_html",
            return_value={"html": "<html>test</html>"},
        )

        response = client.post("/generate/full", json={"topic": "AI", "settings": {}})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_missing_topic_returns_400(self, client):
        """缺少 topic 应返回 400。"""
        response = client.post("/generate/full", json={"topic": "", "settings": {}})
        assert response.status_code == 400
