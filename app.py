import asyncio
import base64
import html
import io
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Optional, Dict, Any
from urllib.parse import parse_qs

import pytz
import qrcode
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader
from video_exporter import get_video_exporter
from logger import get_logger, log_llm_request, log_llm_response_start, log_llm_response_end, log_llm_error
from html_postprocessor import postprocess_html

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    from google import genai

logger = get_logger(__name__)
# -----------------------------------------------------------------------
# 0. 配置
# -----------------------------------------------------------------------
shanghai_tz = pytz.timezone("Asia/Shanghai")

credentials = json.load(open("credentials.json"))
API_KEY = credentials["API_KEY"]
BASE_URL = credentials.get("BASE_URL", "")
MODEL = credentials.get("MODEL", "")
ENABLE_DEBUG_OUTPUT = credentials.get("ENABLE_DEBUG_OUTPUT", True)
MAX_CONCURRENT_GENERATION_TASKS = credentials.get("MAX_CONCURRENT_GENERATION_TASKS", 1)
MAX_PAPER_UPLOAD_BYTES = credentials.get("MAX_PAPER_UPLOAD_BYTES", 20 * 1024 * 1024)
MAX_PAPER_TEXT_CHARS = credentials.get("MAX_PAPER_TEXT_CHARS", 120000)
ACCESS_PASSPHRASES = credentials.get("ACCESS_PASSPHRASES")
MAX_CONCURRENT_EXPORT_TASKS = credentials.get("MAX_CONCURRENT_EXPORT_TASKS", 1)
generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATION_TASKS)
export_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXPORT_TASKS)
shared_html_links = {}
SHARE_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "shared_html")
SHARE_CLEANUP_INTERVAL_SECONDS = 300


SHARE_EXPIRATION_SECONDS = {
    "1h": 60 * 60,
    "3h": 3 * 60 * 60,
    "6h": 6 * 60 * 60,
    "8h": 8 * 60 * 60,
    "1d": 24 * 60 * 60,
    "3d": 3 * 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
    "forever": None,
}

# Video export storage
VIDEO_STORAGE_DIR = os.path.join(os.path.dirname(__file__), "exported_videos")
VIDEO_CLEANUP_INTERVAL_SECONDS = 300
VIDEO_DEFAULT_RETENTION_SECONDS = 60 * 60  # 1 hour

VIDEO_EXPIRATION_SECONDS = {
    "10m": 10 * 60,
    "1h": 60 * 60,
    "6h": 6 * 60 * 60,
    "1d": 24 * 60 * 60,
    "7d": 7 * 24 * 60 * 60,
}

# Maps UI duration setting → approximate seconds (used for meta tag hint)
DURATION_SECONDS_HINT = {
    "preview": 12,
    "short": 30,
    "medium": 60,
    "long": 90,
}


def _debug_llm(label: str, value=None):
    """兼容旧的 debug_llm 调用 —— 现在走统一日志系统."""
    if not ENABLE_DEBUG_OUTPUT:
        return
    logger.debug("===== LLM DEBUG: %s =====", label)
    if value is not None:
        if isinstance(value, (dict, list)):
            logger.debug(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            logger.debug(str(value))
    logger.debug("===== END LLM DEBUG: %s =====", label)


def _debug_conversation(provider: str, model: str, messages: List[dict], settings: Dict[str, Any]):
    if ENABLE_DEBUG_OUTPUT:
        log_llm_request(provider, model, messages, settings)


def _debug_response_start(provider: str):
    if ENABLE_DEBUG_OUTPUT:
        log_llm_response_start(provider)


def _debug_response_chunk(chunk: str):
    # 流式 chunk 直接输出到控制台，不进入日志文件（避免 I/O 风暴）
    if ENABLE_DEBUG_OUTPUT and chunk:
        import sys
        sys.stdout.write(chunk)
        sys.stdout.flush()


def _debug_response_end():
    if ENABLE_DEBUG_OUTPUT:
        log_llm_response_end()


class ThoughtProcessFilter:
    START_MARKERS = (
        "<think>",
        "<thinking>",
        "<reasoning>",
        "思考过程：",
        "思考过程:",
    )
    END_MARKERS = (
        "</think>",
        "</thinking>",
        "</reasoning>",
        "最终答案：",
        "最终答案:",
        "答案：",
        "答案:",
    )

    def __init__(self):
        self.buffer = ""
        self.in_thought = False
        self.max_start_marker_length = max(len(marker) for marker in self.START_MARKERS)
        self.max_end_marker_length = max(len(marker) for marker in self.END_MARKERS)

    @staticmethod
    def _find_first_marker(text: str, markers: tuple[str, ...]):
        found_index = -1
        found_marker = None
        lower_text = text.lower()
        for marker in markers:
            index = lower_text.find(marker.lower())
            if index != -1 and (found_index == -1 or index < found_index):
                found_index = index
                found_marker = marker
        return found_index, found_marker

    def feed(self, text: str) -> str:
        if not text:
            return ""

        self.buffer += text
        visible_parts = []

        while self.buffer:
            if self.in_thought:
                index, marker = self._find_first_marker(self.buffer, self.END_MARKERS)
                if index == -1:
                    self.buffer = self.buffer[-(self.max_end_marker_length - 1):]
                    break
                self.buffer = self.buffer[index + len(marker):]
                self.in_thought = False
                continue

            index, marker = self._find_first_marker(self.buffer, self.START_MARKERS)
            if index == -1:
                keep_length = self.max_start_marker_length - 1
                if len(self.buffer) <= keep_length:
                    break
                visible_parts.append(self.buffer[:-keep_length])
                self.buffer = self.buffer[-keep_length:]
                break

            visible_parts.append(self.buffer[:index])
            self.buffer = self.buffer[index + len(marker):]
            self.in_thought = True

        return "".join(visible_parts)

    def flush(self) -> str:
        if self.in_thought:
            self.buffer = ""
            return ""
        visible = self.buffer
        self.buffer = ""
        return visible

if API_KEY.startswith("sk-"):
    # 为 OpenRouter 添加应用标识
    extra_headers = {}    
    client = AsyncOpenAI(
        api_key=API_KEY, 
        base_url=BASE_URL,
    )

if API_KEY.startswith("sk-REPLACE_ME"):
    raise RuntimeError("请在环境变量里配置 API_KEY")

templates = Jinja2Templates(directory="templates")

# -----------------------------------------------------------------------
# 1. FastAPI 初始化
# -----------------------------------------------------------------------
app = FastAPI(title="AI Animation Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── HTTP 请求日志中间件 ──
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有 HTTP 请求及响应状态/耗时."""
    start_time = time.time()
    logger.info("→ %s %s | client=%s", request.method, request.url.path,
                request.client.host if request.client else "unknown")

    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.time() - start_time) * 1000
        logger.exception("✗ %s %s | 耗时=%.0fms | 未捕获异常",
                         request.method, request.url.path, elapsed)
        raise

    elapsed = (time.time() - start_time) * 1000
    status_code = response.status_code
    if status_code >= 500:
        logger.error("✗ %s %s → %s | 耗时=%.0fms",
                     request.method, request.url.path, status_code, elapsed)
    elif status_code >= 400:
        logger.warning("← %s %s → %s | 耗时=%.0fms",
                      request.method, request.url.path, status_code, elapsed)
    else:
        logger.info("← %s %s → %s | 耗时=%.0fms",
                   request.method, request.url.path, status_code, elapsed)
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")

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


class CopyRequest(BaseModel):
    topic: str
    settings: Optional[Dict[str, Any]] = None


class AnimationRequest(BaseModel):
    copy_json: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None


class PassphraseRequest(BaseModel):
    passphrase: str


class ShareRequest(BaseModel):
    html: str
    expiresIn: str
    password: str = Field(pattern=r"^\d{4,20}$")
    sourceWidth: int = 1920
    sourceHeight: int = 1080


class VideoExportRequest(BaseModel):
    html: Optional[str] = Field(default=None, max_length=5_000_000)  # ~5 MB
    share_id: Optional[str] = Field(default=None, max_length=64)
    width: int = Field(default=1920, ge=640, le=4096)
    height: int = Field(default=1080, ge=360, le=4096)
    fps: int = Field(default=24, ge=12, le=60)
    expires_in: str = Field(default="1h", pattern=r"^(10m|1h|6h|1d|7d)$")
    duration_seconds: Optional[float] = None


def build_generation_setting_instructions(settings: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    settings = settings or {}
    allowed_styles = {
        "cinematic": "电影级叙事：镜头感强、节奏完整、视觉层次丰富。",
        "minimal": "极简专业：留白克制、信息清晰、图形精准。",
        "academic": "教学讲解：结构严谨、步骤明确、适合课堂演示。",
        "futuristic": "未来科技：高对比、科技感视觉、动态 HUD 元素。",
    }
    allowed_durations = {
        "preview": "快速预览：只生成一页，用来快速展示整体视觉效果；不要制作完整视频流程，不需要多段转场或长时间动画。",
        "short": "约 30 秒，重点突出，快速讲清核心概念。",
        "medium": "约 60 秒，完整讲解主要过程。",
        "long": "约 90 秒，包含更细的铺垫、推演和总结。",
    }
    allowed_ratios = {
        "16:9": "16:9 横屏画布，适合网页和演示。",
        "9:16": "9:16 竖屏画布，适合移动端短视频。",
        "1:1": "1:1 方形画布，适合社交媒体展示。",
    }
    allowed_depths = {
        "starter": "入门深度：避免术语堆叠，适合第一次接触该主题的观众。",
        "standard": "标准深度：兼顾直观解释和关键专业细节。",
        "expert": "专业深度：加入必要术语、推导逻辑和边界条件。",
    }
    allowed_resolutions = {
        "720p": "1280 × 720 的 720p 容器。",
        "1080p": "1920 × 1080 的 1080p 容器。",
        "2k": "2048 × 1152 的 2K 容器。",
    }
    return {
        "style": allowed_styles.get(settings.get("style"), allowed_styles["cinematic"]),
        "duration": allowed_durations.get(settings.get("duration"), allowed_durations["medium"]),
        "ratio": allowed_ratios.get(settings.get("ratio"), allowed_ratios["16:9"]),
        "depth": allowed_depths.get(settings.get("depth"), allowed_depths["standard"]),
        "resolution": allowed_resolutions.get(settings.get("resolution"), allowed_resolutions["1080p"]),
        "narration": "旁白文案要更丰富，字幕节奏要清楚。" if settings.get("narration") else "旁白文字保持精炼，只保留关键解释。",
        "bilingual": "必须提供中英双语字幕。" if settings.get("bilingual", True) else "只使用用户当前语言输出字幕。",
        "mathjax": "需要使用 MathJax 渲染数学公式；请在生成的单文件 HTML 中引入 MathJax CDN，并用 LaTeX 语法书写公式。" if settings.get("mathjax") else "不要引入 MathJax，数学表达使用普通文本或 SVG 图形呈现。",
    }


def build_copy_system_prompt(topic: str, settings: Optional[Dict[str, Any]] = None) -> str:
    """Build the 5-act problem-conflict narrative copy generation prompt."""
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)
    duration_sec = DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60)

    prompt = f"""你是一个采用「问题冲突型」叙事结构的科学动画编剧。

## 用户概念
{topic}

## 生成规格
- 视觉风格：{setting_instructions['style']}
- 总时长：约 {duration_sec} 秒
- 画幅：{setting_instructions['ratio']}
- 讲解深度：{setting_instructions['depth']}
- 旁白要求：{setting_instructions['narration']}
- 字幕要求：{setting_instructions['bilingual']}

## 叙事结构约束
你必须严格按照以下五幕结构来组织文案，每幕一个场景：

**第一幕·认知爆破**（3秒抓注意力）
- 手法四选一：假设危机 / 反常识 / 数据震撼 / 身份代入
- 要求：第一句话就要让观众停下来
- 时长：约占总时长 10-15%
- 色彩基调：高对比红/橙/黑 → 制造紧张和冲击力 (--color-danger)
- 动效暗示：快速弹性入场，文字带"刹车回弹"感
- 画面情绪：紧张、震惊、不可置信

**第二幕·延迟满足**（制造疑问，不给答案）
- 手法：强化错误认知 + 暗示答案相反 + 留下更大疑问
- 要求：让观众产生「到底怎么回事」的焦虑感
- 时长：约占总时长 15-20%
- 色彩基调：冷紫/灰蓝 → 神秘、悬疑、未知 (--color-mystery)
- 动效暗示：缓慢揭示，文字从模糊到清晰，大量留白
- 画面情绪：困惑、好奇、被吊胃口

**第三幕·层层揭秘**（保持观看，逐步解锁）
- 手法：一问一答 + 连续小反转 + 信息量逐级递增
- 要求：每揭示一层就抛出一个新问题，形成信息阶梯
- 时长：约占总时长 30-40%
- 色彩基调：清爽蓝/青 → 理性、逻辑、清晰 (--color-reveal)
- 动效暗示：逐条 stagger 滑入，每层揭示后前层变暗聚焦新层
- 画面情绪：逐渐理解、跟上了思路

**第四幕·高潮揭晓**（产生「原来如此」）
- 手法：颠覆原有认知 + 揭示核心原理 + 放大对比
- 要求：用一个清晰的视觉类比或逻辑链条完成最终解释
- 时长：约占总时长 15-20%
- 色彩基调：从蓝色渐变过渡到亮绿 (--color-insight)
- 动效暗示：核心概念放大 + glow（外发光），旧认知淡出/缩小
- 画面情绪：恍然大悟、产生认知快感

**第五幕·记忆钉**（留下传播点）
- 手法：一句话总结 + 金句化表达 + 哲理升华
- 要求：让观众看完后能复述给别人的一句话
- 时长：约占总时长 10-15%
- 色彩基调：暖金/琥珀 → 温暖、沉淀、可传播 (--color-memory)
- 动效暗示：文字优雅居中放大，背景安静收束，logo 般定格
- 画面情绪：满足、想分享

## visual_description 编写规范
每个 act 的 visual_description 必须包含以下6个维度的具体描述：
1. **构图**：元素在画面中的位置（居中/偏左/偏右/网格分布），主次关系
2. **颜色**：背景色、主文字色、辅助图形色、强调色
3. **图形**：形状类型（圆形/矩形/连线/箭头/流程图）、数量、大小关系
4. **动效方向**：从哪个方向进入（下方/左侧/缩放/透明度）
5. **镜头运动**：模拟摄像机的运动感（推近/拉远/平移/固定）
6. **SVG建议**：如果适合用 SVG 图形表达——比如数据流向、公式图解、模型结构——请描述应该画什么

示例（好的 visual_description）：
"画面中央偏上是一个大号问号 SVG 图形，灰色半透明，缓缓旋转。背景是冷紫色调渐变。
文字从画面下方 60px 处弹入（弹性缓动），停在正中央，font-weight 900。
2秒后，问号淡出，背景渐变从紫色过渡到蓝色，暗示答案即将揭晓。"

## 输出格式（纯 JSON，不要任何其他内容）
{{
  "narrative_type": "problem_conflict",
  "title": "动画标题",
  "visual_style": "{settings.get('style', 'cinematic')}",
  "color_palette": "按五幕顺序描述色彩变化：第一幕红/橙→第二幕紫/灰→第三幕蓝→第四幕绿→第五幕暖金",
  "total_duration_hint": {duration_sec},
  "acts": [
    {{
      "act": 1,
      "name": "认知爆破",
      "goal": "3秒抓住注意力",
      "duration_hint": 8,
      "method_used": "反常识",
      "narration": "中文旁白文字",
      "narration_en": "English narration",
      "visual_description": "具体画面描述：必须包含构图、颜色、图形、动效方向、镜头运动、SVG建议六个维度",
      "on_screen_text": "画面上展示的关键大字（≤10字）"
    }}
  ]
}}

## 要求
- 旁白口语化，适合朗读，中文每句不超过 35 字
- 英文旁白为中文的准确翻译
- on_screen_text 是大字/金句，每屏 ≤10 字，与旁白互补不重复
- visual_description 必须包含构图+颜色+图形+动效方向+镜头运动+SVG建议六个维度
- color_palette 描述五幕的色彩流变
- 输出纯 JSON，不要 markdown 代码块包裹"""
    return prompt


def _build_design_system_spec(settings: Dict[str, Any], duration_sec: int) -> str:
    """构建共享的设计系统规范文本，供所有动画生成 prompt 复用。"""
    ratio = settings.get("ratio", "16:9")
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = _build_resolution_dims(resolution_key)

    return f"""## 🎨 设计系统（Design System）—— 必须严格遵循

### CSS 变量体系 —— 必须定义在 :root 中
```css
:root {{
  /* 主色调 —— 根据叙事阶段动态切换 */
  --color-danger:    #DC2626;   /* 危机/问题/警告 */
  --color-mystery:   #7C3AED;   /* 悬念/疑问/未知 */
  --color-reveal:    #2563EB;   /* 揭示/解释/逻辑 */
  --color-insight:   #059669;   /* 顿悟/答案/真相 */
  --color-memory:    #D97706;   /* 金句/记忆/总结 */
  --color-bg:        #FAFBFC;   /* 全局背景 */
  --color-surface:   #FFFFFF;   /* 卡片/面板背景 */
  --color-text:      #0F172A;   /* 主文字色 */
  --color-text-dim:  #64748B;   /* 次要文字/字幕 */
  --color-border:    #E2E8F0;   /* 细线/分割 */

  /* 排版层级 */
  --font-display:  'MiSans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --font-body:     'MiSans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --fs-hero:       clamp(3.5rem, 8vw, 7rem);    /* 主标题大字 */
  --fs-headline:   clamp(2rem, 5vw, 4rem);      /* 场景标题 */
  --fs-body:       1.25rem;                       /* 正文 */
  --fs-subtitle:   1.05rem;                       /* 字幕 */
  --fs-small:      0.85rem;                       /* 标注 */

  /* 间距网格 (8px 基准) */
  --space-xs:  8px;
  --space-sm:  16px;
  --space-md:  24px;
  --space-lg:  40px;
  --space-xl:  64px;
  --space-2xl: 96px;

  /* 缓动函数 —— 必须使用这些！*/
  --ease-smooth:   cubic-bezier(0.22, 0.61, 0.36, 1);     /* 常规过渡 */
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);     /* 弹性出场 */
  --ease-spring:   cubic-bezier(0.175, 0.885, 0.32, 1.275); /* 弹簧感 */
  --ease-slow:     cubic-bezier(0.25, 0.1, 0.25, 1);       /* 慢入慢出 */
}}

body {{
  margin: 0; padding: 0;
  width: {res_w}px; height: {res_h}px;
  overflow: hidden;
  font-family: var(--font-body);
  background: var(--color-bg);
  /* 抗锯齿 */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}}
```

### 背景层次架构 —— 每个场景必须包含三层背景
```html
<!-- L1: 渐变底色 -->
<div class="bg-base" style="position:absolute;inset:0;background:linear-gradient(135deg, var(--color-bg) 0%, #F1F5F9 100%);"></div>
<!-- L2: 纹理叠加（网格/噪点） -->
<svg class="bg-texture" style="position:absolute;inset:0;width:100%;height:100%;opacity:0.04;"><defs><pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" stroke-width="1"/></pattern></defs><rect width="100%" height="100%" fill="url(#grid)"/></svg>
<!-- L3: 浮动光晕装饰 -->
<div class="bg-glow" style="position:absolute;width:600px;height:600px;border-radius:50%;background:radial-gradient(circle, var(--glow-color, rgba(37,99,235,0.06)) 0%, transparent 70%);filter:blur(60px);"></div>
```
根据每幕的情绪，.bg-glow 的 --glow-color 应该变化。

### GSAP 时间轴 —— 强制要求（不是建议！）

**必须**从 CDN 引入 GSAP：`<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>`

**必须**使用以下时间轴架构组织所有动画：
```javascript
// 全局时间轴 —— 所有场景动画必须挂载到这里
const masterTL = gsap.timeline({{ paused: false }});

// 每个场景的开始时间（秒），由 duration_hint 累加得出
let currentTime = 0;
const sceneDurations = [{{scene_durations}}]; // 从文案中提取的 duration_hint 数组

// 场景切换函数
function buildScene(sceneIndex, duration) {{
  const sceneStart = currentTime;
  const tl = gsap.timeline();

  // === 入场：元素从下往上淡入 ===
  tl.fromTo(`#scene-${{sceneIndex}} .entrance-el`,
    {{ y: 60, opacity: 0 }},
    {{ y: 0, opacity: 1, duration: 0.8, stagger: 0.12, ease: "power3.out" }}
  );

  // === 驻留：微妙呼吸感 ===
  tl.to(`#scene-${{sceneIndex}} .accent-shape`, {{
    scale: 1.04, duration: duration * 0.6, ease: "sine.inOut", yoyo: true, repeat: 1
  }}, "-=0.2");

  // === 退场 ===
  tl.to(`#scene-${{sceneIndex}}`, {{
    opacity: 0, scale: 0.97, duration: 0.5, ease: "power2.in"
  }}, `>+${{duration - 0.8}}`);

  masterTL.add(tl, sceneStart);
  currentTime += duration;
}}

// 注册到全局对象（视频导出需要）
window.__timelines = [masterTL];
```

**绝对禁止**：
- ❌ 使用 CSS @keyframes animation（视频导出时会丢帧）
- ❌ 使用 setTimeout/setInterval 控制动画时序
- ❌ 使用 Math.random() 或 Date.now() 影响动画行为
- ❌ 依赖 scroll、click、hover 等用户交互触发动画

### 五幕动效设计语言（Motion Design Language）

**第一幕「认知爆破」—— 冲击入场**
- easing: back.out(1.7) 或 elastic.out(1, 0.3)
- duration_per_element: 0.4–0.6s
- stagger: 0.05–0.08s（几乎同时，形成冲击感）
- scale: 0.8→1.0 或 y: 80→0
- 背景色: 深色或高饱和 → 快速切到明亮
- 特效: 大号文字 scale 轻微过冲回弹

**第二幕「延迟满足」—— 悬疑慢揭**
- easing: power2.inOut（缓慢、平滑）
- duration_per_element: 1.0–1.5s
- stagger: 0.3–0.5s（大量留白）
- opacity: 0→0.6→1（两次渐变）
- 背景色: 偏冷灰紫色调（--color-mystery）
- 特效: 文字从模糊到清晰（filter: blur→0）

**第三幕「层层揭秘」—— 信息阶梯**
- easing: power3.out
- duration_per_element: 0.5–0.8s
- stagger: 0.12–0.18s（逐条递进）
- transform: x: -30→0（从左侧滑入）
- 每层揭示后，前一层轻微变暗（opacity: 0.5），聚焦最新层
- 背景色: 清爽蓝白色（--color-reveal）
- 特效: 连接线/箭头随内容展开而延伸（stroke-dashoffset 动画）

**第四幕「高潮揭晓」—— 认知翻转**
- easing: power4.out（强烈加速→减速）
- duration: 0.6–1.0s
- 核心元素: scale: 1.0→1.15，glow 滤镜增强
- 背景色: 从蓝色渐变过渡到绿色（--color-insight）
- 特效: 旧认知画面 opacity→0 + scale→0.9；新认知画面 scale: 1.1→1.0 + opacity: 0→1
- 关键概念使用 SVG 外发光滤镜（<filter id="glow">）

**第五幕「记忆钉」—— 优雅定格**
- easing: power4.out（最舒缓）
- duration: 1.2–1.8s
- 金句文字: y: 30→0, scale: 0.95→1.0, 使用弹性缓动
- 背景色: 暖色调（--color-memory），画面逐渐安静
- 装饰元素缓慢收缩/淡出，画面只剩核心金句
- 最终定格至少 2 秒（纯静态，给观众消化时间）

### 排版层次铁律
```
┌─────────────────────────────────┐
│     (顶部留白 ≥ 画面高度 10%)     │
│                                 │
│   主文字 (on_screen_text)        │ ← font-size: var(--fs-hero)
│   font-weight: 900              │   居中，占画面高度 8-12%
│   letter-spacing: -0.03em       │
│                                 │
│   (主文字与字幕之间 ≥ 画面高度 15%)│
│                                 │
│   ┌──────────────────────┐      │
│   │ 中文字幕 (narration)   │      │ ← font-size: var(--fs-subtitle)
│   │ English subtitle     │      │   font-weight: 500
│   └──────────────────────┘      │   底部 8-12% 区域
│   (底部留白 ≥ 画面高度 6%)       │   半透明背景条包裹
└─────────────────────────────────┘
```
**铁律**：
1. 主文字和字幕之间必须有明显的视觉层级差（大小至少 3:1）
2. 字幕必须放在半透明背景条上（background: rgba(255,255,255,0.75) 或 rgba(0,0,0,0.6)），确保在任何背景上都可读
3. 每屏文字总量不超过 40 个中文字（含字幕）

### SVG 图形质量标准
- 所有 SVG 必须指定 viewBox，使用相对坐标
- 图标/图形使用 stroke-linecap="round" stroke-linejoin="round"
- 数据流程/连接线：使用 stroke-dasharray + stroke-dashoffset 动画（"画线"效果）
- 关键图形定义 <filter id="glow"> 外发光滤镜用于强调
- 渐变使用 <linearGradient> 而非纯色填充
- 图形变换优先使用 transform="translate(...) scale(...)" 而非修改坐标

### 场景过渡模式
场景之间**禁止**生硬跳切。使用以下过渡模式之一：
1. **叠化（推荐）**：前场景 opacity 1→0 + 后场景 opacity 0→1，重叠 0.3s
2. **推入**：后场景从右侧 translateX(100%)→0，前场景 0→translateX(-30%)
3. **缩放聚焦**：前场景 scale 1→1.2 + opacity 1→0；后场景 scale 0.9→1 + opacity 0→1

### 视频导出兼容性
- <meta name="animation-duration" content="{duration_sec}">
- window.__timelines 必须包含所有 GSAP timeline
- 动画总时长 = 各场景 duration_hint 之和 + 过渡时间
- 所有资源内联（无外部图片/字体请求，GSAP CDN 除外）"""


def _build_resolution_dims(resolution_key: str) -> tuple:
    """返回 (width, height) 像素值。"""
    mapping = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "2k": (2048, 1152),
    }
    return mapping.get(resolution_key, (1920, 1080))


def _resolution_width(resolution_key: str = "1080p") -> int:
    return _build_resolution_dims(resolution_key)[0]


def _resolution_height(resolution_key: str = "1080p") -> int:
    return _build_resolution_dims(resolution_key)[1]


# ── 模板缓存 ──
_ANIMATION_TEMPLATE_CACHE: Optional[str] = None


def _load_animation_template() -> str:
    """加载动画 HTML 骨架模板（带缓存）。"""
    global _ANIMATION_TEMPLATE_CACHE
    if _ANIMATION_TEMPLATE_CACHE is not None:
        return _ANIMATION_TEMPLATE_CACHE
    template_path = os.path.join(os.path.dirname(__file__), "static", "animation-template.html")
    with open(template_path, "r", encoding="utf-8") as fh:
        _ANIMATION_TEMPLATE_CACHE = fh.read()
    return _ANIMATION_TEMPLATE_CACHE


def build_animation_from_copy_system_prompt(copy_json: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> str:
    """Template-fill prompt for the continuous-flow animation template.

    The LLM fills {{SEGMENT_0}} … {{SEGMENT_4}} with JavaScript objects
    describing each segment's content.  The template already contains all
    CSS, GSAP timeline logic, background layers, and continuous motion.
    """
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)
    duration_sec = copy_json.get("total_duration_hint", DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60))

    # 分辨率
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = _build_resolution_dims(resolution_key)

    # 每幕的时长
    acts = copy_json.get("acts", [])
    seg_durations = [str(act.get("duration_hint", 10)) for act in acts]
    seg_durations_str = ", ".join(seg_durations)

    # 文案 JSON
    copy_text = json.dumps(copy_json, ensure_ascii=False, indent=2)

    # 加载模板并预填分辨率/时长
    template = _load_animation_template()
    template = template.replace("{{TOTAL_DURATION}}", str(duration_sec))
    template = template.replace("{{SCENE_W}}", str(res_w))
    template = template.replace("{{SCENE_H}}", str(res_h))
    template = template.replace("{{SEGMENT_DURATIONS}}", seg_durations_str)
    template = template.replace("{{PRIMARY_COLOR}}", "#2563EB")
    template = template.replace("{{SECONDARY_COLOR}}", "#7C3AED")

    # 提取每幕关键信息作为提示
    act_summaries = []
    color_hints = ["#DC2626", "#7C3AED", "#2563EB", "#059669", "#D97706"]
    for i, act in enumerate(acts):
        act_summaries.append(
            f"  第{i+1}幕「{act.get('name', '')}」({act.get('duration_hint', 10)}s): "
            f"手法={act.get('method_used', '')} | "
            f"大字={act.get('on_screen_text', '')} | "
            f"旁白={act.get('narration', '')[:40]}... | "
            f"色彩提示={color_hints[i]}"
        )

    prompt = f"""你是动画内容填充专家。下面是一份已经写好的**连续流动动画** HTML 模板。

## 你的任务
根据五幕文案，替换模板中的 `{{{{SEGMENT_0}}}}` ~ `{{{{SEGMENT_4}}}}` 这 5 个占位符。
每个占位符要替换成一个 **JavaScript 对象**，描述该段落的视觉内容。

## 核心规则
1. **只能替换 {{{{SEGMENT_N}}}} 占位符**，不能修改模板的 CSS、GSAP 代码、HTML 结构
2. 每个占位符替换为一个合法的 JS 对象字面量（见下方格式）
3. 输出完整 HTML（占位符全替换后），不要 Markdown 代码块，不要解释文字

## 五幕文案
{copy_text}

## 段落摘要
{chr(10).join(act_summaries)}

## 段落对象格式 —— 每个 SEGMENT_N 必须按此格式
```js
{{
  title: "画面大字金句（≤12字）",        // 必填，对应 on_screen_text
  titleColor: "#DC2626",               // 可选，大字强调色
  subZh: "中文旁白文字",                 // 必填，对应 narration
  subEn: "English subtitle",           // 可选，对应 narration_en
  body: "补充说明文字（可选）",           // 可选，小字补充
  bigNum: "97%",                       // 可选，大号数字（数据震撼手法时用）
  visualSVG: '<svg viewBox="0 0 100 100">...</svg>',  // 核心！见下方 SVG 指南
  steps: ["步骤1", "步骤2", "步骤3"],    // 层层揭秘时用，3-5个步骤
  compareBefore: "旧认知",              // 高潮揭晓时用
  compareAfter: "新认知",               // 高潮揭晓时用
  compareLabelBefore: "之前",           // 可选
  compareLabelAfter: "真相",            // 可选
}}
```
**注意**：不需要的字段可以省略。steps 和 compareBefore 通常不同时出现。

## SVG 视觉指南（visualSVG 字段）

根据不同幕选择不同的视觉形式：

**第1幕·认知爆破** — 冲击力图形：
- 大号问号或感叹号 SVG
- 裂开的几何形状
- 震撼数据用 bigNum 字段，不用 SVG

**第2幕·延迟满足** — 悬疑图形：
- 半透明旋转的问号
- 从模糊变清晰的形状（opacity 动画由模板处理）
- 被虚线圆圈包围的未知区域

**第3幕·层层揭秘** — 用 steps 数组（不用 visualSVG）：
- 每个步骤是一个字符串
- 3-5 个步骤，每个 ≤20 字

**第4幕·高潮揭晓** — 用 compareBefore/compareAfter（不用 visualSVG）：
- 对比新旧认知
- 或用一个"发光灯泡/钥匙"类型的 SVG

**第5幕·记忆钉** — 收束图形：
- 简单优雅的几何图形
- 圆形 + 对勾、钻石形、星形
- 如果不确定，留空 visualSVG

SVG 格式要求：
```
<svg viewBox="0 0 120 120" width="180" height="180">
  <circle cx="60" cy="60" r="50" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" data-draw="true"/>
  <text x="60" y="68" text-anchor="middle" font-size="32" font-weight="900" fill="currentColor">?</text>
</svg>
```
- 使用 viewBox 坐标
- stroke-linecap="round" stroke-linejoin="round"
- 颜色用 currentColor（会继承 stage-visual 的颜色）
- 需要"画线"动画的元素加 data-draw="true" 属性

## 模板
```html
{template}
```

只输出完整 HTML，一个字都不要多。"""
    return prompt


# -----------------------------------------------------------------------
# 2. 核心：流式生成器 (现在会使用 history)
# -----------------------------------------------------------------------
async def llm_event_stream(
    topic: str,
    history: Optional[List[dict]] = None,
    model: str = None, # Will use MODEL from config if not specified
    settings: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    history = history or []
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)

    # Use configured model if not specified
    if model is None:
        model = MODEL

    logger.info("LLM 请求 | topic=%s | model=%s | history_count=%d",
                topic[:100], model, len(history))
    if ENABLE_DEBUG_OUTPUT:
        _debug_llm("request received", {
            "provider": "openai-compatible",
            "model": model,
            "topic": topic,
            "history": history,
            "settings": settings,
        })

    # 使用连续流动模板填充模式
    duration_sec = DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60)
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = _build_resolution_dims(resolution_key)

    template = _load_animation_template()
    template = template.replace("{{TOTAL_DURATION}}", str(duration_sec))
    template = template.replace("{{SCENE_W}}", str(res_w))
    template = template.replace("{{SCENE_H}}", str(res_h))
    template = template.replace("{{SEGMENT_DURATIONS}}", "6, 10, 22, 14, 8")
    template = template.replace("{{PRIMARY_COLOR}}", "#2563EB")
    template = template.replace("{{SECONDARY_COLOR}}", "#7C3AED")

    system_prompt = f"""你是动画内容填充专家。为概念「{topic}」创作动画内容，替换模板中 `{{{{SEGMENT_0}}}}` ~ `{{{{SEGMENT_4}}}}` 这 5 个占位符。

## 核心规则
1. **只能替换 {{{{SEGMENT_N}}}} 占位符**，不修改模板 CSS/JS/HTML 结构
2. 每个替换为一个 JavaScript 对象（见格式）
3. 输出完整 HTML，不要 Markdown 代码块

## 内容规格
- 视觉风格：{setting_instructions['style']}
- 时长节奏：{setting_instructions['duration']}
- 讲解深度：{setting_instructions['depth']}
- 旁白：{setting_instructions['narration']}
- 字幕：{setting_instructions['bilingual']}

## 5 段落结构和时长
- 段落 0 (6s)：开场冲击 — 反常识/数据震撼/假设危机
- 段落 1 (10s)：悬念铺垫 — 暗示答案不简单
- 段落 2 (22s)：层层解释 — 每层一个新问题（用 steps 数组）
- 段落 3 (14s)：高潮揭晓 — 核心原理（用 compareBefore/compareAfter）
- 段落 4 (8s)：金句收尾 — 一句话总结

## 段落对象格式
```js
{{
  title: "大字金句（≤12字）",
  titleColor: "#DC2626",        // 可选，该段强调色（5段依次用: #DC2626, #7C3AED, #2563EB, #059669, #D97706）
  subZh: "中文旁白",
  subEn: "English subtitle",    // 如不需要双语则省略
  body: "补充说明（可选）",
  bigNum: "97%",                // 数据震撼时用
  visualSVG: '<svg viewBox="0 0 120 120">...</svg>',  // SVG 图标
  steps: ["步骤1", "步骤2"],     // 段落2用
  compareBefore: "旧认知",       // 段落3用
  compareAfter: "真相",          // 段落3用
}}
```

## SVG 要求
- viewBox 坐标系, stroke-linecap="round"
- 颜色用 currentColor
- 简洁几何图形，需要画线动画加 data-draw="true"
- 段落0: 冲击力图形（问号/感叹号/裂开形状）
- 段落1: 悬疑图形（旋转问号/迷雾/虚线框）
- 段落2: 用 steps 数组，不用 visualSVG
- 段落3: 用 compareBefore/compareAfter，或发光灯泡/钥匙 SVG
- 段落4: 优雅几何图形（圆形+对勾/星形），或留空 visualSVG

## 模板
```html
{template}
```

只输出完整 HTML。"""

    messages = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": topic},
    ]

    _debug_conversation("openai-compatible", model, messages, settings)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.8, 
        )
    except OpenAIError as e:
        log_llm_error("openai-compatible", str(e))
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    _debug_response_start("openai-compatible")
    thought_filter = ThoughtProcessFilter()
    async for chunk in response:
        # 某些 OpenAI-compatible / OpenRouter 流式块可能没有 choices 或没有 content
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue

        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if not delta:
            continue

        token = getattr(delta, "content", None) or ""
        if not token:
            continue

        visible_token = thought_filter.feed(token)
        if not visible_token:
            continue

        _debug_response_chunk(visible_token)
        payload = json.dumps({"token": visible_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"
        await asyncio.sleep(0.001)

    remaining_token = thought_filter.flush()
    if remaining_token:
        _debug_response_chunk(remaining_token)
        payload = json.dumps({"token": remaining_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"

    _debug_response_end()

    logger.info("LLM 流式生成完成")
    yield 'data: {"event":"[DONE]"}\n\n'


def parse_settings_form(settings: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(settings or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def extract_pdf_text(pdf_file: UploadFile) -> Dict[str, Any]:
    filename = pdf_file.filename or "paper.pdf"
    content_type = pdf_file.content_type or ""
    logger.info("PDF 提取开始 | filename=%s | size=%d", filename, pdf_file.size or 0)
    if not filename.lower().endswith(".pdf") and "pdf" not in content_type.lower():
        raise ValueError("请上传 PDF 文件")

    content = await pdf_file.read()
    if not content:
        raise ValueError("PDF 文件为空")
    if len(content) > MAX_PAPER_UPLOAD_BYTES:
        raise ValueError(f"PDF 文件过大，请上传不超过 {MAX_PAPER_UPLOAD_BYTES // 1024 // 1024}MB 的文件")

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        logger.exception("PDF 解析失败 | filename=%s", filename)
        raise ValueError("PDF 解析失败，请确认文件未损坏") from exc

    page_texts = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            page_texts.append(f"[Page {index}]\n{text}")

    paper_text = "\n\n".join(page_texts).strip()
    if not paper_text:
        logger.warning("PDF 未提取到文字 | filename=%s | pages=%d", filename, len(reader.pages))
        raise ValueError("未能从 PDF 中提取文字，暂不支持扫描版或图片型论文")

    truncated = len(paper_text) > MAX_PAPER_TEXT_CHARS
    if truncated:
        paper_text = paper_text[:MAX_PAPER_TEXT_CHARS]

    logger.info("PDF 提取完成 | filename=%s | pages=%d | chars=%d | truncated=%s",
                filename, len(reader.pages), len(paper_text), truncated)
    return {
        "filename": filename,
        "text": paper_text,
        "page_count": len(reader.pages),
        "truncated": truncated,
    }


async def paper_llm_event_stream(
    paper_text: str,
    filename: str,
    focus: str = "",
    model: str = None,
    settings: Optional[Dict[str, Any]] = None,
    truncated: bool = False,
) -> AsyncGenerator[str, None]:
    settings = settings or {}
    setting_instructions = build_generation_setting_instructions(settings)
    if model is None:
        model = MODEL

    focus_instruction = (
        f"用户指定重点：{focus}。请围绕该章节或概念展开，但必须结合整篇论文上下文说明其动机、方法和意义。"
        if focus.strip()
        else "用户未指定重点。请生成整篇论文的动画讲解，覆盖研究背景、核心问题、方法框架、关键实验/结果、结论与启发。"
    )
    truncation_instruction = "论文原文因长度限制已被截断，请基于已提供内容生成，并避免声称看到了未提供的部分。" if truncated else "论文原文已完整提供给你。"

    duration_sec = DURATION_SECONDS_HINT.get(settings.get("duration", "medium"), 60)
    resolution_key = settings.get("resolution", "1080p")
    res_w, res_h = _build_resolution_dims(resolution_key)

    template = _load_animation_template()
    template = template.replace("{{TOTAL_DURATION}}", str(duration_sec))
    template = template.replace("{{SCENE_W}}", str(res_w))
    template = template.replace("{{SCENE_H}}", str(res_h))
    template = template.replace("{{SEGMENT_DURATIONS}}", "8, 12, 20, 14, 6")
    template = template.replace("{{PRIMARY_COLOR}}", "#2563EB")
    template = template.replace("{{SECONDARY_COLOR}}", "#7C3AED")

    system_prompt = f"""你是论文讲解动画的内容填充专家。根据论文内容创作动画，替换模板中 `{{{{SEGMENT_0}}}}` ~ `{{{{SEGMENT_4}}}}`。

{focus_instruction}
{truncation_instruction}

## 核心规则
1. **只能替换 {{{{SEGMENT_N}}}}**，不修改模板 CSS/JS/HTML
2. 每个替换为 JS 对象（见格式）
3. 输出完整 HTML，不要 Markdown 代码块

## 内容规格
- 视觉风格：{setting_instructions['style']}
- 时长节奏：{setting_instructions['duration']}
- 讲解深度：{setting_instructions['depth']}

## 论文内容组织（5 段落）
- 段落 0 (8s)：研究背景与问题
- 段落 1 (12s)：核心洞察/假设
- 段落 2 (20s)：方法框架（用 steps 步骤列表）
- 段落 3 (14s)：关键实验/结果（用 compareBefore/compareAfter 或 SVG 图表）
- 段落 4 (6s)：结论与启发

## 段落对象格式
```js
{{
  title: "大字金句（≤12字）",
  titleColor: "#2563EB",
  subZh: "中文旁白",
  subEn: "English subtitle",
  body: "补充说明（可选）",
  visualSVG: '<svg viewBox="0 0 120 120">...</svg>',
  steps: ["步骤1", "步骤2"],
  compareBefore: "旧方法",
  compareAfter: "本文方法",
}}
```

## 论文特别要求
- 准确呈现核心贡献、关键术语、方法流程
- 方法框架段用 steps 数组呈现模型流程
- 实验结果段用 compareBefore/compareAfter 做新旧对比
- 公式概念用 SVG 图形表达

## 模板
```html
{template}
```

只输出完整 HTML。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"论文文件名：{filename}\n\n论文内容：\n{paper_text}"},
    ]

    _debug_conversation("openai-compatible", model, messages, settings)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.8,
        )
    except OpenAIError as e:
        log_llm_error("openai-compatible", str(e))
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    _debug_response_start("openai-compatible")
    thought_filter = ThoughtProcessFilter()
    async for chunk in response:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue

        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if not delta:
            continue

        token = getattr(delta, "content", None) or ""
        if not token:
            continue

        visible_token = thought_filter.feed(token)
        if not visible_token:
            continue

        _debug_response_chunk(visible_token)
        payload = json.dumps({"token": visible_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"
        await asyncio.sleep(0.001)

    remaining_token = thought_filter.flush()
    if remaining_token:
        _debug_response_chunk(remaining_token)
        payload = json.dumps({"token": remaining_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"

    _debug_response_end()
    logger.info("论文流式生成完成")
    yield 'data: {"event":"[DONE]"}\n\n'


# ── Two-stage streaming generators ──

async def copy_llm_event_stream(
    topic: str,
    model: str = None,
    settings: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """Stage 1: Generate structured 5-act copy as streaming JSON."""
    settings = settings or {}
    if model is None:
        model = MODEL

    system_prompt = build_copy_system_prompt(topic, settings)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请为以下概念生成五幕文案：{topic}"},
    ]

    _debug_conversation("openai-compatible", model, messages, settings)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.8,
        )
    except OpenAIError as e:
        log_llm_error("openai-compatible", f"copy generation: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    _debug_response_start("openai-compatible")
    thought_filter = ThoughtProcessFilter()
    async for chunk in response:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if not delta:
            continue
        token = getattr(delta, "content", None) or ""
        if not token:
            continue

        visible_token = thought_filter.feed(token)
        if not visible_token:
            continue

        _debug_response_chunk(visible_token)
        payload = json.dumps({"token": visible_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"
        await asyncio.sleep(0.001)

    remaining_token = thought_filter.flush()
    if remaining_token:
        _debug_response_chunk(remaining_token)
        payload = json.dumps({"token": remaining_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"

    _debug_response_end()
    logger.info("文案流式生成完成")
    yield 'data: {"event":"[DONE]"}\n\n'


async def animation_from_copy_llm_event_stream(
    copy_json: Dict[str, Any],
    model: str = None,
    settings: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[str, None]:
    """Stage 2: Generate HTML animation from structured copy."""
    settings = settings or {}
    if model is None:
        model = MODEL

    system_prompt = build_animation_from_copy_system_prompt(copy_json, settings)
    copy_title = copy_json.get("title", "动画")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请根据以上五幕文案生成动画：{copy_title}"},
    ]

    _debug_conversation("openai-compatible", model, messages, settings)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.8,
        )
    except OpenAIError as e:
        log_llm_error("openai-compatible", f"animation-from-copy: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    _debug_response_start("openai-compatible")
    thought_filter = ThoughtProcessFilter()
    async for chunk in response:
        choices = getattr(chunk, "choices", None)
        if not choices:
            continue
        choice = choices[0]
        delta = getattr(choice, "delta", None)
        if not delta:
            continue
        token = getattr(delta, "content", None) or ""
        if not token:
            continue

        visible_token = thought_filter.feed(token)
        if not visible_token:
            continue

        _debug_response_chunk(visible_token)
        payload = json.dumps({"token": visible_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"
        await asyncio.sleep(0.001)

    remaining_token = thought_filter.flush()
    if remaining_token:
        _debug_response_chunk(remaining_token)
        payload = json.dumps({"token": remaining_token}, ensure_ascii=False)
        yield f"data: {payload}\n\n"

    _debug_response_end()
    logger.info("动画（从文案）流式生成完成")
    yield 'data: {"event":"[DONE]"}\n\n'


# -----------------------------------------------------------------------
# 3. 路由 (CHANGED: Now a POST request)
# -----------------------------------------------------------------------
@app.get("/config")
async def get_public_config():
    return {"requiresPassphrase": bool(ACCESS_PASSPHRASES)}


@app.post("/verify-passphrase")
async def verify_passphrase(passphrase_request: PassphraseRequest):
    if ACCESS_PASSPHRASES and passphrase_request.passphrase not in ACCESS_PASSPHRASES:
        logger.warning("暗号验证失败")
        raise HTTPException(status_code=403, detail="暗号错误")
    logger.info("暗号验证通过")
    return {"ok": True}


def build_share_access_page(error_message: str = ""):
    error_html = f'<p class="error">{html.escape(error_message)}</p>' if error_message else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>访问分享动画</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px; font-family: 'MiSans', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif; color: #000; background: linear-gradient(90deg, rgba(0,0,0,.06) 1px, transparent 1px), linear-gradient(0deg, rgba(0,0,0,.06) 1px, transparent 1px), #fff; background-size: 48px 48px; }}
        .card {{ width: min(420px, 100%); padding: 28px; background: #fff; border: 1px solid #000; box-shadow: 12px 12px 0 #000; display: grid; gap: 14px; }}
        p {{ margin: 0; font-size: .72rem; font-weight: 900; letter-spacing: .18em; }}
        h1 {{ margin: 0; font-size: clamp(2rem, 7vw, 4rem); letter-spacing: -.08em; line-height: .95; }}
        input {{ min-height: 52px; border: 1px solid #000; padding: 0 14px; font: inherit; }}
        input:focus, button:focus-visible {{ outline: 2px solid #000; outline-offset: 3px; }}
        button {{ min-height: 50px; border: 1px solid #000; background: #000; color: #fff; font: inherit; font-weight: 900; cursor: pointer; }}
        button:hover {{ background: #fff; color: #000; }}
        .error {{ color: #b10000; letter-spacing: 0; }}
    </style>
</head>
<body>
    <form class="card" method="post">
        <p>SHARED ANIMATION</p>
        <h1>请输入访问密码</h1>
        {error_html}
        <input name="password" type="password" placeholder="访问密码" required autofocus>
        <button type="submit">进入</button>
    </form>
</body>
</html>"""


def create_qr_data_url(value: str):
    image = qrcode.make(value)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_shared_viewer_page(html_content: str, source_width: int, source_height: int):
    safe_width = min(max(source_width, 320), 4096)
    safe_height = min(max(source_height, 320), 4096)
    escaped_srcdoc = html.escape(html_content, quote=True)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>ZSJ-观想录分享</title>
    <style>
        * {{ box-sizing: border-box; }}
        html, body {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: #fff; }}
        body {{ display: grid; place-items: center; font-family: 'MiSans', 'HarmonyOS Sans SC', 'Microsoft YaHei', sans-serif; }}
        .viewer {{ width: min(100vw, calc(100vh * {safe_width} / {safe_height})); height: min(100vh, calc(100vw * {safe_height} / {safe_width})); border: 1px solid #000; background: #111; overflow: hidden; }}
        iframe {{ width: {safe_width}px; height: {safe_height}px; border: 0; display: block; background: #fff; transform: scale(var(--viewer-scale, 1)); transform-origin: top left; }}
        .orientation-prompt {{ position: fixed; inset: 0; z-index: 10; display: none; place-items: center; padding: 24px; background: rgba(255, 255, 255, .94); color: #000; text-align: center; font-weight: 900; }}
        .orientation-prompt.visible {{ display: grid; }}
        .orientation-card {{ display: grid; gap: 16px; max-width: 420px; padding: 24px; border: 1px solid #000; background: #fff; box-shadow: 8px 8px 0 #000; }}
        .orientation-card button {{ min-height: 44px; padding: 0 16px; border: 1px solid #000; background: #000; color: #fff; font: inherit; font-weight: 900; cursor: pointer; }}
    </style>
</head>
<body>
    <main class="viewer"><iframe sandbox="allow-scripts allow-same-origin" srcdoc="{escaped_srcdoc}"></iframe></main>
    <div id="orientation-prompt" class="orientation-prompt">
        <div class="orientation-card">
            <div>移动端适配较差，推荐PC端查看</div>
            <button type="button" id="orientation-dismiss">继续竖屏观看</button>
        </div>
    </div>
    <script>
        (function () {{
            var dismissed = false;
            var prompt = document.getElementById('orientation-prompt');
            var viewer = document.querySelector('.viewer');
            var sourceWidth = {safe_width};
            var sourceHeight = {safe_height};
            document.getElementById('orientation-dismiss').addEventListener('click', function () {{
                dismissed = true;
                prompt.classList.remove('visible');
            }});
            function fitViewer() {{
                var scale = Math.min(viewer.clientWidth / sourceWidth, viewer.clientHeight / sourceHeight);
                viewer.style.setProperty('--viewer-scale', scale.toString());
            }}
            function shouldShowMobilePrompt() {{
                return !dismissed && /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
            }}
            function updatePrompt() {{
                fitViewer();
                prompt.classList.toggle('visible', shouldShowMobilePrompt());
            }}
            window.addEventListener('resize', updatePrompt);
            window.addEventListener('orientationchange', updatePrompt);
            updatePrompt();
        }})();
    </script>
</body>
</html>"""


def get_share_paths(share_id: str):
    return {
        "meta": os.path.join(SHARE_STORAGE_DIR, f"{share_id}.json"),
        "html": os.path.join(SHARE_STORAGE_DIR, f"{share_id}.html"),
    }


def serialize_share_record(record: Dict[str, Any]):
    return {
        "password": record["password"],
        "created_at": record["created_at"].isoformat(),
        "expires_at": record["expires_at"].isoformat() if record["expires_at"] else None,
    }


def parse_share_datetime(value: str):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return shanghai_tz.localize(parsed)
    return parsed.astimezone(shanghai_tz)


def load_share_from_disk(share_id: str):
    paths = get_share_paths(share_id)
    if not os.path.exists(paths["meta"]) or not os.path.exists(paths["html"]):
        return None
    with open(paths["meta"], "r", encoding="utf-8") as file:
        meta = json.load(file)
    with open(paths["html"], "r", encoding="utf-8") as file:
        html_content = file.read()
    record = {
        "html": html_content,
        "password": meta["password"],
        "created_at": parse_share_datetime(meta["created_at"]),
        "expires_at": parse_share_datetime(meta["expires_at"]) if meta.get("expires_at") else None,
    }
    shared_html_links[share_id] = record
    return record


def save_share_to_disk(share_id: str, record: Dict[str, Any]):
    os.makedirs(SHARE_STORAGE_DIR, exist_ok=True)
    paths = get_share_paths(share_id)
    with open(paths["html"], "w", encoding="utf-8") as file:
        file.write(record["html"])
    with open(paths["meta"], "w", encoding="utf-8") as file:
        json.dump(serialize_share_record(record), file, ensure_ascii=False, indent=2)


def delete_share(share_id: str):
    shared_html_links.pop(share_id, None)
    for path in get_share_paths(share_id).values():
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def get_share_record(share_id: str):
    record = shared_html_links.get(share_id) or load_share_from_disk(share_id)
    if not record:
        return None
    if record["expires_at"] and record["expires_at"] <= datetime.now(shanghai_tz):
        delete_share(share_id)
        return None
    return record


def cleanup_expired_shares_once():
    now = datetime.now(shanghai_tz)
    os.makedirs(SHARE_STORAGE_DIR, exist_ok=True)
    for share_id, record in list(shared_html_links.items()):
        if record["expires_at"] and record["expires_at"] <= now:
            delete_share(share_id)
    for filename in os.listdir(SHARE_STORAGE_DIR):
        if not filename.endswith(".json"):
            continue
        share_id = filename[:-5]
        record = load_share_from_disk(share_id)
        if record and record["expires_at"] <= now:
            delete_share(share_id)


async def cleanup_expired_shares_loop():
    while True:
        cleanup_expired_shares_once()
        await asyncio.sleep(SHARE_CLEANUP_INTERVAL_SECONDS)


@app.on_event("startup")
async def start_share_cleanup_task():
    cleanup_expired_shares_once()
    asyncio.create_task(cleanup_expired_shares_loop())
    cleanup_expired_videos_once()
    asyncio.create_task(cleanup_expired_videos_loop())


@app.post("/share")
async def create_share_link(share_request: ShareRequest, request: Request):
    ttl_seconds = SHARE_EXPIRATION_SECONDS.get(share_request.expiresIn)
    if share_request.expiresIn not in SHARE_EXPIRATION_SECONDS:
        raise HTTPException(status_code=400, detail="Invalid expiration")
    if not share_request.html.strip():
        raise HTTPException(status_code=400, detail="HTML content is required")

    # 服务端后处理增强
    try:
        enhanced_html = postprocess_html(share_request.html)
    except Exception:
        logger.exception("HTML 后处理增强失败，使用原始 HTML")
        enhanced_html = share_request.html

    share_id = secrets.token_urlsafe(16)
    created_at = datetime.now(shanghai_tz)
    expires_at = created_at + timedelta(seconds=ttl_seconds) if ttl_seconds else None
    record = {
        "html": build_shared_viewer_page(enhanced_html, share_request.sourceWidth, share_request.sourceHeight),
        "password": share_request.password,
        "created_at": created_at,
        "expires_at": expires_at,
    }
    shared_html_links[share_id] = record
    save_share_to_disk(share_id, record)
    share_url = str(request.url_for("read_shared_html", share_id=share_id))
    logger.info("分享链接已创建 | share_id=%s | expires_in=%s | url=%s",
                share_id, share_request.expiresIn, share_url)
    return {
        "url": share_url,
        "qrCode": create_qr_data_url(share_url),
        "createdAt": created_at.isoformat(),
        "expiresAt": expires_at.isoformat() if expires_at else None,
        "password": share_request.password,
    }


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def read_shared_html(share_id: str):
    shared = get_share_record(share_id)
    if not shared:
        raise HTTPException(status_code=404, detail="Share link expired or not found")
    if shared["password"]:
        return HTMLResponse(build_share_access_page())
    return HTMLResponse(shared["html"])


@app.post("/share/{share_id}", response_class=HTMLResponse)
async def verify_shared_html(share_id: str, request: Request):
    shared = get_share_record(share_id)
    if not shared:
        raise HTTPException(status_code=404, detail="Share link expired or not found")

    body = (await request.body()).decode()
    form = parse_qs(body)
    password = form.get("password", [""])[0]
    if shared["password"] and password != shared["password"]:
        return HTMLResponse(build_share_access_page("访问密码错误"), status_code=403)
    return HTMLResponse(shared["html"])


class LogErrorRequest(BaseModel):
    errors: List[Dict[str, Any]] = []


@app.post("/api/log-error")
async def log_frontend_error(error_request: LogErrorRequest):
    """接收前端上报的错误日志，写入后端日志文件."""
    for err in error_request.errors:
        logger.error(
            "前端错误 | 消息=%s | URL=%s | UA=%s | 时间=%s | 堆栈=%s",
            err.get("message", "unknown")[:300],
            err.get("url", ""),
            err.get("userAgent", "")[:200],
            err.get("timestamp", ""),
            (err.get("stack") or "")[:500],
        )
    return {"ok": True}


@app.post("/generate")
async def generate(
    chat_request: ChatRequest, # CHANGED: Use the Pydantic model
    request: Request,
):
    """
    Main endpoint: POST /generate
    Accepts a JSON body with "topic" and optional "history".
    Returns an SSE stream.
    """
    accumulated_response = ""  # for caching flow results
    queued = generation_semaphore.locked()

    async def event_generator():
        nonlocal accumulated_response
        if queued:
            payload = json.dumps({"event": "queued"}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

        async with generation_semaphore:
            if queued:
                payload = json.dumps({"event": "started"}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            try:
                async for chunk in llm_event_stream(chat_request.topic, chat_request.history, settings=chat_request.settings):
                    accumulated_response += chunk
                    if await request.is_disconnected():
                        logger.info("客户端断开连接（/generate）")
                        break
                    yield chunk
            except Exception as e:
                logger.exception("流式生成异常（/generate）: %s", e)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"


    async def wrapped_stream():
        async for chunk in event_generator():
            yield chunk

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/event-stream; charset=utf-8",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(wrapped_stream(), headers=headers)


@app.post("/paper/generate")
async def generate_paper(
    request: Request,
    pdf: UploadFile = File(...),
    focus: str = Form(""),
    settings: str = Form("{}"),
):
    parsed_settings = parse_settings_form(settings)
    queued = generation_semaphore.locked()

    async def event_generator():
        if queued:
            payload = json.dumps({"event": "queued"}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

        async with generation_semaphore:
            if queued:
                payload = json.dumps({"event": "started"}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            try:
                paper = await extract_pdf_text(pdf)
                async for chunk in paper_llm_event_stream(
                    paper["text"],
                    paper["filename"],
                    focus=focus.strip(),
                    settings=parsed_settings,
                    truncated=paper["truncated"],
                ):
                    if await request.is_disconnected():
                        logger.info("客户端断开连接（/paper/generate）")
                        break
                    yield chunk
            except Exception as e:
                logger.exception("流式生成异常（/paper/generate）: %s", e)
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/event-stream; charset=utf-8",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers)


@app.post("/generate/copy")
async def generate_copy(
    copy_request: CopyRequest,
    request: Request,
):
    """
    Stage 1: Generate structured 5-act copy from a concept.
    Returns an SSE stream of JSON tokens.
    """
    queued = generation_semaphore.locked()

    async def event_generator():
        if queued:
            payload = json.dumps({"event": "queued"}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

        async with generation_semaphore:
            if queued:
                payload = json.dumps({"event": "started"}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            try:
                async for chunk in copy_llm_event_stream(
                    copy_request.topic,
                    settings=copy_request.settings,
                ):
                    if await request.is_disconnected():
                        logger.info("客户端断开连接（/generate/copy）")
                        break
                    yield chunk
            except Exception as e:
                logger.exception("流式生成异常（/generate/copy）: %s", e)
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/event-stream; charset=utf-8",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers)


@app.post("/generate/animation")
async def generate_animation(
    animation_request: AnimationRequest,
    request: Request,
):
    """
    Stage 2: Generate HTML animation from structured copy JSON.
    Returns an SSE stream of HTML tokens.
    """
    queued = generation_semaphore.locked()

    async def event_generator():
        if queued:
            payload = json.dumps({"event": "queued"}, ensure_ascii=False)
            yield f"data: {payload}\n\n"

        async with generation_semaphore:
            if queued:
                payload = json.dumps({"event": "started"}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            try:
                async for chunk in animation_from_copy_llm_event_stream(
                    animation_request.copy_json,
                    settings=animation_request.settings,
                ):
                    if await request.is_disconnected():
                        logger.info("客户端断开连接（/generate/animation）")
                        break
                    yield chunk
            except Exception as e:
                logger.exception("流式生成异常（/generate/animation）: %s", e)
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/event-stream; charset=utf-8",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers)


@app.post("/export/video")
async def export_video(video_request: VideoExportRequest, request: Request):
    """Export an HTML animation page to MP4 video via SSE progress stream."""
    # Resolve HTML content — prefer share_id, fall back to direct html
    html_content = None
    if video_request.share_id:
        record = get_share_record(video_request.share_id)
        if record:
            html_content = record.get("html") or ""
        if not html_content:
            raise HTTPException(status_code=404, detail="Share not found or expired")

    if not html_content and video_request.html:
        html_content = video_request.html

    if not html_content:
        raise HTTPException(status_code=400, detail="Either html or share_id is required")

    # 服务端后处理增强
    try:
        html_content = postprocess_html(html_content)
    except Exception:
        logger.exception("视频导出：HTML 后处理增强失败")

    exporter = get_video_exporter()
    progress_queue: asyncio.Queue = asyncio.Queue()
    queued = export_semaphore.locked()

    async def _push(status: str, percent: float, message: str):
        await progress_queue.put({
            "status": status, "percent": percent, "message": message,
        })

    retention = VIDEO_EXPIRATION_SECONDS.get(
        video_request.expires_in, VIDEO_DEFAULT_RETENTION_SECONDS
    )

    async def _do_export():
        return await exporter.export(
            html=html_content,
            width=video_request.width,
            height=video_request.height,
            fps=video_request.fps,
            duration_hint=video_request.duration_seconds,
            retention_seconds=retention,
            on_progress=_push,
        )

    async def event_generator():
        nonlocal queued

        if queued:
            yield f"data: {json.dumps({'event': 'queued', 'message': '导出任务排队中...'})}\n\n"

        async with export_semaphore:
            if queued:
                yield f"data: {json.dumps({'event': 'started', 'message': '导出任务开始执行'})}\n\n"

            render_task = asyncio.create_task(_do_export())

            while True:
                try:
                    event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if render_task.done():
                        exc = render_task.exception()
                        if exc:
                            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                        break
                    yield "data: {\"event\":\"heartbeat\"}\n\n"
                    continue

                if event["status"] == "complete":
                    try:
                        video_id = render_task.result()
                    except Exception as exc:
                        logger.exception("视频导出任务异常: %s", exc)
                        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                        return
                    logger.info("视频导出完成 | video_id=%s", video_id)
                    yield f"data: {json.dumps({'event': '[DONE]', 'video_id': video_id})}\n\n"
                    return
                elif event["status"] == "error":
                    yield f"data: {json.dumps({'error': event['message']})}\n\n"
                    return
                else:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if await request.is_disconnected():
                    render_task.cancel()
                    break

    headers = {
        "Cache-Control": "no-store",
        "Content-Type": "text/event-stream; charset=utf-8",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers)


@app.get("/video/{video_id}")
async def download_video(video_id: str):
    """Download a rendered MP4 video by ID."""
    exporter = get_video_exporter()
    path = exporter.get_video_path(video_id)
    if not path:
        logger.warning("视频下载失败——未找到 | video_id=%s", video_id)
        raise HTTPException(status_code=404, detail="Video not found or expired")
    meta = exporter.get_metadata(video_id) or {}
    filename = f"animation_{video_id}.mp4"
    logger.info("视频下载 | video_id=%s | file=%s", video_id, filename)
    return FileResponse(path, media_type="video/mp4", filename=filename)


async def cleanup_expired_videos_once():
    exporter = get_video_exporter()
    exporter.cleanup_expired(VIDEO_DEFAULT_RETENTION_SECONDS)


async def cleanup_expired_videos_loop():
    while True:
        cleanup_expired_videos_once()
        await asyncio.sleep(VIDEO_CLEANUP_INTERVAL_SECONDS)


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"time": datetime.now(shanghai_tz).strftime("%Y%m%d%H%M%S")},
    )

# -----------------------------------------------------------------------
# 4. 本地启动命令
# -----------------------------------------------------------------------
# uvicorn app:app --reload --host 0.0.0.0 --port 8000


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
