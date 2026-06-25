"""
sse_adapter.py — 将 LangGraph astream_events() 转换为现有 SSE 协议。

v2: 由于 LangGraph astream_events v2 无法捕获节点内部 llm.astream() 的
on_chat_model_stream 事件，改用 asyncio.Queue 旁路传递 token：
- stream_graph_to_sse 创建 StreamContext（含 asyncio.Queue）
- 节点通过 get_stream_context().push_token() 推送 token
- 主循环同时消费 graph events 和节点 token，合并为 SSE 输出
"""
import asyncio
import contextvars
import json
import logging
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger(__name__)

# 需要向前端流式输出 token 的节点名
_STREAMING_NODES = {"generate_segments", "generate_copy", "generate_animation"}

# 所有图中的业务节点名（用于过滤掉内部链如 ChatOpenAI、RunnableSequence 等）
_GRAPH_NODES = {
    "analyze_topic", "analyze_paper",
    "generate_copy", "generate_segments", "generate_animation",
    "validate_copy", "validate_segments", "validate_animation",
    "assemble", "postprocess",
}

# ── 流式上下文（ContextVar，每个请求独立） ──

class StreamContext:
    """节点与 SSE adapter 之间的 token 传输通道。"""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        # 标记：图是否已结束（不再有新 event/token）
        self._done = False

    def push_token(self, token: str):
        """节点调用此方法推送一个 token 到 SSE 流。"""
        if token and not self._done:
            self.queue.put_nowait(("token", token))

    def push_event(self, event: dict):
        """graph producer 推送 astream_events 事件。"""
        if not self._done:
            self.queue.put_nowait(("event", event))

    def push_error(self, error_msg: str):
        """推送异常。"""
        if not self._done:
            self.queue.put_nowait(("error", error_msg))

    def mark_done(self):
        """标记结束。"""
        if not self._done:
            self._done = True
            self.queue.put_nowait(("done", None))

    async def get(self):
        """从队列获取下一个条目。"""
        return await self.queue.get()


_stream_ctx: contextvars.ContextVar = contextvars.ContextVar(
    "stream_ctx", default=None
)


def get_stream_context() -> StreamContext | None:
    """节点内调用，获取当前请求的 StreamContext。"""
    return _stream_ctx.get(None)


# ── 主适配器 ──

async def stream_graph_to_sse(compiled_graph, input_state: dict, request: Request):
    """将 LangGraph astream_events 转换为 SSE 文本流。

    使用 asyncio.Queue 合并两个事件源：
    1. astream_events（节点开始/结束、retry 检测、state 收集）
    2. 节点内 push_token（LLM 流式 token）
    """
    config = {"configurable": {"thread_id": str(uuid4())}}
    ctx = StreamContext()
    _stream_ctx.set(ctx)

    current_node = ""
    accumulated_state = {}
    streaming_node_seen: set[str] = set()

    async def graph_event_producer():
        """后台任务：迭代 astream_events，将事件推入队列。"""
        try:
            async for event in compiled_graph.astream_events(
                input_state, config, version="v2"
            ):
                if await request.is_disconnected():
                    logger.info("客户端断开连接（graph stream）")
                    break
                ctx.push_event(event)
        except Exception as exc:
            logger.exception("Graph 执行异常: %s", exc)
            ctx.push_error(str(exc))
        ctx.mark_done()

    task = asyncio.create_task(graph_event_producer())

    try:
        while True:
            typ, data = await ctx.get()

            if typ == "done":
                break

            if typ == "error":
                yield f"data: {json.dumps({'error': data}, ensure_ascii=False)}\n\n"
                break

            if typ == "token":
                # 节点推送的 LLM token（已经过 ThoughtProcessFilter 过滤）
                payload = json.dumps({"token": data}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
                continue

            # typ == "event": 处理 astream_events 事件
            if typ != "event":
                continue

            event = data
            kind = event["event"]

            # ── 跟踪当前节点（仅业务节点）──
            if kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name in _GRAPH_NODES:
                    current_node = node_name
                    logger.info("→ 节点开始: %s", current_node)
                    # ★ 重试检测
                    if node_name in _STREAMING_NODES:
                        if node_name in streaming_node_seen:
                            yield f'data: {json.dumps({"event": "reset"}, ensure_ascii=False)}\n\n'
                            logger.info("检测到 %s 重试，已通知前端重置缓冲区", node_name)
                        else:
                            streaming_node_seen.add(node_name)

            # ── 节点结束时收集返回值 ──
            elif kind == "on_chain_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, dict):
                    accumulated_state.update(output)

            # ── LLM stream 事件（兜底，理论上不会触发）──
            elif kind == "on_chat_model_stream":
                logger.info("on_chat_model_stream 触发了（token 应由节点 push，此路径仅作兜底）")
                chunk = event["data"]["chunk"]
                content = chunk.content if hasattr(chunk, "content") else ""
                if content and current_node in _STREAMING_NODES:
                    payload = json.dumps({"token": content}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"

    finally:
        if not task.done():
            task.cancel()

    # ── 图执行结束后，从 state 取出最终结果 ──
    if accumulated_state.get("html"):
        payload = json.dumps(
            {"token": "\n\n" + accumulated_state["html"]}, ensure_ascii=False
        )
        yield f"data: {payload}\n\n"
    elif accumulated_state.get("error"):
        yield f"data: {json.dumps({'error': accumulated_state['error']}, ensure_ascii=False)}\n\n"

    yield 'data: {"event":"[DONE]"}\n\n'
