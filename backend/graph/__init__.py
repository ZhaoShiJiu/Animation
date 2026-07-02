"""
graph/__init__.py — ChatOpenAI 实例化（带缓存）。
"""
from langchain_openai import ChatOpenAI

from backend.config import API_KEY, BASE_URL, MODEL

# LLM 实例缓存（按 temperature 键）
_llm_cache: dict[float, ChatOpenAI] = {}


def get_llm(temperature: float = 0.8) -> ChatOpenAI:
    """创建或获取缓存的 ChatOpenAI 实例。

    所有 graph node 通过此函数获取 LLM，确保 streaming=True，
    token 才能通过 astream_events 冒泡到 SSE adapter。
    缓存避免每次调用都创建新实例（节省连接建立开销）。
    """
    if temperature not in _llm_cache:
        _llm_cache[temperature] = ChatOpenAI(
            api_key=API_KEY,
            base_url=BASE_URL,
            model=MODEL,
            temperature=temperature,
            streaming=True,
        )
    return _llm_cache[temperature]


def clear_llm_cache():
    """清空 LLM 实例缓存（测试用）。"""
    _llm_cache.clear()
