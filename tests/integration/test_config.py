"""
test_config.py — 配置加载集成测试。

注意：backend.config 是模块导入时即执行的代码，conftest.py 中的 builtins.open
重定向确保它读到 fake_credentials.json。此测试验证 monkeypatch 后的值。
"""
import pytest


class TestConfigValues:
    """验证 conftest fixture 注入后的配置值。"""

    def test_api_key_is_fake(self):
        from backend import config
        assert config.API_KEY == "sk-test-fake-key"

    def test_base_url_is_fake(self):
        from backend import config
        assert config.BASE_URL == "https://api.test.local"

    def test_model_is_test(self):
        from backend import config
        assert config.MODEL == "test-model"

    def test_debug_output_disabled(self):
        from backend import config
        assert config.ENABLE_DEBUG_OUTPUT is False

    def test_concurrency_defaults(self):
        from backend import config
        assert config.MAX_CONCURRENT_GENERATION_TASKS == 1
        assert config.MAX_CONCURRENT_EXPORT_TASKS == 1

    def test_access_passphrases(self):
        from backend import config
        assert config.ACCESS_PASSPHRASES == ["test123"]

    def test_duration_hints_present(self):
        from backend import config
        assert config.DURATION_SECONDS_HINT["preview"] == 12
        assert config.DURATION_SECONDS_HINT["short"] == 30
        assert config.DURATION_SECONDS_HINT["medium"] == 60
        assert config.DURATION_SECONDS_HINT["long"] == 90

    def test_share_expiration_keys(self):
        from backend import config
        assert "1h" in config.SHARE_EXPIRATION_SECONDS
        assert "1d" in config.SHARE_EXPIRATION_SECONDS
        assert "forever" in config.SHARE_EXPIRATION_SECONDS

    def test_video_expiration_keys(self):
        from backend import config
        assert "10m" in config.VIDEO_EXPIRATION_SECONDS
        assert "1d" in config.VIDEO_EXPIRATION_SECONDS

    def test_semaphores_created(self):
        from backend import config
        assert config.generation_semaphore is not None
        assert config.export_semaphore is not None

    def test_timezone_is_shanghai(self):
        from backend import config
        assert config.shanghai_tz is not None
        assert str(config.shanghai_tz) == "Asia/Shanghai"

    def test_storage_dirs_exist_in_paths(self):
        from backend import config
        assert "storage" in config.SHARE_STORAGE_DIR
        assert "storage" in config.VIDEO_STORAGE_DIR
