"""
helpers.py — 测试辅助工具。

提供 FakeChunk（模拟 LangChain 流式 token）、mock stream 生成器等。
"""
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class FakeChunk:
    """模拟 LangChain ChatOpenAI astream 产出的 AIMessageChunk。

    用法:
        chunks = [
            FakeChunk(content="Hello"),
            FakeChunk(content=" world"),
        ]
    """
    content: str = ""
    tool_calls: list = None
    additional_kwargs: dict = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.additional_kwargs is None:
            self.additional_kwargs = {}


class FakeAIMessage:
    """模拟 LangChain ainvoke 产出的 AIMessage。

    用法:
        msg = FakeAIMessage(content='{"segments": [...]}')
    """
    def __init__(self, content: str = "", tool_calls: list = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.additional_kwargs = {}


async def fake_async_stream(chunks: list):
    """生成一个 async generator，依次产出给定 chunks。

    用法:
        mock_llm.astream.return_value = fake_async_stream([
            FakeChunk(content="{"),
            FakeChunk(content='"segments"'),
            FakeChunk(content=":[]}"),
        ])
    """
    for chunk in chunks:
        yield chunk


def make_segments_json(segments: List[Dict[str, Any]]) -> str:
    """将 segments 列表序列化为 LLM 输出的 JSON 字符串。

    模拟 validate_segments 接收到的 segments_raw 字段格式。
    """
    import json
    return json.dumps({"segments": segments}, ensure_ascii=False)
