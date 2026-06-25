# AI Animation Backend — 架构文档

> 一个本地优先的 AI 科普视频生成 Web 应用。输入主题或上传 PDF 论文，模型生成可直接播放的单文件 HTML 动画页面。

---

## 目录

1. [项目概览](#1-项目概览)
2. [目录结构](#2-目录结构)
3. [技术栈](#3-技术栈)
4. [AI 流程架构](#4-ai-流程架构)
5. [LangGraph 图详解](#5-langgraph-图详解)
6. [数据模型](#6-数据模型)
7. [API 路由](#7-api-路由)
8. [SSE 流式协议](#8-sse-流式协议)
9. [设计系统](#9-设计系统)
10. [部署](#10-部署)

---

## 1. 项目概览

### 核心功能

| 功能 | 说明 |
|---|---|
| 主题生成动画 | 输入概念主题 → AI 生成 5 段叙事动画 HTML |
| 论文解读动画 | 上传 PDF 论文 → AI 提炼要点 → 生成科普动画 |
| 两阶段精细生成 | 先生成文案（5 幕叙事）→ 审核后生成动画 |
| 视频导出 | HTML 动画 → Playwright 渲染 → MP4 视频 |
| 分享链接 | 生成的动画生成带密码保护的分享链接 |

### AI 流程对比

| | 旧架构（v1） | 新架构（v2 / LangGraph） |
|---|---|---|
| 调用方式 | 一次巨型 prompt → LLM 直出 JSON | 多步流水线：分析 → 生成 → 校验 → 拼装 → 后处理 |
| 校验 | `json.loads()` + 手动检查 | Pydantic 强校验，精确到字段 |
| 失败处理 | 直接返回错误 | 最多 2 次自动重试，附带具体修正指令 |
| 两阶段流程 | 两次 HTTP 请求，客户端传 JSON | 一次 `/generate/full` 请求，graph 内编排 |
| 论文处理 | 120K 字符直接塞 prompt | 先提炼 outline，后续节点用精简上下文 |
| 代码复用 | 4 个生成器 ~80% 复制粘贴 | 1 个 SSE adapter 三张图共用 |

---

## 2. 目录结构

```
Animation/
├── app.py                         # FastAPI 主应用（路由层）
├── Dockerfile                     # Docker 部署配置
├── requirements.txt               # Python 依赖
├── credentials.json               # 密钥 & 配置（不入 git）
│
├── backend/
│   ├── config.py                  # 全局配置、LLM 客户端、信号量
│   ├── models.py                  # Pydantic 请求/响应/校验模型
│   ├── prompts.py                 # Prompt 构建函数
│   ├── logger.py                  # 统一日志系统（文件轮转 + 控制台彩色）
│   ├── llm_stream.py              # v1 流式生成器（旧，Phase 3 将简化）
│   ├── html_postprocessor.py      # HTML 后处理增强管道
│   ├── share.py                   # 分享链接 CRUD + 清理
│   ├── video_api.py               # 视频导出路由
│   ├── video_exporter.py          # Playwright + HyperFrames 渲染引擎
│   ├── start_guanxianglu.py       # 观向录启动脚本
│   │
│   └── graph/                     # ★ LangGraph v2 架构
│       ├── __init__.py            # ChatOpenAI 延迟实例化 + get_llm()
│       ├── state.py               # AnimationState TypedDict（全局状态）
│       ├── sse_adapter.py         # astream_events → SSE 适配器
│       │
│       ├── nodes/
│       │   ├── plan.py            # 分析节点：analyze_topic / analyze_paper
│       │   ├── generate_copy.py   # 文案生成节点（两阶段图用）
│       │   ├── generate_segments.py # 动画生成节点（三图共用）
│       │   ├── validate.py        # 校验节点：Pydantic 校验 + 重试反馈
│       │   ├── assemble.py        # HTML 拼装节点
│       │   └── postprocess.py     # HTML 后处理节点
│       │
│       ├── edges/
│       │   └── routing.py         # 条件边：校验通过/失败路由
│       │
│       └── graphs/
│           ├── topic_graph.py     # 图 A：主题 → 动画
│           ├── paper_graph.py     # 图 B：论文 → 动画
│           └── two_stage_graph.py # 图 C：主题 → 文案 → 动画（两阶段合并）
│
├── frontend/
│   ├── templates/index.html       # 首页模板
│   └── static/
│       ├── script.js              # 前端逻辑
│       ├── style.css              # 样式
│       ├── animation-template.html # 动画 HTML 骨架模板
│       └── ...
│
└── storage/                       # 运行时数据
    ├── logs/                      # 日志文件
    ├── shared_html/               # 分享的 HTML 文件
    ├── exported_videos/           # 导出的 MP4 视频
    └── temp_render/               # 临时渲染目录
```

---

## 3. 技术栈

| 层次 | 技术 | 说明 |
|---|---|---|
| Web 框架 | FastAPI + Uvicorn | 异步 HTTP + SSE 流式响应 |
| AI 编排 | **LangGraph** | StateGraph 多步流水线 + 条件路由 + 流式事件 |
| LLM 调用 | **langchain-openai** (`ChatOpenAI`) | OpenAI 兼容 API，`streaming=True` + `response_format=json_object` |
| 数据校验 | Pydantic v2 | 请求模型 + **LLM 输出强校验**（`model_validator`） |
| 模板引擎 | Jinja2 | 首页 HTML 渲染 |
| 动画引擎 | **GSAP 3.14** | JavaScript 时间轴动画（CDN 引入） |
| 视频导出 | Playwright + HyperFrames | 无头浏览器渲染 HTML → MP4 |
| PDF 解析 | PyPDF (pypdf) | 提取论文文字 |
| 部署 | Docker | Python 3.10-slim + Node.js 22 + Chromium |

### Python 依赖

```
fastapi                     # Web 框架
uvicorn                     # ASGI 服务器
pydantic                    # 数据校验
openai                      # OpenAI SDK（config.py 中 AsyncOpenAI）
langgraph>=0.2.0            # ★ AI 流程编排
langchain-core>=0.3.0       # ★ LangChain 核心（消息类型等）
langchain-openai>=0.2.0     # ★ ChatOpenAI 封装
jinja2                      # 模板引擎
pytz                        # 时区
qrcode[pil]                 # 二维码生成
python-multipart            # 文件上传
pypdf                       # PDF 解析
playwright>=1.59.0          # 浏览器自动化（视频导出）
requests                    # HTTP 请求
google-genai                # Google Gemini（备用）
```

---

## 4. AI 流程架构

### 4.1 v1 架构（旧，仍可用）

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI 路由                      │
│  /generate          /paper/generate                 │
│  /generate/copy     /generate/animation             │
└──────────┬──────────────────────────────────────────┘
           │ 调用
           ▼
┌─────────────────────────────────────────────────────┐
│              llm_stream.py (4 个生成器)               │
│                                                     │
│  llm_event_stream()                                 │
│  paper_llm_event_stream()                           │
│  copy_llm_event_stream()                            │
│  animation_from_copy_llm_event_stream()             │
│                                                     │
│  每个生成器的流程：                                    │
│  ① 构建巨型 system prompt（含 JSON 格式手写说明）       │
│  ② AsyncOpenAI.chat.completions.create(stream=True) │
│  ③ ThoughtProcessFilter 剥离思考标记                  │
│  ④ 逐 token SSE yield                               │
│  ⑤ json.loads() + _parse_segments_json() 解析       │
│  ⑥ _assemble_animation_html() 拼装                  │
│  ⑦ postprocess_html() 后处理                        │
│  ⑧ 最终 HTML SSE yield                              │
│  ⑨ yield [DONE]                                    │
└─────────────────────────────────────────────────────┘
```

### 4.2 v2 架构（新，LangGraph）

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI 路由                      │
│  /generate/v2      /paper/generate/v2               │
│  /generate/full                                     │
└──────────┬──────────────────────────────────────────┘
           │ 调用 graph + SSE adapter
           ▼
┌─────────────────────────────────────────────────────┐
│              sse_adapter.py                          │
│  stream_graph_to_sse(graph, input_state, request)   │
│                                                     │
│  ① graph.astream_events(input_state, v2)            │
│  ② on_chat_model_stream → SSE token（仅 generate_*）  │
│  ③ on_custom_event:html → SSE 最终 HTML             │
│  ④ yield [DONE]                                    │
└──────────┬──────────────────────────────────────────┘
           │ LangGraph 编排
           ▼
┌─────────────────────────────────────────────────────┐
│                LangGraph StateGraph                  │
│                                                     │
│  多步流水线:                                         │
│  analyze → generate → validate ⇄ retry              │
│           → assemble → postprocess                  │
│                                                     │
│  条件路由:                                           │
│  validate 通过 → assemble                           │
│  validate 失败 → retry（max 2 次）                   │
│  retry 耗尽   → END（返回错误）                      │
└─────────────────────────────────────────────────────┘
```

### 4.3 关键设计决策

| 决策 | 说明 |
|---|---|
| **LLM 只输出 JSON** | `response_format={"type": "json_object"}` 保证合法 JSON |
| **服务端拼装 HTML** | LLM 输出 ~500-1500 token JSON，模板 ~15KB 在服务端填入，彻底避免 LLM 截断 |
| **Pydantic 单一数据源** | 模型定义同时用于：① prompt 格式说明自动生成 ② 结果强校验 ③ 重试反馈 |
| **流式 + 非流式混合** | `generate_*` 节点流式输出 token（前端实时看到）；`analyze_*` 节点非流式（内部规划，前端不可见） |
| **分析节点只流式给 generate 节点** | SSE adapter 根据 `current_node` 名字决定是否转发 token 给前端 |

---

## 5. LangGraph 图详解

### 5.1 图 A：topic_graph（替换 `/generate`）

```
START
  │
  ▼
┌──────────────────┐
│  analyze_topic    │  LLM 小调用（~100 token），非流式
│  输入: topic       │  产出: {category, difficulty, core_idea,
│  产出: outline     │         visual_metaphors, narrative_angle, ...}
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ generate_segments │  LLM 主调用，流式 token 给前端
│  输入: outline     │  response_format={"type":"json_object"}
│        + topic     │  产出: segments_raw（JSON 字符串）
│        + settings  │
│        + feedback  │  ← 重试时注入上次校验失败的修正指令
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│validate_segments  │  Pydantic AnimationOutput 强校验
│  输入: segments_raw│
│  产出: segments    │  通过 → segments 数据 / 失败 → feedback
│        + valid     │
└──┬───────────┬───┘
   │           │
   │ 通过       │ 失败 (retry ≤ 2)
   ▼           ▼
┌────────┐  ┌──────────────────┐
│assemble│  │ generate_segments │  重试（带 validation_feedback）
│ 拼装    │  └──────────────────┘
│ HTML   │
└───┬────┘
    ▼
┌──────────────┐
│ postprocess   │  注入 CSS 变量、GSAP 补丁、字体平滑
│  输出: html   │  通过 custom event 发送最终 HTML 给 SSE adapter
└──────┬───────┘
       ▼
      END
```

**特点**：
- `analyze_topic` 是额外的规划步骤，帮助后续 prompt 更聚焦
- `generate_segments` 同时支持 topic 模式和 paper 模式（通过 `state.pdf_text` 判断）
- 校验失败最多重试 2 次，每次注入具体错误信息

### 5.2 图 B：paper_graph（替换 `/paper/generate`）

```
START
  │
  ▼
┌──────────────────┐
│  analyze_paper    │  LLM 调用，非流式
│  输入: pdf_text    │  将最长 120K 字符的论文提炼为 ~300 字 outline
│        + focus     │  产出: {paper_summary, core_idea, method_highlights,
│  产出: outline     │         key_result, visual_metaphors, ...}
└──────┬───────────┘
       │
       ▼
    （后续节点与 topic_graph 完全相同）
       │
       ▼
generate_segments → validate_segments ⇄ assemble → postprocess → END
```

**特点**：
- `analyze_paper` 是核心价值节点——将论文全文提炼后再生成，大幅提升质量
- 后续 `generate_segments` 不再直接读论文原文，而是用精简的 outline
- 支撑最高 20MB PDF 上传 / 120K 字符提取

### 5.3 图 C：two_stage_graph（替换 `/generate/copy` + `/generate/animation`）

```
START
  │
  ▼
┌──────────────────┐
│  analyze_topic    │  同上
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  generate_copy    │  生成 5 幕叙事文案，流式 token 给前端
│  输入: outline     │  复用现有 build_copy_system_prompt()
│        + topic     │  response_format={"type":"json_object"}
│  产出: copy_json   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  validate_copy    │  Pydantic CopySchema 校验
│  输入: copy_json   │
│  产出: copy_valid  │  通过 → 进入 generate_animation
└──┬───────────┬───┘   失败 → 重试 generate_copy (max 2)
   │           │
   │ 通过       │ 失败 (retry ≤ 2)
   ▼           ▼
┌────────────┐  ┌──────────────┐
│ generate_   │  │ generate_copy│  重试
│ animation   │  └──────────────┘
└──────┬─────┘
       │
       ▼
┌──────────────────┐
│validate_animation │  复用 validate_segments
└──┬───────────┬───┘
   │           │
   │ 通过       │ 失败 → 重试 generate_animation (max 2)
   ▼           ▼
assemble → postprocess → END
```

**特点**：
- **两层独立的 retry 循环**：文案重试不影响动画，动画重试不影响文案
- 原来需要两次 HTTP 请求 + 客户端传递 JSON，现在一次 `/generate/full` 完成
- 文案和动画的 token 都会流式输出给前端（两个阶段各自流式）

### 5.4 节点职责速查

| 节点 | 文件 | LLM 调用 | 流式给前端 | 说明 |
|---|---|---|---|---|
| `analyze_topic` | `nodes/plan.py` | ✅ (ainvoke) | ❌ | 分析主题 → ~100 token outline |
| `analyze_paper` | `nodes/plan.py` | ✅ (ainvoke) | ❌ | 提炼论文 → ~300 字 outline |
| `generate_copy` | `nodes/generate_copy.py` | ✅ (astream) | ✅ | 生成 5 幕文案 JSON |
| `generate_segments` | `nodes/generate_segments.py` | ✅ (astream) | ✅ | 主题/论文 → 5 段 JSON |
| `generate_animation` | `nodes/generate_segments.py` | ✅ (astream) | ✅ | 文案 → 5 段 JSON |
| `validate_copy` | `nodes/validate.py` | ❌ | ❌ | Pydantic CopySchema 校验 |
| `validate_segments` | `nodes/validate.py` | ❌ | ❌ | Pydantic AnimationOutput 校验 |
| `assemble` | `nodes/assemble.py` | ❌ | ❌ | JSON → HTML 模板 |
| `postprocess` | `nodes/postprocess.py` | ❌ | ✅ (custom event) | 注入 CSS/GSAP → 发送最终 HTML |

---

## 6. 数据模型

### 6.1 AnimationState（LangGraph 全局状态）

```python
class AnimationState(TypedDict, total=False):
    # ── 输入 ──
    topic: str                          # 用户主题
    settings: dict                      # 风格/时长/画幅/深度等
    history: list[dict]                 # 多轮对话历史

    # ── PDF 输入 ──
    pdf_filename: str
    pdf_text: str                       # 已提取的论文全文
    pdf_truncated: bool
    focus: str

    # ── 中间产物 ──
    outline: dict                       # 主题/论文分析结果
    copy_json: dict                     # 5 幕文案
    segments_raw: str                   # LLM 原始 JSON 输出
    segments: list[dict]                # Pydantic 校验后的 5 段数据
    seg_durations: list[int]

    # ── 最终产物 ──
    html: str                           # 完整动画 HTML

    # ── 控制字段 ──
    error: str
    validation_feedback: str            # 校验失败时的修正指令
    retry_count: int
    max_retries: int                    # 默认 2
    copy_valid: bool
    segments_valid: bool
```

### 6.2 LLM 输出校验模型

```python
class AnimationSegment(BaseModel):
    """单个动画段落的 schema——同时用于 prompt 生成和结果校验"""
    title: str                          # 必填，≤12字
    titleColor: str                     # 必填，hex 颜色 #RRGGBB
    subZh: str                          # 必填，中文旁白
    subEn: str = ""                     # 英文字幕
    body: str = ""                      # 补充说明
    bigNum: str | None = None           # 大号数字
    visualSVG: str | None = None        # SVG 图形
    steps: list[str] | None = None      # 步骤列表（段2）
    compareBefore: str | None = None    # 对比前（段3）
    compareAfter: str | None = None     # 对比后（段3）
    compareLabelBefore: str | None = None
    compareLabelAfter: str | None = None

    @model_validator(mode="after")
    def mutually_exclusive_visual(self):
        """visualSVG / steps / compareBefore 互斥"""
        ...

class AnimationOutput(BaseModel):
    """LLM 输出的顶层结构"""
    segments: list[AnimationSegment]    # 恰好 5 个元素
```

### 6.3 请求模型

```python
class ChatRequest(BaseModel):
    topic: str
    history: Optional[List[dict]] = None
    settings: Optional[Dict[str, Any]] = None

class CopyRequest(BaseModel):
    topic: str
    settings: Optional[Dict[str, Any]] = None

class AnimationRequest(BaseModel):
    copy_json: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None
```

---

## 7. API 路由

### 7.1 路由总览

| 方法 | 路由 | 版本 | 说明 |
|---|---|---|---|
| GET | `/` | — | 首页 |
| GET | `/config` | — | 公开配置（是否需要暗号） |
| POST | `/verify-passphrase` | — | 暗号验证 |
| POST | `/share` | — | 创建分享链接 |
| GET | `/share/{id}` | — | 查看分享 |
| POST | `/share/{id}` | — | 密码验证分享 |
| POST | `/api/log-error` | — | 前端错误日志上报 |
| **POST** | **`/generate`** | v1 | 主题 → 动画 |
| **POST** | **`/generate/v2`** | **v2** | **主题 → 动画（LangGraph）** |
| POST | `/paper/generate` | v1 | 论文 → 动画 |
| **POST** | **`/paper/generate/v2`** | **v2** | **论文 → 动画（LangGraph）** |
| POST | `/generate/copy` | v1 | 主题 → 文案 |
| POST | `/generate/animation` | v1 | 文案 → 动画 |
| **POST** | **`/generate/full`** | **v2** | **主题 → 文案 → 动画，一次完成** |
| POST | `/export/video` | — | HTML → MP4 视频导出 |
| GET | `/video/{id}` | — | 下载导出视频 |

### 7.2 新路由详解

#### POST `/generate/v2`

```json
// 请求体
{
  "topic": "量子纠缠",
  "settings": {
    "style": "cinematic",
    "duration": "medium",
    "ratio": "16:9",
    "depth": "standard",
    "resolution": "1080p",
    "bilingual": true,
    "narration": true
  },
  "history": []
}

// SSE 响应流
data: {"token":"{"}          // ← generate_segments 的 LLM token
data: {"token":"\"segments"}
data: {"token":"\":["}
// ... JSON token 流 ...
data: {"token":"\n\n<html>..."}  // ← 拼装完成的完整 HTML
data: {"event":"[DONE]"}
```

#### POST `/paper/generate/v2`

```
// multipart/form-data
pdf: <file>
focus: "第二章方法论"
settings: '{"style":"academic","duration":"medium","depth":"expert"}'

// SSE 响应流（同 /generate/v2）
```

#### POST `/generate/full`

```json
// 请求体
{
  "topic": "量子纠缠",
  "settings": {
    "style": "cinematic",
    "duration": "medium"
  }
}

// SSE 响应流（两阶段）
data: {"token":"{"}          // ← Stage 1: generate_copy 的 JSON token
// ... 文案 JSON token 流 ...
data: {"token":"{"}          // ← Stage 2: generate_animation 的 JSON token
// ... 动画 JSON token 流 ...
data: {"token":"\n\n<html>..."}  // ← 最终 HTML
data: {"event":"[DONE]"}
```

---

## 8. SSE 流式协议

前端与后端的 SSE 通信协议保持不变（v1 和 v2 完全兼容）：

### 事件类型

| 事件 | 格式 | 说明 |
|---|---|---|
| 排队 | `{"event":"queued"}` | 任务在信号量队列中等待 |
| 开始 | `{"event":"started"}` | 信号量获取成功，开始生成 |
| Token | `{"token":"..."}` | LLM 流式输出的单个文本 token |
| 最终 HTML | `{"token":"\n\n<html>..."}` | 拼装完成的完整动画 HTML |
| 错误 | `{"error":"..."}` | 生成失败的错误信息 |
| 结束 | `{"event":"[DONE]"}` | 流结束标记 |

### v2 的关键行为

- 只有 `generate_*` 节点的 LLM token 才会流式给前端
- `analyze_*` 节点的 LLM 调用是内部的，前端不可见
- `validate` / `assemble` 节点不产生 token 输出
- `postprocess` 节点通过 LangGraph custom event 发送最终 HTML
- 前端不需要任何改动即可使用 v2 路由

---

## 9. 设计系统

### 9.1 CSS 变量体系

```css
:root {
  --color-danger:    #DC2626;   /* 危机/问题/警告 */
  --color-mystery:   #7C3AED;   /* 悬念/疑问/未知 */
  --color-reveal:    #2563EB;   /* 揭示/解释/逻辑 */
  --color-insight:   #059669;   /* 顿悟/答案/真相 */
  --color-memory:    #D97706;   /* 金句/记忆/总结 */
  --color-bg:        #FAFBFC;
  --color-text:      #0F172A;
  --color-text-dim:  #64748B;

  --font-display: 'MiSans', 'PingFang SC', sans-serif;
  --fs-hero:       clamp(3.5rem, 8vw, 7rem);
  --fs-headline:   clamp(2rem, 5vw, 4rem);
  --fs-body:       1.25rem;
  --fs-subtitle:   1.05rem;

  --ease-smooth:     cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out-back:   cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-spring:     cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

### 9.2 5 段叙事结构

| 段 | 名称 | 时长 | 视觉元素 | 颜色 |
|---|---|---|---|---|
| 0 | 认知爆破 | 6-8s | visualSVG | #DC2626 |
| 1 | 悬念铺垫 | 10-12s | visualSVG | #7C3AED |
| 2 | 层层揭秘 | 20-22s | steps 数组 | #2563EB |
| 3 | 高潮揭晓 | 14s | compareBefore/After | #059669 |
| 4 | 金句收尾 | 6-8s | visualSVG | #D97706 |

### 9.3 HTML 后处理注入

`backend/html_postprocessor.py` 对 LLM 生成的 HTML 自动注入：

| 检测项 | 缺失时自动注入 |
|---|---|
| CSS 变量 `--color-*` | 注入完整设计系统 |
| 字体平滑 `-webkit-font-smoothing` | 注入抗锯齿 |
| 噪点纹理 `<feTurbulence>` | 注入 SVG 噪点背景 |
| GSAP timeline 注册 | 注入 `window.__timelines` 自动收集 |
| viewport meta | 注入 `<meta viewport>` |
| 闭合标签截断 | 自动补全 `</body></html>` |

---

## 10. 部署

### 10.1 Docker

```bash
# 构建
docker build -t animation-app .

# 运行
docker run -p 8000:8000 \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/storage:/app/storage \
  animation-app
```

### 10.2 Dockerfile 结构

```dockerfile
FROM python:3.10-slim
WORKDIR /app

# 系统依赖：FFmpeg + Node.js 22 + Chromium 共享库
RUN apt-get install ffmpeg nodejs chromium-libs

# Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# Playwright Chromium
RUN python -m playwright install chromium --with-deps

# HyperFrames（加速视频首次渲染）
RUN npm install -g hyperframes@0.6.121

# 应用代码
COPY . .
RUN mkdir -p storage/exported_videos storage/temp_render storage/logs storage/shared_html

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.3 credentials.json 配置

```json
{
  "API_KEY": "sk-your-api-key",
  "BASE_URL": "https://api.openai.com/v1",
  "MODEL": "gpt-4o",
  "ENABLE_DEBUG_OUTPUT": true,
  "LOG_LEVEL": "INFO",
  "MAX_CONCURRENT_GENERATION_TASKS": 2,
  "MAX_CONCURRENT_EXPORT_TASKS": 1,
  "MAX_PAPER_UPLOAD_BYTES": 20971520,
  "MAX_PAPER_TEXT_CHARS": 120000,
  "ACCESS_PASSPHRASES": null
}
```

| 字段 | 说明 |
|---|---|
| `API_KEY` | OpenAI 兼容 API 密钥 |
| `BASE_URL` | API 端点地址 |
| `MODEL` | 模型名称 |
| `ENABLE_DEBUG_OUTPUT` | 是否在控制台打印 LLM 请求/响应 |
| `LOG_LEVEL` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `MAX_CONCURRENT_GENERATION_TASKS` | 最大并发生成数 |
| `MAX_PAPER_UPLOAD_BYTES` | PDF 上传大小限制（默认 20MB） |
| `MAX_PAPER_TEXT_CHARS` | PDF 提取文字上限（默认 120K） |
| `ACCESS_PASSPHRASES` | 访问暗号列表，null 则无需暗号 |

---

## 附录

### A. 迁移路线图

| 阶段 | 内容 | 风险 |
|---|---|---|
| **Phase 1** ✅ | 新建 `backend/graph/`、新增 3 条 v2 路由、旧路由保留 | 零风险，新旧并行 |
| **Phase 2** | 前端切到 v2 路由，观察一周 | 低风险，可随时回滚 |
| **Phase 3** | 删除旧路由、删除 `llm_stream.py` 中的旧生成器、简化 `prompts.py` | 清理性改动 |

### B. 关键文件依赖关系

```
app.py
  ├── config.py         ← 凭证、信号量、LLM 客户端
  ├── models.py         ← 请求模型 + LLM 输出校验模型
  ├── prompts.py        ← Prompt 构建函数
  ├── llm_stream.py     ← v1 生成器 + extract_pdf_text
  ├── share.py          ← 分享逻辑
  ├── video_api.py      ← 视频导出
  ├── html_postprocessor.py ← HTML 后处理
  └── graph/            ← ★ v2 LangGraph 架构
      ├── __init__.py   ← ChatOpenAI(get_llm)
      ├── state.py      ← AnimationState
      ├── sse_adapter.py ← stream_graph_to_sse
      ├── nodes/        ← 7 个节点
      ├── edges/        ← 条件路由
      └── graphs/       ← 3 张 StateGraph
```

### C. 5 段数据字段互斥规则

每个段（segment）只能使用以下三种可视化类型之一：

| 字段 | 适用段 | 说明 |
|---|---|---|
| `visualSVG` | 0, 1, 4 | SVG 图形（开场冲击、悬念铺垫、金句收尾） |
| `steps` | 2 | 字符串数组（层层揭秘的步骤列表） |
| `compareBefore/After` | 3 | 新旧对比（高潮揭晓的认知翻转） |

此规则由 Pydantic `@model_validator` 在 `AnimationSegment` 中强制执行。
