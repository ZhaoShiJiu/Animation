"""
test_routing.py — LangGraph 条件路由逻辑测试。
"""
import pytest
from backend.graph.edges.routing import (
    after_validate_copy,
    after_validate_segments,
    _retry_left,
    TOKEN_PASSED,
    TOKEN_RETRY,
    TOKEN_ABORT,
)


# ═══════════════════════════════════════════════════════════════════════════
# _retry_left
# ═══════════════════════════════════════════════════════════════════════════

class TestRetryLeft:
    """剩余重试次数判断。"""

    def test_retry_available_when_below_max(self):
        state = {"retry_count": 1, "max_retries": 2}
        assert _retry_left(state) is True

    def test_retry_available_when_equal_max(self):
        state = {"retry_count": 2, "max_retries": 2}
        assert _retry_left(state) is True

    def test_retry_exhausted(self):
        state = {"retry_count": 3, "max_retries": 2}
        assert _retry_left(state) is False

    def test_default_max_retries(self):
        """不提供 max_retries 时默认 2。"""
        state = {"retry_count": 0}
        assert _retry_left(state) is True

    def test_retry_count_missing_defaults_zero(self):
        """不提供 retry_count 时默认 0。"""
        state = {"max_retries": 2}
        assert _retry_left(state) is True


# ═══════════════════════════════════════════════════════════════════════════
# after_validate_copy
# ═══════════════════════════════════════════════════════════════════════════

class TestAfterValidateCopy:
    """文案校验路由测试。"""

    def test_pass_when_copy_valid(self):
        state = {"copy_valid": True}
        assert after_validate_copy(state) == TOKEN_PASSED

    def test_retry_when_invalid_and_retries_left(self):
        state = {"copy_valid": False, "retry_count": 1, "max_retries": 2}
        assert after_validate_copy(state) == TOKEN_RETRY

    def test_abort_when_invalid_and_retries_exhausted(self):
        state = {"copy_valid": False, "retry_count": 3, "max_retries": 2}
        assert after_validate_copy(state) == TOKEN_ABORT

    def test_first_attempt_copy_invalid(self):
        """第一次尝试（retry_count=0）文案无效——可以重试。"""
        state = {"copy_valid": False, "retry_count": 0, "max_retries": 2}
        assert after_validate_copy(state) == TOKEN_RETRY

    def test_copy_valid_overrides_retry_count(self):
        """文案有效时，即使 retry_count 超标也 pass。"""
        state = {"copy_valid": True, "retry_count": 5, "max_retries": 2}
        assert after_validate_copy(state) == TOKEN_PASSED


# ═══════════════════════════════════════════════════════════════════════════
# after_validate_segments
# ═══════════════════════════════════════════════════════════════════════════

class TestAfterValidateSegments:
    """Segments 校验路由测试。"""

    def test_pass_when_segments_valid(self):
        state = {"segments_valid": True}
        assert after_validate_segments(state) == TOKEN_PASSED

    def test_retry_when_invalid_and_retries_left(self):
        state = {"segments_valid": False, "retry_count": 1, "max_retries": 2}
        assert after_validate_segments(state) == TOKEN_RETRY

    def test_abort_when_invalid_and_retries_exhausted(self):
        state = {"segments_valid": False, "retry_count": 3, "max_retries": 2}
        assert after_validate_segments(state) == TOKEN_ABORT

    def test_first_attempt_segments_invalid(self):
        """第一次尝试 segments 无效——可以重试。"""
        state = {"segments_valid": False, "retry_count": 0, "max_retries": 2}
        assert after_validate_segments(state) == TOKEN_RETRY

    def test_segments_valid_overrides_retry_count(self):
        """Segments 有效时，即使 retry_count 超标也 pass。"""
        state = {"segments_valid": True, "retry_count": 5, "max_retries": 2}
        assert after_validate_segments(state) == TOKEN_PASSED


# ═══════════════════════════════════════════════════════════════════════════
# 令牌常量
# ═══════════════════════════════════════════════════════════════════════════

class TestTokens:
    """确保路由令牌常量值不变（防止意外修改破坏图边映射）。"""

    def test_token_values(self):
        assert TOKEN_PASSED == "passed"
        assert TOKEN_RETRY == "retry"
        assert TOKEN_ABORT == "abort"
