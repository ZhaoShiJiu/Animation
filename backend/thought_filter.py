"""
thought_filter.py — 流式 token 思考标签过滤器。

DeepSeek R1 等模型即使在 json_object 模式下仍输出 <think>...</think> 标签。
本过滤器在流式接收 token 时实时剥离，确保前后端拿到纯净输出。
"""
from typing import Optional


class ThoughtProcessFilter:
    """流式思考标签过滤器。逐 token 喂入，返回剥离后的可见文本。"""

    START_MARKERS: tuple[str, ...] = (
        "<think>",
        "<thinking>",
        "<reasoning>",
        "思考过程：",
        "思考过程:",
    )
    END_MARKERS: tuple[str, ...] = (
        "</think>",
        "</thinking>",
        "</reasoning>",
        "最终答案：",
        "最终答案:",
        "答案：",
        "答案:",
    )

    def __init__(self) -> None:
        self._buffer: str = ""
        self._in_thought: bool = False
        self._max_start_len: int = max(len(m) for m in self.START_MARKERS)
        self._max_end_len: int = max(len(m) for m in self.END_MARKERS)

    @staticmethod
    def _find_first(text: str, markers: tuple[str, ...]) -> tuple[int, Optional[str]]:
        """在 text 中查找最早出现的 marker，返回 (index, marker)。"""
        found_idx = -1
        found_marker: Optional[str] = None
        lower = text.lower()
        for m in markers:
            idx = lower.find(m.lower())
            if idx != -1 and (found_idx == -1 or idx < found_idx):
                found_idx = idx
                found_marker = m
        return found_idx, found_marker

    def feed(self, text: str) -> str:
        """喂入新的 token 文本，返回可见部分。"""
        if not text:
            return ""

        self._buffer += text
        visible: list[str] = []

        while self._buffer:
            if self._in_thought:
                idx, marker = self._find_first(self._buffer, self.END_MARKERS)
                if idx == -1:
                    # 保留尾部若干字符，防止结束标记被截断
                    keep = max(0, len(self._buffer) - (self._max_end_len - 1))
                    self._buffer = self._buffer[-keep:] if keep > 0 else ""
                    break
                self._buffer = self._buffer[idx + len(marker):]
                self._in_thought = False
                continue

            idx, marker = self._find_first(self._buffer, self.START_MARKERS)
            if idx == -1:
                keep = self._max_start_len - 1
                if len(self._buffer) <= keep:
                    break
                visible.append(self._buffer[:-keep])
                self._buffer = self._buffer[-keep:]
                break

            visible.append(self._buffer[:idx])
            self._buffer = self._buffer[idx + len(marker):]
            self._in_thought = True

        return "".join(visible)

    def flush(self) -> str:
        """流结束，清空缓冲区。如果仍在思考中则丢弃。"""
        if self._in_thought:
            self._buffer = ""
            return ""
        remaining = self._buffer
        self._buffer = ""
        return remaining
