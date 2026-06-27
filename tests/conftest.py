"""
conftest.py — 全局测试 fixtures。

关键设计：在 import 任何项目模块之前，拦截 credentials.json 的读取，
自动重定向到 tests/fake_credentials.json。这样 backend.config 的模块级
open() 调用不会因缺少真实凭证而失败，无需手动复制文件。
"""
import builtins
import os

# ═══════════════════════════════════════════════════════════════════════════
# 模块级（pytest 加载 conftest 时立即执行，早于所有测试和项目 import）
# ═══════════════════════════════════════════════════════════════════════════

_original_open = builtins.open


def _patched_open(file, mode="r", *args, **kwargs):
    """当尝试打开不存在的 credentials.json 时，重定向到测试用假凭证。"""
    if isinstance(file, str) and os.path.basename(file) == "credentials.json":
        if not os.path.exists(file):
            fake = os.path.join(os.path.dirname(__file__), "fake_credentials.json")
            if os.path.exists(fake):
                return _original_open(fake, mode, *args, **kwargs)
    return _original_open(file, mode, *args, **kwargs)


builtins.open = _patched_open

# ═══════════════════════════════════════════════════════════════════════════
# 常规 imports（现在安全了——backend.config 会自动读到假凭证）
# ═══════════════════════════════════════════════════════════════════════════

import pytest
from unittest.mock import AsyncMock, MagicMock


# ── Fixtures ──


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    """所有测试自动注入假配置，确保不依赖真实的 credentials.json 值。"""
    monkeypatch.setattr("backend.config.API_KEY", "sk-test-fake-key")
    monkeypatch.setattr("backend.config.BASE_URL", "https://api.test.local")
    monkeypatch.setattr("backend.config.MODEL", "test-model")
    monkeypatch.setattr("backend.config.ENABLE_DEBUG_OUTPUT", False)
    monkeypatch.setattr("backend.config.MAX_CONCURRENT_GENERATION_TASKS", 1)
    monkeypatch.setattr("backend.config.MAX_CONCURRENT_EXPORT_TASKS", 1)
    monkeypatch.setattr("backend.config.ACCESS_PASSPHRASES", ["test123"])


@pytest.fixture
def mock_llm(mocker):
    """Mock backend.graph.get_llm() 返回 AsyncMock。

    使用方式：
        llm = mock_llm()
        llm.ainvoke.return_value = FakeAIMessage(content="...")
        llm.astream.return_value = fake_async_stream([...])
    """
    mock_instance = AsyncMock()
    mock_get = mocker.patch("backend.graph.get_llm")
    mock_get.return_value = mock_instance
    return mock_instance


@pytest.fixture
def sample_segments():
    """返回 5 段合法的 AnimationSegment 数据，供 assemble / validate 测试复用。"""
    return [
        {
            "title": "认知爆破",
            "titleColor": "#DC2626",
            "subZh": "这是一个引人注目的开篇",
            "subEn": "This is a striking opening",
            "body": "开篇补充说明",
        },
        {
            "title": "延迟满足",
            "titleColor": "#7C3AED",
            "subZh": "制造悬念的第二幕",
            "subEn": "Building suspense in act two",
            "visualSVG": "<svg viewBox='0 0 120 120'><circle cx='60' cy='60' r='40' fill='currentColor'/></svg>",
        },
        {
            "title": "层层揭秘",
            "titleColor": "#2563EB",
            "subZh": "逐步揭示信息阶梯",
            "subEn": "Step by step revelation",
            "steps": ["第一步：发现问题", "第二步：分析原因", "第三步：找到答案"],
        },
        {
            "title": "高潮揭晓",
            "titleColor": "#059669",
            "subZh": "产生恍然大悟的时刻",
            "subEn": "The aha moment",
            "compareBefore": "旧的错误认知",
            "compareAfter": "新的正确理解",
            "compareLabelBefore": "以前以为",
            "compareLabelAfter": "其实是",
        },
        {
            "title": "记忆钉",
            "titleColor": "#D97706",
            "subZh": "一句话总结留下传播点",
            "subEn": "A memorable takeaway",
            "bigNum": "42",
        },
    ]


@pytest.fixture
def sample_html():
    """返回一个最小合法的动画 HTML，供 postprocessor 测试复用。"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>Test Animation</title>
    <style>
        body { margin: 0; font-family: sans-serif; }
    </style>
</head>
<body>
    <div id="scene-0">
        <h1 class="entrance-el">测试标题</h1>
        <p>测试内容</p>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script>
        var tl = gsap.timeline();
        tl.fromTo("#scene-0 .entrance-el",
            { y: 60, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.8 }
        );
    </script>
</body>
</html>"""


@pytest.fixture
def sample_copy_json():
    """返回一个合法的 CopySchema 测试数据。"""
    return {
        "narrative_type": "problem_conflict",
        "title": "测试动画标题",
        "visual_style": "cinematic",
        "color_palette": "红→紫→蓝→绿→金",
        "total_duration_hint": 60,
        "acts": [
            {
                "act": 1,
                "name": "认知爆破",
                "goal": "3秒抓住注意力",
                "duration_hint": 8,
                "method_used": "反常识",
                "narration": "这是一个测试旁白文案不超过三十五字",
                "narration_en": "This is a test narration",
                "visual_description": "画面中央大号问号，冷紫色背景，文字从下方弹入",
                "on_screen_text": "震撼大字",
            },
            {
                "act": 2,
                "name": "延迟满足",
                "goal": "制造疑问",
                "duration_hint": 10,
                "method_used": "强化错误认知",
                "narration": "第二幕旁白文案不超过三十五字限制",
                "narration_en": "Act two narration",
                "visual_description": "文字从模糊到清晰，偏冷灰紫色调",
                "on_screen_text": "到底怎么回事",
            },
            {
                "act": 3,
                "name": "层层揭秘",
                "goal": "逐步解锁",
                "duration_hint": 20,
                "method_used": "一问一答",
                "narration": "第三幕旁白逐一解释每个层面",
                "narration_en": "Act three step by step",
                "visual_description": "逐条滑入，清爽蓝白色调",
                "on_screen_text": "原来是这样",
            },
            {
                "act": 4,
                "name": "高潮揭晓",
                "goal": "颠覆认知",
                "duration_hint": 12,
                "method_used": "放大对比",
                "narration": "第四幕揭示核心原理让人恍然大悟",
                "narration_en": "The big reveal",
                "visual_description": "核心概念放大加外发光，旧认知淡出",
                "on_screen_text": "原来如此",
            },
            {
                "act": 5,
                "name": "记忆钉",
                "goal": "留下传播点",
                "duration_hint": 10,
                "method_used": "金句总结",
                "narration": "第五幕一句话总结让人印象深刻",
                "narration_en": "Memorable takeaway",
                "visual_description": "文字居中放大，暖金色调，优雅定格",
                "on_screen_text": "记住这一句",
            },
        ],
    }
