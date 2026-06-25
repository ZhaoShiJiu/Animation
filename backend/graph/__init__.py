"""
graph/__init__.py — ChatOpenAI 实例化。
"""

from langchain_openai import ChatOpenAI

from backend.config import API_KEY, BASE_URL, MODEL


def get_llm(temperature: float = 0.8) -> ChatOpenAI:
    """创建 ChatOpenAI 实例。

    所有 graph node 通过此函数获取 LLM，确保 streaming=True，
    token 才能通过 astream_events 冒泡到 SSE adapter。
    每次调用创建新实例以保证 temperature 等参数生效。
    """
    return ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=temperature,
        streaming=True,
    )
