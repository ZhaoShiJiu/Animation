"""
state.py — AnimationState TypedDict，所有 graph 共用。
"""
from typing import TypedDict, Optional


class AnimationState(TypedDict, total=False):
    """LangGraph 动画生成的全局状态。

    字段按生命周期阶段分组，total=False 表示所有字段可选。
    """

    # ── 输入 ──
    topic: str                          # 用户输入的主题/概念
    settings: dict                      # {style, duration, ratio, depth, resolution, ...}
    history: list[dict]                 # 多轮对话历史 [{role, content}, ...]

    # ── PDF 论文输入（paper_graph 专用）──
    pdf_filename: str                   # 上传的 PDF 文件名
    pdf_text: str                       # 已提取的论文全文
    pdf_truncated: bool                 # 论文是否因超长被截断
    focus: str                          # 用户指定的论文重点章节

    # ── 中间产物 ──
    outline: dict                       # 主题/论文分析结果
    narrative_json: dict                # 纯文案
    direction_json: dict                # 动画指导
    segments_raw: str                   # LLM 原始输出的 JSON 字符串
    segments: list[dict]                # Pydantic 校验后的 5 段数据
    seg_durations: list[int]            # 每段时间分配

    # ── 最终产物 ──
    html: str                           # 拼装完成的完整动画 HTML

    # ── 控制字段 ──
    error: str                          # 当前错误信息
    validation_feedback: str            # 校验失败时给 LLM 的修正指令
    retry_count: int                    # 当前重试次数
    max_retries: int                    # 最大重试次数，默认 2
    narrative_valid: bool               # 纯文案是否通过 Pydantic 校验
    direction_valid: bool               # 动画指导是否通过 Pydantic 校验
    segments_valid: bool                # segments 是否通过 Pydantic 校验
