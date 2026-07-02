"""
test_video_exporter.py — VideoExporter 单元测试。
"""
import os
import pytest

from backend.video_exporter import VideoExporter, get_video_exporter


class TestHasHyperFramesMarkup:
    """has_hyperframes_markup 检测测试。"""

    def test_detects_data_composition_id(self):
        assert VideoExporter.has_hyperframes_markup(
            '<div data-composition-id="abc123">content</div>'
        ) is True

    def test_detects_case_insensitive(self):
        assert VideoExporter.has_hyperframes_markup(
            '<div DATA-COMPOSITION-ID="abc">content</div>'
        ) is True

    def test_no_hyperframes_returns_false(self):
        assert VideoExporter.has_hyperframes_markup(
            '<div>plain content</div>'
        ) is False

    def test_empty_html(self):
        assert VideoExporter.has_hyperframes_markup("") is False


class TestParseDuration:
    """parse_duration 解析测试。"""

    def test_parses_meta_tag(self):
        html = '<meta name="animation-duration" content="45.5">'
        assert VideoExporter.parse_duration(html) == 45.5

    def test_parses_single_quotes(self):
        html = "<meta name='animation-duration' content='30'>"
        assert VideoExporter.parse_duration(html) == 30.0

    def test_returns_default_when_missing(self):
        assert VideoExporter.parse_duration("<html></html>") == 30.0

    def test_returns_default_when_empty(self):
        assert VideoExporter.parse_duration("", default=60.0) == 60.0

    def test_case_insensitive(self):
        html = '<META NAME="ANIMATION-DURATION" CONTENT="90">'
        assert VideoExporter.parse_duration(html) == 90.0


class TestParseResolution:
    """parse_resolution 解析测试。"""

    def test_parses_data_attributes(self):
        html = '<div data-width="1280" data-height="720">'
        w, h = VideoExporter.parse_resolution(html)
        assert w == 1280
        assert h == 720

    def test_parses_viewport_width_height(self):
        html = '<meta name="viewport" content="width=1920, height=1080">'
        w, h = VideoExporter.parse_resolution(html)
        assert w == 1920
        assert h == 1080

    def test_returns_default_when_missing(self):
        w, h = VideoExporter.parse_resolution("<html></html>")
        assert w == 1920
        assert h == 1080


class TestGetVideoExporterSingleton:
    """get_video_exporter 单例测试。"""

    def test_returns_same_instance(self):
        e1 = get_video_exporter()
        e2 = get_video_exporter()
        assert e1 is e2

    def test_instance_has_storage_dirs(self):
        exporter = get_video_exporter()
        assert os.path.isdir(exporter.storage_dir)
        assert os.path.isdir(exporter.temp_dir)


class TestVideoExporterMetadata:
    """metadata 读写测试。"""

    def test_get_metadata_nonexistent(self, tmp_path):
        exporter = VideoExporter(storage_dir=str(tmp_path))
        assert exporter.get_metadata("nonexistent") is None

    def test_get_video_path_nonexistent(self, tmp_path):
        exporter = VideoExporter(storage_dir=str(tmp_path))
        assert exporter.get_video_path("nonexistent") is None


class TestCleanupExpired:
    """cleanup_expired 测试。"""

    def test_cleanup_removes_expired(self, tmp_path):
        import json, time
        from datetime import datetime, timezone, timedelta
        exporter = VideoExporter(storage_dir=str(tmp_path))

        # 创建一个"过期"视频的 metadata（带时区）
        old_time = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        meta = {
            "video_id": "test123",
            "width": 1920,
            "height": 1080,
            "fps": 24,
            "duration_seconds": 30,
            "created_at": old_time,
            "retention_seconds": 3600,
        }
        meta_path = os.path.join(str(tmp_path), "test123.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        exporter.cleanup_expired(default_max_age_seconds=3600)

        assert not os.path.exists(meta_path)
        assert exporter.get_metadata("test123") is None

    def test_cleanup_preserves_fresh(self, tmp_path):
        import json
        from datetime import datetime, timezone
        exporter = VideoExporter(storage_dir=str(tmp_path))

        now = datetime.now(timezone.utc)
        meta = {
            "video_id": "fresh",
            "width": 1920,
            "height": 1080,
            "fps": 24,
            "duration_seconds": 30,
            "created_at": now.isoformat(),
            "retention_seconds": 86400,  # 1 day
        }
        meta_path = os.path.join(str(tmp_path), "fresh.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        exporter.cleanup_expired(default_max_age_seconds=3600)

        assert os.path.exists(meta_path)


class TestDeleteVideo:
    """delete_video 测试。"""

    def test_delete_removes_both_files(self, tmp_path):
        exporter = VideoExporter(storage_dir=str(tmp_path))
        meta_path = os.path.join(str(tmp_path), "del.json")
        mp4_path = os.path.join(str(tmp_path), "del.mp4")

        with open(meta_path, "w") as f:
            f.write("{}")
        with open(mp4_path, "w") as f:
            f.write("fake mp4")

        exporter.delete_video("del")

        assert not os.path.exists(meta_path)
        assert not os.path.exists(mp4_path)

    def test_delete_nonexistent_is_safe(self, tmp_path):
        exporter = VideoExporter(storage_dir=str(tmp_path))
        exporter.delete_video("nonexistent")  # 不应抛出异常
