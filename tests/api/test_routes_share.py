"""
test_routes_share.py — 分享相关路由测试。
"""
import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI TestClient。"""
    from app import app
    return TestClient(app)


class TestCreateShareRoute:
    """POST /share 测试。"""

    def test_valid_share_request_returns_url(self, client):
        response = client.post("/share", json={
            "html": "<div>test animation content</div>",
            "expiresIn": "1h",
            "password": "123456",
        })
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "qrCode" in data
        assert "password" in data
        assert data["password"] == "123456"

    def test_missing_html_returns_400(self, client):
        """缺少 html 应返回 400。"""
        response = client.post("/share", json={
            "html": "",
            "expiresIn": "1h",
            "password": "123456",
        })
        assert response.status_code == 400

    def test_invalid_expiration_returns_400(self, client):
        """无效过期时间应返回 400。"""
        response = client.post("/share", json={
            "html": "<div>test</div>",
            "expiresIn": "2h",  # 不在允许列表中
            "password": "123456",
        })
        assert response.status_code == 400

    def test_password_too_short_returns_422(self, client):
        """密码过短应返回 422（Pydantic 校验）。"""
        response = client.post("/share", json={
            "html": "<div>test</div>",
            "expiresIn": "1h",
            "password": "12",  # 少于 4 位
        })
        assert response.status_code == 422

    def test_forever_expiration(self, client):
        """永久有效的分享。"""
        response = client.post("/share", json={
            "html": "<div>forever</div>",
            "expiresIn": "forever",
            "password": "999999",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["expiresAt"] is None


class TestReadShareRoute:
    """GET /share/{share_id} 测试。"""

    def test_nonexistent_share_returns_404(self, client):
        response = client.get("/share/nonexistent_id_12345")
        assert response.status_code == 404

    def test_newly_created_share_shows_password_page(self, client):
        """新建的有密码分享应展示密码输入页。"""
        create_resp = client.post("/share", json={
            "html": "<div>protected</div>",
            "expiresIn": "1h",
            "password": "999999",
        })
        share_url = create_resp.json()["url"]
        share_id = share_url.rsplit("/", 1)[-1]

        response = client.get(f"/share/{share_id}")
        assert response.status_code == 200
        assert "请输入访问密码" in response.text


class TestVerifyShareRoute:
    """POST /share/{share_id} 测试。"""

    def test_verify_correct_password(self, client):
        """正确密码应返回动画页面。"""
        create_resp = client.post("/share", json={
            "html": "<div>protected content</div>",
            "expiresIn": "1h",
            # ShareRequest.password 只接受纯数字 4-20 位
            "password": "12345678",
        })
        share_id = create_resp.json()["url"].rsplit("/", 1)[-1]

        response = client.post(
            f"/share/{share_id}",
            data={"password": "12345678"},
        )
        assert response.status_code == 200
        assert "protected content" in response.text

    def test_verify_wrong_password_returns_403(self, client):
        """错误密码应返回 403。"""
        create_resp = client.post("/share", json={
            "html": "<div>secret</div>",
            "expiresIn": "1h",
            # ShareRequest.password 只接受纯数字 4-20 位
            "password": "111111",
        })
        share_id = create_resp.json()["url"].rsplit("/", 1)[-1]

        response = client.post(
            f"/share/{share_id}",
            data={"password": "222222"},
        )
        assert response.status_code == 403
        assert "访问密码错误" in response.text

    def test_nonexistent_share_verify_returns_404(self, client):
        response = client.post(
            "/share/nonexistent_xyz",
            data={"password": "123456"},
        )
        assert response.status_code == 404
