"""
test_graph_e2e.py — LangGraph 端到端测试（mock LLM 响应）。

验证整张图从输入到 HTML 输出的完整流程。
"""
import json
import pytest

from backend.graph.state import AnimationState
from backend.graph.graphs.paper_graph import build_paper_graph
from backend.graph.graphs.three_stage_graph import build_three_stage_graph
from tests.helpers import FakeAIMessage, FakeChunk, fake_async_stream


# ── 测试数据 ──

VALID_TOPIC_OUTLINE = {
    "category": "物理",
    "difficulty": "中级",
    "core_idea": "测试核心概念",
    "visual_metaphors": ["比喻1", "比喻2"],
    "key_terms": ["术语1"],
    "narrative_angle": "反常识切入",
    "target_audience": "普通观众",
}

VALID_PAPER_OUTLINE = {
    "category": "计算机",
    "difficulty": "专业",
    "core_idea": "论文核心贡献",
    "visual_metaphors": ["比喻"],
    "key_terms": ["术语"],
    "narrative_angle": "好奇心驱动",
    "paper_summary": "这是一篇关于测试的论文摘要。",
    "method_highlights": ["方法1"],
    "key_result": "关键结果",
}

VALID_SEGMENTS_JSON = json.dumps({
    "segments": [
        {"title": "认知爆破", "titleColor": "#DC2626", "subZh": "开篇", "body": "补充"},
        {"title": "延迟满足", "titleColor": "#7C3AED", "subZh": "悬念",
         "visualSVG": "<svg viewBox='0 0 120 120'><circle cx='60' cy='60' r='40'/></svg>"},
        {"title": "层层揭秘", "titleColor": "#2563EB", "subZh": "揭示",
         "steps": ["步骤1", "步骤2", "步骤3"]},
        {"title": "高潮揭晓", "titleColor": "#059669", "subZh": "揭晓",
         "compareBefore": "旧认知", "compareAfter": "新认知"},
        {"title": "记忆钉", "titleColor": "#D97706", "subZh": "收尾", "bigNum": "42"},
    ]
})

VALID_NARRATIVE_JSON = {
    "narrative_type": "problem_conflict",
    "title": "测试标题",
    "total_duration_hint": 60,
    "acts": [
        {"act": 1, "name": "认知爆破", "goal": "抓住注意力", "duration_hint": 8,
         "method_used": "反常识", "narration": "旁白不超过三十五字",
         "narration_en": "English", "on_screen_text": "大字", "emotion": "震惊"},
        {"act": 2, "name": "延迟满足", "goal": "制造疑问", "duration_hint": 10,
         "method_used": "悬疑", "narration": "第二幕旁白短句",
         "narration_en": "Act two", "on_screen_text": "悬念大字", "emotion": "好奇"},
        {"act": 3, "name": "层层揭秘", "goal": "逐步解锁", "duration_hint": 20,
         "method_used": "一问一答", "narration": "第三幕逐步揭示",
         "narration_en": "Act three", "on_screen_text": "揭秘大字", "emotion": "理解"},
        {"act": 4, "name": "高潮揭晓", "goal": "颠覆认知", "duration_hint": 12,
         "method_used": "放大对比", "narration": "第四幕核心原理揭示",
         "narration_en": "Act four", "on_screen_text": "揭晓大字", "emotion": "顿悟"},
        {"act": 5, "name": "记忆钉", "goal": "传播点", "duration_hint": 10,
         "method_used": "金句总结", "narration": "第五幕一句话收尾",
         "narration_en": "Act five", "on_screen_text": "金句大字", "emotion": "满足"},
    ],
}

VALID_DIRECTION_JSON = {
    "visual_style": "cinematic",
    "color_palette_flow": "红→紫→蓝→绿→金",
    "acts": [
        {"act": 1, "composition": "中央", "main_element": "大号数字", "easing": "back.out(1.7)",
         "entrance_direction": "下方弹入", "entrance_duration_range": "0.4s", "camera_movement": "推近",
         "visual_technique": "过冲回弹", "primary_color": "#DC2626", "bg_color": "#1a1a2e"},
        {"act": 2, "act": 2, "composition": "居中", "main_element": "问号", "easing": "power2.inOut",
         "entrance_direction": "透明度渐变", "entrance_duration_range": "1.2s", "camera_movement": "固定",
         "visual_technique": "模糊到清晰", "primary_color": "#7C3AED", "bg_color": "#FAFBFC"},
        {"act": 3, "composition": "左侧列表", "main_element": "步骤卡片", "easing": "power3.out",
         "entrance_direction": "左侧滑入", "entrance_duration_range": "0.6s", "camera_movement": "微平移",
         "visual_technique": "逐条递进", "primary_color": "#2563EB", "bg_color": "#FAFBFC"},
        {"act": 4, "composition": "左右对比", "main_element": "对比面板", "easing": "power4.out",
         "entrance_direction": "缩放", "entrance_duration_range": "0.8s", "camera_movement": "推近",
         "visual_technique": "旧淡出新放大", "primary_color": "#059669", "bg_color": "#FAFBFC"},
        {"act": 5, "composition": "居中", "main_element": "金句大字", "easing": "power4.out",
         "entrance_direction": "缩放+上浮", "entrance_duration_range": "1.5s", "camera_movement": "拉远",
         "visual_technique": "优雅定格", "primary_color": "#D97706", "bg_color": "#FAFBFC"},
    ],
}


# ── paper_graph E2E ──

class TestPaperGraphE2E:
    """paper_graph 端到端测试。"""

    async def test_paper_graph_full_pipeline(self, mock_llm, mocker):
        """论文全流程：analyze_paper → generate_segments → validate → assemble → postprocess"""
        graph = build_paper_graph()

        mock_llm.ainvoke.return_value = FakeAIMessage(
            content=json.dumps(VALID_PAPER_OUTLINE, ensure_ascii=False)
        )
        mock_llm.astream.return_value = fake_async_stream([
            FakeChunk(content=VALID_SEGMENTS_JSON),
        ])

        mocker.patch(
            "backend.graph.nodes.postprocess.postprocess_html",
            return_value="<html>PAPER_OK</html>",
        )

        result = await graph.ainvoke(AnimationState(
            topic="论文", pdf_filename="test.pdf",
            pdf_text="论文完整文本内容。", pdf_truncated=False,
            focus="", settings={}, retry_count=0, max_retries=2,
        ))
        assert "html" in result


# ── three_stage_graph E2E ──

class TestThreeStageGraphE2E:
    """three_stage_graph 端到端测试。"""

    async def test_three_stage_full_pipeline(self, mock_llm, mocker):
        """三阶段全流程：analyze → narrative → validate → direction → validate → animation → validate → assemble"""
        graph = build_three_stage_graph()

        # analyze_topic 用 ainvoke
        mock_llm.ainvoke.return_value = FakeAIMessage(
            content=json.dumps(VALID_TOPIC_OUTLINE, ensure_ascii=False)
        )

        # 三个流式节点各返回对应 JSON
        mock_llm.astream.side_effect = [
            fake_async_stream([FakeChunk(content=json.dumps(VALID_NARRATIVE_JSON))]),
            fake_async_stream([FakeChunk(content=json.dumps(VALID_DIRECTION_JSON))]),
            fake_async_stream([FakeChunk(content=VALID_SEGMENTS_JSON)]),
        ]

        mocker.patch(
            "backend.graph.nodes.postprocess.postprocess_html",
            return_value="<html>THREE_STAGE_OK</html>",
        )

        result = await graph.ainvoke(AnimationState(
            topic="三阶段测试", settings={}, retry_count=0, max_retries=2,
        ))
        assert "html" in result
        assert result.get("narrative_valid") is True
        assert result.get("direction_valid") is True
        assert result.get("segments_valid") is True

    async def test_three_stage_narrative_retry(self, mock_llm, mocker):
        """文案校验失败重试。"""
        graph = build_three_stage_graph()

        mock_llm.ainvoke.return_value = FakeAIMessage(
            content=json.dumps(VALID_TOPIC_OUTLINE, ensure_ascii=False)
        )

        # 第一次文案失败（缺少 title），第二次通过
        bad_narrative = {**VALID_NARRATIVE_JSON, "title": ""}
        mock_llm.astream.side_effect = [
            fake_async_stream([FakeChunk(content=json.dumps(bad_narrative))]),
            fake_async_stream([FakeChunk(content=json.dumps(VALID_NARRATIVE_JSON))]),
            fake_async_stream([FakeChunk(content=json.dumps(VALID_DIRECTION_JSON))]),
            fake_async_stream([FakeChunk(content=VALID_SEGMENTS_JSON)]),
        ]

        mocker.patch(
            "backend.graph.nodes.postprocess.postprocess_html",
            return_value="<html>NARRATIVE_RETRY_OK</html>",
        )

        result = await graph.ainvoke(AnimationState(
            topic="测试", settings={}, retry_count=0, max_retries=2,
        ))
        assert "html" in result

    async def test_three_stage_animation_retry(self, mock_llm, mocker):
        """动画校验失败重试（前两个阶段正常）。"""
        graph = build_three_stage_graph()

        mock_llm.ainvoke.return_value = FakeAIMessage(
            content=json.dumps(VALID_TOPIC_OUTLINE, ensure_ascii=False)
        )

        bad_segments = json.dumps({"segments": [{"title": "a", "subZh": "b"}]})
        mock_llm.astream.side_effect = [
            fake_async_stream([FakeChunk(content=json.dumps(VALID_NARRATIVE_JSON))]),
            fake_async_stream([FakeChunk(content=json.dumps(VALID_DIRECTION_JSON))]),
            fake_async_stream([FakeChunk(content=bad_segments)]),
            fake_async_stream([FakeChunk(content=VALID_SEGMENTS_JSON)]),
        ]

        mocker.patch(
            "backend.graph.nodes.postprocess.postprocess_html",
            return_value="<html>ANIM_RETRY_OK</html>",
        )

        result = await graph.ainvoke(AnimationState(
            topic="测试", settings={}, retry_count=0, max_retries=2,
        ))
        assert "html" in result
