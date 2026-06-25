"""
models.py — Pydantic 请求/响应模型。
从 app.py 拆分出来。
"""
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    topic: str
    history: Optional[List[dict]] = None
    settings: Optional[Dict[str, Any]] = None


# ── Two-stage generation models ──

class CopyAct(BaseModel):
    act: int
    name: str
    goal: str
    duration_hint: int
    method_used: str
    narration: str
    narration_en: str = ""
    visual_description: str
    on_screen_text: str = ""


class CopySchema(BaseModel):
    narrative_type: str = "problem_conflict"
    title: str
    visual_style: str = "cinematic"
    color_palette: str = ""
    total_duration_hint: int = 60
    acts: List[CopyAct] = []


class PassphraseRequest(BaseModel):
    passphrase: str


class ShareRequest(BaseModel):
    html: str
    expiresIn: str
    password: str = Field(pattern=r"^\d{4,20}$")
    sourceWidth: int = 1920
    sourceHeight: int = 1080


class VideoExportRequest(BaseModel):
    html: Optional[str] = Field(default=None, max_length=5_000_000)
    share_id: Optional[str] = Field(default=None, max_length=64)
    width: int = Field(default=1920, ge=640, le=4096)
    height: int = Field(default=1080, ge=360, le=4096)
    fps: int = Field(default=24, ge=12, le=60)
    expires_in: str = Field(default="1h", pattern=r"^(10m|1h|6h|1d|7d)$")
    duration_seconds: Optional[float] = None


class LogErrorRequest(BaseModel):
    errors: List[Dict[str, Any]] = []


# ── LLM 输出校验模型（LangGraph validate 节点使用）──

class AnimationSegment(BaseModel):
    """单个动画段落的 schema——同时用于 prompt 生成和结果校验"""
    title: str = Field(description="画面大字，不超过12字", max_length=12)
    titleColor: str = Field(
        default="#DC2626",
        description="强调色，如 #DC2626",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
    subZh: str = Field(description="中文旁白")
    subEn: str = Field(default="", description="英文字幕")
    body: str = Field(default="", description="补充说明小字")
    bigNum: str | None = Field(default=None, description="大号数字")
    visualSVG: str | None = Field(default=None, description="SVG 图形，viewBox 坐标系，内部属性用单引号")
    steps: list[str] | None = Field(default=None, description="步骤列表，段2专用（3-5个步骤）")
    compareBefore: str | None = Field(default=None, description="对比前，段3专用")
    compareAfter: str | None = Field(default=None, description="对比后，段3专用")
    compareLabelBefore: str | None = Field(default=None, description="对比前标签")
    compareLabelAfter: str | None = Field(default=None, description="对比后标签")

    @model_validator(mode="after")
    def mutually_exclusive_visual(self):
        """每段只能用一个可视化类型（visualSVG / steps / compareBefore）"""
        present = sum(1 for v in [
            self.visualSVG is not None,
            self.steps is not None,
            self.compareBefore is not None,
        ] if v)
        if present > 1:
            raise ValueError(
                f"visualSVG/steps/compareBefore 每段只能用一个，当前用了{int(present)}个"
            )
        return self


class AnimationOutput(BaseModel):
    """LLM 输出的顶层结构——必须是 Object（segments 数组），不能直接是数组"""
    segments: list[AnimationSegment] = Field(
        description="5个动画段落",
        min_length=5,
        max_length=5,
    )
