"""
test_thought_filter.py — ThoughtProcessFilter 纯算法测试。

注意：ThoughtProcessFilter 为流式 token 设计，feed() 会保留尾部若干字符
在缓冲区（防止标签跨 chunk 被截断）。批量喂入完整文本后需调用 flush() 获取剩余内容。
本测试文件使用 feed_and_flush() 辅助函数统一处理此模式。
"""
import pytest
from backend.thought_filter import ThoughtProcessFilter


def feed_and_flush(f: ThoughtProcessFilter, text: str) -> str:
    """喂入文本并返回完整可见输出（feed 结果 + flush 结果）。"""
    return f.feed(text) + f.flush()


class TestThoughtProcessFilter:
    """ThoughtProcessFilter 核心功能测试。"""

    # ── 基础功能 ──

    def test_no_think_tags_passthrough(self):
        """无 think 标签的文本应原样输出。"""
        f = ThoughtProcessFilter()
        assert feed_and_flush(f, "Hello world") == "Hello world"

    def test_empty_input(self):
        """空输入返回空字符串。"""
        f = ThoughtProcessFilter()
        assert f.feed("") == ""
        assert f.flush() == ""

    def test_feed_empty_then_content(self):
        """先喂空再喂内容——空不应影响后续。"""
        f = ThoughtProcessFilter()
        f.feed("")
        result = feed_and_flush(f, "normal text")
        assert result == "normal text"

    # ── 思考标签剥离 ──

    def test_strip_think_tag_basic(self):
        """基础 <think>...</think> 剥离。"""
        f = ThoughtProcessFilter()
        assert feed_and_flush(f, "<think>hidden</think>visible") == "visible"

    def test_strip_thinking_tag(self):
        """剥离 <thinking>...</thinking> 标签。"""
        f = ThoughtProcessFilter()
        assert feed_and_flush(f, "<thinking>internal</thinking>output") == "output"

    def test_strip_reasoning_tag(self):
        """剥离 <reasoning>...</reasoning> 标签。"""
        f = ThoughtProcessFilter()
        assert feed_and_flush(f, "<reasoning>logic</reasoning>result") == "result"

    def test_strip_chinese_think_prefix(self):
        """剥离"思考过程："中文前缀。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "思考过程：一些内部推理最终答案：实际可见内容")
        assert result == "实际可见内容"

    def test_strip_chinese_answer_prefix(self):
        """剥离"答案："中文前缀。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "思考过程：内部推理答案：可见结果")
        assert result == "可见结果"

    # ── 流式分片处理 ──

    def test_streaming_chunks(self):
        """模拟流式接收：标签跨多个 chunk 时仍正确剥离。"""
        f = ThoughtProcessFilter()
        r1 = f.feed("<thin")
        r2 = f.feed("k>")
        r3 = f.feed("hidden")
        r4 = f.feed("</think>")
        r5 = f.feed("visible")
        r6 = f.flush()

        combined = r1 + r2 + r3 + r4 + r5 + r6
        assert "visible" in combined
        assert "hidden" not in combined

    def test_streaming_start_marker_split(self):
        """开始标签跨两个 chunk。"""
        f = ThoughtProcessFilter()
        r1 = f.feed("<thi")
        r2 = f.feed("nk>hidden</think>visible")
        combined = r1 + r2 + f.flush()
        assert "visible" in combined
        assert "hidden" not in combined

    def test_streaming_end_marker_split(self):
        """两个 think 块分两个 chunk 到达，中间夹 visible。"""
        f = ThoughtProcessFilter()
        r1 = f.feed("<think>hidden1</think>keep1")
        r2 = f.feed("<think>hidden2</think>keep2")
        combined = r1 + r2 + f.flush()
        assert "keep1" in combined
        assert "keep2" in combined
        assert "hidden1" not in combined
        assert "hidden2" not in combined

    # ── 多个思考块 ──

    def test_multiple_think_blocks(self):
        """多个思考标签块都应被剥离。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "<think>a</think>keep1<think>b</think>keep2")
        assert result == "keep1keep2"

    def test_consecutive_think_tags(self):
        """连续的思考标签块。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "<think>a</think><think>b</think>keep")
        assert result == "keep"

    # ── flush 行为 ──

    def test_flush_in_thought_discards(self):
        """flush 时如果仍在思考中，丢弃缓冲区。"""
        f = ThoughtProcessFilter()
        f.feed("<think>unfinished")
        result = f.flush()
        assert result == ""

    def test_flush_out_of_thought_returns_buffer(self):
        """flush 时不在思考中，返回缓冲内容。"""
        f = ThoughtProcessFilter()
        f.feed("ab")
        flushed = f.flush()
        assert flushed == "ab"

    # ── 边界情况 ──

    def test_only_think_tag(self):
        """整个输入都在思考标签内——返回空。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "<think>everything is hidden</think>")
        assert result == ""

    def test_text_before_think(self):
        """思考标签前有可见文本。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "before<think>hidden</think>after")
        assert result == "beforeafter"

    def test_case_insensitive(self):
        """标签匹配应大小写不敏感。"""
        f = ThoughtProcessFilter()
        result = feed_and_flush(f, "<THINK>hidden</THINK>visible")
        assert result == "visible"

    def test_partial_start_tag_not_triggered(self):
        """内容包含类似但不完整的标签不应误触发。"""
        f = ThoughtProcessFilter()
        result = f.feed("<thin something")
        flushed = f.flush()
        combined = result + flushed
        assert combined == "<thin something"

    def test_mixed_content_no_tags(self):
        """混合内容但无任何标签——应原样输出。"""
        f = ThoughtProcessFilter()
        text = "普通的中文文本和 English text 123 !@#"
        result = feed_and_flush(f, text)
        assert result == text

    # ── 重用 ──

    def test_filter_reuse(self):
        """同一个过滤器实例可以多次使用。"""
        f = ThoughtProcessFilter()
        assert feed_and_flush(f, "<think>a</think>out1") == "out1"
        assert feed_and_flush(f, "<thinking>b</thinking>out2") == "out2"

    def test_filter_reuse_after_flush(self):
        """flush 后过滤器可继续使用。"""
        f = ThoughtProcessFilter()
        feed_and_flush(f, "<think>a</think>out1")
        result = feed_and_flush(f, "out2")
        assert result == "out2"
