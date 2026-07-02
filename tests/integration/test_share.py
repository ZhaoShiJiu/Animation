"""
test_share.py — 分享链接 CRUD 集成测试。
"""
import os
import json
import pytest
from datetime import datetime, timedelta

from backend.config import shanghai_tz, SHARE_STORAGE_DIR, shared_html_links
from backend.share import (
    get_share_paths,
    serialize_share_record,
    parse_share_datetime,
    save_share_to_disk,
    load_share_from_disk,
    delete_share,
    get_share_record,
    cleanup_expired_shares_once,
    create_qr_data_url,
    build_share_access_page,
    build_shared_viewer_page,
)


class TestSharePaths:
    """路径生成测试。"""

    def test_get_share_paths(self):
        paths = get_share_paths("abc123")
        assert paths["meta"].endswith("abc123.json")
        assert paths["html"].endswith("abc123.html")
        assert SHARE_STORAGE_DIR in paths["meta"]


class TestSerializeDeserialize:
    """序列化/反序列化测试。"""

    def test_serialize_share_record(self):
        now = datetime.now(shanghai_tz)
        record = {
            "password": "123456",
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
        serialized = serialize_share_record(record)
        assert serialized["password"] == "123456"
        assert "T" in serialized["created_at"]  # ISO format

    def test_parse_share_datetime_naive(self):
        """无时区的 datetime 字符串应本地化为上海时区。"""
        parsed = parse_share_datetime("2025-01-01T12:00:00")
        assert parsed.tzinfo is not None

    def test_parse_share_datetime_with_tz(self):
        """带时区的 datetime 字符串应转为上海时区。"""
        parsed = parse_share_datetime("2025-01-01T12:00:00+00:00")
        assert parsed.tzinfo is not None


class TestShareCRUD:
    """分享 CRUD 集成测试（使用 tmp_path）。"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, monkeypatch, tmp_path):
        """重定向存储路径到临时目录。"""
        test_dir = str(tmp_path / "shared_html")
        monkeypatch.setattr("backend.share.SHARE_STORAGE_DIR", test_dir)
        monkeypatch.setattr("backend.config.SHARE_STORAGE_DIR", test_dir)
        # 清空内存缓存
        shared_html_links.clear()
        yield
        shared_html_links.clear()

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """保存后能正确加载。"""
        now = datetime.now(shanghai_tz)
        record = {
            "html": "<div>test animation</div>",
            "password": "abcd1234",
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
        await save_share_to_disk("test001", record)
        loaded = await load_share_from_disk("test001")

        assert loaded is not None
        assert loaded["html"] == record["html"]
        assert loaded["password"] == record["password"]

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(self):
        """不存在的分享返回 None。"""
        assert await load_share_from_disk("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete_share(self):
        """删除分享应同时清理内存和磁盘。"""
        now = datetime.now(shanghai_tz)
        record = {
            "html": "<div>delete me</div>",
            "password": "123456",
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
        await save_share_to_disk("to_delete", record)
        shared_html_links["to_delete"] = record

        await delete_share("to_delete")
        assert "to_delete" not in shared_html_links
        assert await load_share_from_disk("to_delete") is None

    @pytest.mark.asyncio
    async def test_get_share_record_in_memory(self):
        """从内存缓存获取分享。"""
        now = datetime.now(shanghai_tz)
        record = {
            "html": "<div>cached</div>",
            "password": "0000",
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
        shared_html_links["cache_test"] = record
        result = await get_share_record("cache_test")
        assert result is not None
        assert result["html"] == "<div>cached</div>"

    @pytest.mark.asyncio
    async def test_get_share_record_expired(self):
        """过期分享应被删除并返回 None。"""
        now = datetime.now(shanghai_tz)
        record = {
            "html": "<div>expired</div>",
            "password": "0000",
            "created_at": now - timedelta(hours=2),
            "expires_at": now - timedelta(hours=1),  # 1小时前过期
        }
        shared_html_links["expired_test"] = record
        result = await get_share_record("expired_test")
        assert result is None
        assert "expired_test" not in shared_html_links

    @pytest.mark.asyncio
    async def test_get_share_record_no_expiry(self):
        """无过期时间的分享永久有效。"""
        now = datetime.now(shanghai_tz)
        record = {
            "html": "<div>forever</div>",
            "password": "0000",
            "created_at": now,
            "expires_at": None,
        }
        shared_html_links["forever_test"] = record
        result = await get_share_record("forever_test")
        assert result is not None

    @pytest.mark.asyncio
    async def test_cleanup_expired_shares(self):
        """清理任务应删除过期分享。"""
        now = datetime.now(shanghai_tz)
        expired = {
            "html": "<div>expired</div>",
            "password": "0000",
            "created_at": now - timedelta(hours=3),
            "expires_at": now - timedelta(hours=1),
        }
        valid = {
            "html": "<div>valid</div>",
            "password": "0000",
            "created_at": now,
            "expires_at": now + timedelta(hours=1),
        }
        shared_html_links["exp"] = expired
        shared_html_links["val"] = valid

        await cleanup_expired_shares_once()

        assert "exp" not in shared_html_links
        assert "val" in shared_html_links


class TestPageBuilders:
    """页面构建函数测试。"""

    def test_build_share_access_page_no_error(self):
        page = build_share_access_page()
        assert "请输入访问密码" in page
        # 无错误时不应包含 error_message 段落
        assert '<p class="error">' not in page

    def test_build_share_access_page_with_error(self):
        page = build_share_access_page("密码错误")
        assert "密码错误" in page
        assert "error" in page

    def test_build_shared_viewer_page(self):
        page = build_shared_viewer_page("<div>animation</div>", 1920, 1080)
        assert "animation" in page
        assert "iframe" in page

    def test_create_qr_data_url(self):
        qr = create_qr_data_url("https://example.com")
        assert qr.startswith("data:image/png;base64,")
