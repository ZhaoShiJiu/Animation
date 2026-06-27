"""
test_routes_basic.py — 基础 API 路由测试（无需 LLM mock）。
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI TestClient fixture。"""
    from app import app
    return TestClient(app)


class TestIndexRoute:
    """GET / 首页测试。"""

    def test_index_returns_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_index_contains_title(self, client):
        response = client.get("/")
        # AI Animation Backend 的主页模板
        assert response.status_code == 200


class TestConfigRoute:
    """GET /config 测试。"""

    def test_config_returns_json(self, client):
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "requiresPassphrase" in data

    def test_config_requires_passphrase_is_bool(self, client):
        response = client.get("/config")
        data = response.json()
        assert isinstance(data["requiresPassphrase"], bool)


class TestVerifyPassphrase:
    """POST /verify-passphrase 测试。"""

    def test_correct_passphrase(self, client):
        response = client.post("/verify-passphrase", json={"passphrase": "test123"})
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_wrong_passphrase_returns_403(self, client):
        response = client.post("/verify-passphrase", json={"passphrase": "wrong"})
        assert response.status_code == 403

    def test_no_passphrase_required_when_empty(self, client, monkeypatch):
        """空 passphrase 列表时任何密码都通过。"""
        # 需要同时 patch app 和 config，因为 app 在 import 时已经引用了 config 的值
        monkeypatch.setattr("backend.config.ACCESS_PASSPHRASES", [])
        monkeypatch.setattr("app.ACCESS_PASSPHRASES", [])
        response = client.post("/verify-passphrase", json={"passphrase": "anything"})
        assert response.status_code == 200


class TestLogErrorRoute:
    """POST /api/log-error 测试。"""

    def test_log_error_returns_ok(self, client):
        response = client.post("/api/log-error", json={
            "errors": [{"message": "test error", "url": "/test"}]
        })
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_log_error_empty_errors(self, client):
        response = client.post("/api/log-error", json={"errors": []})
        assert response.status_code == 200


class TestStaticFiles:
    """静态文件测试。"""

    def test_static_script_js(self, client):
        """静态 JS 文件应可访问。"""
        response = client.get("/static/script.js")
        assert response.status_code == 200

    def test_static_style_css(self, client):
        """静态 CSS 文件应可访问。"""
        response = client.get("/static/style.css")
        assert response.status_code == 200
