# ZSJ-观想录 — 项目全面报告

> **生成日期**：2026-06-24  
> **项目版本**：v2.0.0（代码中）/ v0.1.3（最近 commit）  
> **Git 分支**：main  
> **工作区状态**：有大量未提交的重构改动（16 个文件，+408 / -10797 行）

---

## 目录

1. [项目定义](#1-项目定义)
2. [当前状态摘要](#2-当前状态摘要)
3. [技术架构全览](#3-技术架构全览)
4. [AI 流程架构](#4-ai-流程架构)
5. [LangGraph 图详解](#5-langgraph-图详解)
6. [数据模型](#6-数据模型)
7. [API 路由表](#7-api-路由表)
8. [SSE 流式协议](#8-sse-流式协议)
9. [设计系统](#9-设计系统)
10. [前端架构](#10-前端架构)
11. [视频导出引擎](#11-视频导出引擎)
12. [部署配置](#12-部署配置)
13. [项目文件清单](#13-项目文件清单)
14. [架构质量评估](#14-架构质量评估)
15. [已知问题与风险](#15-已知问题与风险)
16. [迁移进度](#16-迁移进度)

---

## 1. 项目定义

### 1.1 一句话描述

**把一个概念或一篇论文，变成一段可以播放的知识动画。**

### 1.2 核心价值

| 维度 | 说明 |
|---|---|
| **输入** | 自然语言主题（如"量子纠缠"）/ PDF 学术论文 |
| **输出** | 单文件 HTML 动画页面（可直接播放、分享、导出 MP4） |
| **受众** | 科普创作者、教师、研究人员、短视频制作者 |
| **定位** | 本地优先的 AI 科普视频生成工具 |

### 1.3 产品功能矩阵

| 功能 | 状态 | 说明 |
|---|---|---|
| 主题 → 动画 | ✅ 可用 | 输入概念，LangGraph 流水线生成 5 段动画 HTML |
| 论文 → 动画 | ✅ 可用 | 上传 PDF，先提炼再生成科普动画 |
| 两阶段精细生成 | ✅ 可用 | 先生成文案 → 审核 → 生成动画，单次 API 调用 |
| 文案独立生成 | ✅ 可用 | 只生成 5 幕叙事文案，不生成动画 |
| 文案 → 动画 | ✅ 可用 | 基于已有文案生成动画 |
| 视频导出 (MP4) | ✅ 可用 | HTML → Playwright/HyperFrames → MP4 |
| 分享链接 | ✅ 可用 | 带密码保护 + 过期时间的分享 |
| 多轮修改 | ✅ 可用 | 基于历史上下文迭代修改 |
| 暗号访问控制 | ✅ 可用 | 可选的入口鉴权 |
| 多语言界面 | ✅ 可用 | 中/英双语切换 |

---

## 2. 当前状态摘要

### 2.1 正在进行的重构

项目处于 **v1 → v2 架构迁移** 的中间阶段：

- **路由层已切到 LangGraph v2**：`app.py` 的 `/generate`、`/paper/generate`、`/generate/full` 等路由均已使用编译后的 LangGraph state graph
- **旧代码已物理移动**：原来的 `html_postprocessor.py`、`logger.py`、`video_exporter.py`、`start_guanxianglu.py` 已从根目录移至 `backend/` 目录
- **前端资产已重组**：`static/` 和 `templates/` 移至 `frontend/` 目录
- **旧文件未删除干净**：git status 显示旧位置的 7 个文件被标记为已删除（D），但尚未提交
- **5 张 LangGraph 图已全部实现**：topic_graph、paper_graph、two_stage_graph、copy_graph、animation_graph

### 2.2 未提交的改动量

```
16 files changed:
  408 insertions
  10797 deletions  (净删约 10,000 行)
```

改动集中在：
- `app.py` — 从 ~1900 行精简为 ~493 行（删除了内联的旧版生成器逻辑）
- 旧文件移至 `backend/` 子包
- `README.md` — 大幅重写
- `Dockerfile` — 优化
- `requirements.txt` — 新增 langgraph/langchain 依赖

---

## 3. 技术架构全览

### 3.1 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  Jinja2 Template (index.html)                                │
│  + script.js (SSE 消费 / UI 交互)                            │
│  + style.css (设计系统 / 布局)                                │
│  + animation-template.html (动画 HTML 骨架)                   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP / SSE
┌────────────────────▼────────────────────────────────────────┐
│                      FastAPI (app.py)                         │
│  - 路由注册 (7 个 AI 生成路由 + 分享 + 视频导出)               │
│  - 中间件 (CORS / HTTP 请求日志)                              │
│  - 信号量并发控制 (生成 / 导出)                                │
│  - 启动清理任务                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│               Backend 业务层                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ config.py     │ │ models.py    │ │ prompts.py           │ │
│  │ 凭证/信号量   │ │ Pydantic模型 │ │ Prompt 构建函数      │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ share.py      │ │ video_api.py │ │ llm_stream.py        │ │
│  │ 分享CRUD+清理 │ │ 视频导出路由 │ │ PDF文本提取          │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │ html_post-    │ │ video_       │ │ thought_filter.py    │ │
│  │ processor.py  │ │ exporter.py  │ │ DeepSeek思考过滤     │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
│  ┌──────────────┐ ┌──────────────────────────────────────┐ │
│  │ logger.py     │ │ 统一日志(文件轮转+控制台彩色)         │ │
│  └──────────────┘ └──────────────────────────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Backend LangGraph AI 编排层                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ graph/__init__.py  → ChatOpenAI 延迟实例化            │   │
│  │ graph/state.py     → AnimationState TypedDict        │   │
│  │ graph/sse_adapter.py → astream_events → SSE 适配     │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ graph/nodes/                                          │   │
│  │   plan.py          → analyze_topic / analyze_paper   │   │
│  │   generate_copy.py → 5幕文案生成                      │   │
│  │   generate_segments.py → 5段视觉内容生成              │   │
│  │   validate.py      → Pydantic 校验 + 重试反馈        │   │
│  │   assemble.py      → JSON → HTML模板拼装             │   │
│  │   postprocess.py   → HTML后处理增强                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ graph/edges/                                          │   │
│  │   routing.py       → 条件路由决策                    │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ graph/graphs/                                         │   │
│  │   topic_graph.py   → 主题→动画                        │   │
│  │   paper_graph.py   → 论文→动画                        │   │
│  │   two_stage_graph.py → 主题→文案→动画(合并)           │   │
│  │   copy_graph.py    → 主题→文案                        │   │
│  │   animation_graph.py → 文案→动画                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 技术栈明细

| 层次 | 技术 | 版本要求 | 用途 |
|---|---|---|---|
| **Web 框架** | FastAPI | latest | 异步 HTTP + SSE 流式响应 |
| **ASGI 服务器** | Uvicorn | latest | 生产级 ASGI 服务 |
| **AI 编排** | LangGraph | ≥0.2.0 | StateGraph 多步流水线 + 条件路由 |
| **LLM 客户端** | langchain-openai (ChatOpenAI) | ≥0.2.0 | OpenAI 兼容 API 调用 |
| **LLM 核心** | langchain-core | ≥0.3.0 | 消息类型、工具定义 |
| **LLM SDK** | openai | latest | AsyncOpenAI 直调（备用） |
| **数据校验** | Pydantic | v2 | 请求模型 + LLM 输出强校验 |
| **模板引擎** | Jinja2 | latest | 首页 HTML 渲染 |
| **动画引擎** | GSAP | 3.12.2 / 3.14.2 | JavaScript 时间轴动画 |
| **PDF 解析** | pypdf | latest | 提取论文文字 |
| **视频导出** | Playwright | ≥1.59.0 | 无头浏览器录制 |
| **视频渲染** | HyperFrames | 0.6.121 | 确定性视频渲染（可选） |
| **视频转码** | FFmpeg | system | WebM → MP4 转码 |
| **二维码** | qrcode[pil] | latest | 分享链接二维码 |
| **时区处理** | pytz | latest | Asia/Shanghai 时区 |
| **文件上传** | python-multipart | latest | PDF 文件上传 |
| **HTTP 客户端** | requests | latest | 健康检查等 |
| **前端** | 原生 HTML/CSS/JS | — | 零框架，零构建步骤 |
| **容器化** | Docker | — | Python 3.10-slim + Node.js 22 + Chromium |

### 3.3 外部依赖

| 依赖 | 来源 | 说明 |
|---|---|---|
| GSAP | cdnjs.cloudflare.com | 动画引擎 CDN |
| MiSans 字体 | font.sec.miui.com | 小米免费商用字体 |
| Node.js 22 | mirrors.aliyun.com | Docker 构建时下载 |
| Debian 源 | mirrors.aliyun.com | Docker 内 apt 源 |

---

## 4. AI 流程架构

### 4.1 v1 架构（旧，代码已从 app.py 移除但保留在 llm_stream.py）

```
用户请求 → 单次巨型 prompt → LLM 流式返回 JSON → json.loads() 解析
         → 手动校验 → 模板拼装 → HTML 后处理 → SSE 返回
```

**问题**：
- 一次巨型 prompt，LLM 容易输出不稳定
- 校验依赖 `json.loads()` + 手动检查，不精确
- 论文全文直接塞 prompt（最长 120K 字符），质量不可控
- 4 个生成器 ~80% 代码重复
- 重试逻辑和生成逻辑耦合

### 4.2 v2 架构（新，LangGraph）

```
用户请求 → analyze (小调用, ~100 token, 非流式)
         → generate (主调用, 流式, response_format=json_object)
         → validate (Pydantic 强校验)
         → 通过 → assemble (服务端模板拼装) → postprocess → SSE 返回
         → 失败 → 注入修正指令 → 重试 generate (max 2次)
```

**优势**：
| 改进点 | v1 | v2 |
|---|---|---|
| 调用方式 | 一次巨型 prompt | 多步流水线 |
| 校验 | `json.loads()` + 手动 | Pydantic v2 强校验 |
| 失败处理 | 直接返回错误 | 最多 2 次自动重试，附带精确修正指令 |
| 论文处理 | 120K 字符直塞 | 先提炼为 ~300 字 outline |
| 代码复用 | 4 个生成器 ~80% 重复 | 1 个 SSE adapter + 共享 nodes |
| 两阶段流程 | 两次 HTTP 请求 | 单次 `/generate/full` 请求 |
| Token 可见性 | 所有输出对用户可见 | 分析节点内部，只流式 generate 节点 |

### 4.3 关键设计决策

| 决策 | 说明 |
|---|---|
| **LLM 只输出 JSON** | `response_format={"type": "json_object"}` 保证合法 JSON，服务端拼装 ~15KB HTML 模板 |
| **Pydantic 单一数据源** | 模型定义同时用于：① prompt 格式说明自动生成 ② 结果强校验 ③ 重试反馈生成 |
| **流式 + 非流式混合** | `generate_*` 节点流式（前端实时看到），`analyze_*` 非流式（内部规划） |
| **ThoughtProcessFilter** | 流式剥离 DeepSeek R1 等模型的 `<think>...</think>` 标签 |
| **信号量并发控制** | `generation_semaphore` 和 `export_semaphore` 限制并发数 |

---

## 5. LangGraph 图详解

### 5.1 总览

项目共编译 5 张 StateGraph，全部在 `app.py` 启动时编译一次，全局复用：

| # | 图名 | 路由 | 节点数 | 流程 |
|---|---|---|---|---|
| A | `topic_graph` | `/generate` | 5 | analyze_topic → generate_segments ⇄ validate → assemble → postprocess |
| B | `paper_graph` | `/paper/generate` | 5 | analyze_paper → generate_segments ⇄ validate → assemble → postprocess |
| C | `two_stage_graph` | `/generate/full` | 7 | analyze_topic → generate_copy ⇄ validate → generate_animation ⇄ validate → assemble → postprocess |
| D | `copy_graph` | `/generate/copy` | 3 | analyze_topic → generate_copy ⇄ validate → END |
| E | `animation_graph` | `/generate/animation` | 4 | generate_animation ⇄ validate → assemble → postprocess |

### 5.2 图 A：topic_graph

```
START → analyze_topic → generate_segments → validate_segments
                ↑              ↓ 失败 (retry ≤ 2)
                └──────────────┘
                       ↓ 通过
                   assemble → postprocess → END
```

- `analyze_topic` 探索主题产出 `{category, difficulty, core_idea, visual_metaphors, narrative_angle}`
- `generate_segments` 生成 5 段视觉内容 JSON，token 流式给前端
- `validate_segments` 用 `AnimationOutput` Pydantic 模型校验
- 失败时生成精确到字段的修正指令，注入下一次 prompt

### 5.3 图 B：paper_graph

```
START → analyze_paper → generate_segments → validate_segments
                ↑               ↓ 失败 (retry ≤ 2)
                └───────────────┘
                       ↓ 通过
                   assemble → postprocess → END
```

- `analyze_paper` 是核心价值节点：将最长 120K 字符论文提炼为精简 outline
- 后续 `generate_segments` 不再直接读论文原文，而是使用提炼后的上下文

### 5.4 图 C：two_stage_graph

```
START → analyze_topic → generate_copy → validate_copy
                ↑              ↓ 失败 (retry ≤ 2)
                └──────────────┘
                       ↓ 通过
                  generate_animation → validate_animation
                ↑                           ↓ 失败 (retry ≤ 2)
                └───────────────────────────┘
                       ↓ 通过
                   assemble → postprocess → END
```

- **两层独立的 retry 循环**：文案重试不影响动画，动画重试不影响文案
- 原来需要两次 HTTP 请求 + 客户端传递 JSON，现在一次请求完成

### 5.5 节点职责速查

| 节点 | 文件 | 调用 LLM | 流式给前端 | 说明 |
|---|---|---|---|---|
| `analyze_topic` | `nodes/plan.py` | ✅ `ainvoke` | ❌ | 分析主题 → ~100 token outline |
| `analyze_paper` | `nodes/plan.py` | ✅ `ainvoke` | ❌ | 提炼论文 → ~300 字 outline |
| `generate_copy` | `nodes/generate_copy.py` | ✅ `astream` | ✅ | 生成 5 幕文案 JSON |
| `generate_segments` | `nodes/generate_segments.py` | ✅ `astream` | ✅ | 主题/论文 → 5 段 JSON |
| `generate_animation` | `nodes/generate_segments.py` | ✅ `astream` | ✅ | 文案 → 5 段 JSON |
| `validate_copy` | `nodes/validate.py` | ❌ | ❌ | Pydantic `CopySchema` 校验 |
| `validate_segments` | `nodes/validate.py` | ❌ | ❌ | Pydantic `AnimationOutput` 校验 |
| `assemble` | `nodes/assemble.py` | ❌ | ❌ | JSON → HTML 模板 |
| `postprocess` | `nodes/postprocess.py` | ❌ | ✅ (custom event) | 注入 CSS/GSAP → 最终 HTML |

### 5.6 条件路由逻辑 (`edges/routing.py`)

```python
def after_validate_segments(state):
    if segments_valid → "assemble"
    elif retry_count ≤ max_retries → "generate_segments"  # 重试
    else → "__end__"  # 终止
```

---

## 6. 数据模型

### 6.1 AnimationState（全局状态）

```python
class AnimationState(TypedDict, total=False):
    # 输入
    topic: str
    settings: dict          # {style, duration, ratio, depth, resolution, ...}
    history: list[dict]     # 多轮对话

    # PDF 输入
    pdf_filename: str
    pdf_text: str           # 已提取的论文全文
    pdf_truncated: bool
    focus: str              # 用户指定重点

    # 中间产物
    outline: dict           # 主题/论文分析结果
    copy_json: dict         # 5 幕文案
    segments_raw: str       # LLM 原始 JSON 输出
    segments: list[dict]    # Pydantic 校验后的 5 段数据
    seg_durations: list[int]

    # 最终产物
    html: str               # 完整动画 HTML

    # 控制字段
    error: str
    validation_feedback: str
    retry_count: int
    max_retries: int        # 默认 2
    copy_valid: bool
    segments_valid: bool
```

### 6.2 LLM 输出校验模型

```python
class AnimationSegment(BaseModel):
    title: str                          # 必填，≤12字
    titleColor: str                     # 必填，hex #RRGGBB
    subZh: str                          # 必填，中文旁白
    subEn: str = ""                     # 英文字幕
    body: str = ""                      # 补充说明
    bigNum: str | None = None           # 大号数字
    visualSVG: str | None = None        # SVG 图形
    steps: list[str] | None = None      # 步骤列表（段2专用）
    compareBefore: str | None = None    # 对比前（段3专用）
    compareAfter: str | None = None     # 对比后（段3专用）
    compareLabelBefore: str | None = None
    compareLabelAfter: str | None = None

    @model_validator(mode="after")
    def mutually_exclusive_visual(self):
        # visualSVG / steps / compareBefore 互斥
        ...

class AnimationOutput(BaseModel):
    segments: list[AnimationSegment]    # 恰好 5 个元素
```

### 6.3 文案校验模型

```python
class CopyAct(BaseModel):
    act: int
    name: str
    goal: str
    duration_hint: int
    method_used: str
    narration: str
    narration_en: str = ""
    visual_description: str           # 6维度：构图/颜色/图形/动效/镜头/SVG
    on_screen_text: str = ""

class CopySchema(BaseModel):
    narrative_type: str = "problem_conflict"
    title: str
    visual_style: str = "cinematic"
    color_palette: str = ""
    total_duration_hint: int = 60
    acts: List[CopyAct] = []
```

### 6.4 请求模型

```python
class ChatRequest(BaseModel):
    topic: str
    history: Optional[List[dict]] = None
    settings: Optional[Dict[str, Any]] = None

class ShareRequest(BaseModel):
    html: str
    expiresIn: str          # "1h"|"3h"|"6h"|"8h"|"1d"|"3d"|"7d"|"forever"
    password: str           # 4-20位数字
    sourceWidth: int = 1920
    sourceHeight: int = 1080

class VideoExportRequest(BaseModel):
    html: Optional[str] = None           # max 5MB
    share_id: Optional[str] = None
    width: int = 1920                    # 640-4096
    height: int = 1080                   # 360-4096
    fps: int = 24                        # 12-60
    expires_in: str = "1h"              # "10m"|"1h"|"6h"|"1d"|"7d"
    duration_seconds: Optional[float] = None
```

---

## 7. API 路由表

### 7.1 页面与认证

| 方法 | 路由 | 说明 |
|---|---|---|
| GET | `/` | 首页（Jinja2 渲染） |
| GET | `/config` | 公开配置（是否需要暗号） |
| POST | `/verify-passphrase` | 暗号验证 |

### 7.2 AI 生成（全部使用 LangGraph v2）

| 方法 | 路由 | 说明 | 请求格式 |
|---|---|---|---|
| POST | `/generate` | 主题 → 动画 | `{"topic":"...", "settings":{...}, "history":[...]}` |
| POST | `/paper/generate` | 论文 → 动画 | multipart: pdf + focus + settings |
| POST | `/generate/copy` | 主题 → 文案 | `{"topic":"...", "settings":{...}}` |
| POST | `/generate/animation` | 文案 → 动画 | `{"copy_json":{...}, "settings":{...}}` |
| POST | `/generate/full` | 主题 → 文案 → 动画（合并） | `{"topic":"...", "settings":{...}}` |

### 7.3 分享

| 方法 | 路由 | 说明 |
|---|---|---|
| POST | `/share` | 创建分享链接（返回 URL + 二维码） |
| GET | `/share/{id}` | 查看分享（无密码直接看，有密码显示输入页） |
| POST | `/share/{id}` | 密码验证分享 |

### 7.4 视频导出

| 方法 | 路由 | 说明 |
|---|---|---|
| POST | `/export/video` | HTML → MP4 视频导出（SSE 进度流） |
| GET | `/video/{id}` | 下载导出视频 |

### 7.5 其他

| 方法 | 路由 | 说明 |
|---|---|---|
| POST | `/api/log-error` | 前端错误日志上报 |

---

## 8. SSE 流式协议

### 8.1 事件类型

| 事件 | JSON 格式 | 说明 |
|---|---|---|
| 排队 | `{"event":"queued"}` | 任务在信号量队列中等待 |
| 开始 | `{"event":"started"}` | 信号量获取成功，开始生成 |
| Token | `{"token":"..."}` | LLM 流式输出的单个文本 token |
| 最终 HTML | `{"token":"\\n\\n<html>..."}` | 拼装完成的完整动画 HTML |
| 错误 | `{"error":"..."}` | 生成失败的错误信息 |
| 结束 | `{"event":"[DONE]"}` | 流结束标记 |

### 8.2 v2 适配器行为

- 只有 `generate_segments`、`generate_copy`、`generate_animation` 节点的 LLM token 才流式给前端
- `analyze_*` 节点的 LLM 调用是内部的，前端不可见
- `validate` 和 `assemble` 节点不产生 token 输出
- `postprocess` 节点完成后，最终 HTML 通过 `accumulated_state["html"]` 路径一次性 SSE 发送
- 前端**零改动**即可从 v1 切到 v2

---

## 9. 设计系统

### 9.1 动画设计系统（注入到生成的 HTML 中）

```css
:root {
  /* 叙事色彩 */
  --color-danger:    #DC2626;   /* 危机/问题/警告 — 段0 */
  --color-mystery:   #7C3AED;   /* 悬念/疑问/未知 — 段1 */
  --color-reveal:    #2563EB;   /* 揭示/解释/逻辑 — 段2 */
  --color-insight:   #059669;   /* 顿悟/答案/真相 — 段3 */
  --color-memory:    #D97706;   /* 金句/记忆/总结 — 段4 */

  /* 排版层级 */
  --font-display: 'MiSans', 'PingFang SC', sans-serif;
  --fs-hero:       clamp(3.5rem, 8vw, 7rem);
  --fs-headline:   clamp(2rem, 5vw, 4rem);
  --fs-body:       1.25rem;
  --fs-subtitle:   1.05rem;

  /* 缓动函数 */
  --ease-smooth:     cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out-back:   cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-spring:     cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

### 9.2 5 段叙事结构

| 段 | 名称 | 时长 | 核心视觉 | 颜色 | 动效 |
|---|---|---|---|---|---|
| 0 | **认知爆破** | 6-8s | visualSVG | #DC2626 | 冲击入场 (back.out) |
| 1 | **悬念铺垫** | 10-12s | visualSVG | #7C3AED | 悬疑慢揭 (power2.inOut) |
| 2 | **层层揭秘** | 20-22s | steps[] 步骤列表 | #2563EB | 信息阶梯 (power3.out, stagger) |
| 3 | **高潮揭晓** | 14s | compareBefore/After | #059669 | 认知翻转 (power4.out, glow) |
| 4 | **金句收尾** | 6-8s | visualSVG | #D97706 | 优雅定格 (power4.out) |

### 9.3 可视化类型互斥规则

每个段只能使用以下三种可视化类型之一：

| 字段 | 适用段 | 说明 |
|---|---|---|
| `visualSVG` | 0, 1, 4 | SVG 图形（开场冲击、悬念铺垫、金句收尾） |
| `steps` | 2 | 字符串数组（层层揭秘的步骤列表） |
| `compareBefore/After` | 3 | 新旧对比（高潮揭晓的认知翻转） |

由 `AnimationSegment.model_validator` 强制执行。

### 9.4 HTML 后处理注入（`backend/html_postprocessor.py`）

| 检测项 | 缺失时自动注入 |
|---|---|
| CSS 变量 `--color-*` | 完整设计系统 CSS |
| 字体平滑 `-webkit-font-smoothing` | 抗锯齿样式 |
| 噪点纹理 `<feTurbulence>` | SVG 噪点背景 |
| GSAP timeline 注册 | `window.__timelines` 自动收集补丁 |
| viewport meta | `<meta viewport>` |
| 闭合标签截断 | 自动补全 `</body></html>`（含 IIFE 闭合） |

---

## 10. 前端架构

### 10.1 技术方案

- **零框架**：原生 HTML/CSS/JS，无 React/Vue，无构建步骤
- **Jinja2 模板**：`frontend/templates/index.html` 由服务端渲染
- **GSAP 动画**：通过 CDN 加载（3.12.2 用于首页，3.14.2 用于生成的动画）
- **MiSans 字体**：通过小米 CDN 加载

### 10.2 首页布局

```
┌─────────────────────────────────────────────┐
│  Wordmark: ZSJ-观想录        语言切换  ⚙配置 │
├─────────────────────────────────────────────┤
│                                             │
│         Hero 大标题 + 输入框                  │
│      [概念生成]  [论文解释]  [提交]           │
│                                             │
├──────────────────┬──────────────────────────┤
│  LIVE SESSION    │  RAW RESPONSE             │
│  (生成进度)      │  (流式 token / 渲染动画)   │
│                  │                          │
│  • token-by-token│  • iframe sandbox        │
│  • 排队/开始提示 │  • 新窗口/下载/分享按钮    │
│                  │  • 解析失败→重新生成       │
└──────────────────┴──────────────────────────┘
```

### 10.3 前端关键功能

- **SSE 流式消费**：实时展示 LLM 输出的每个 token
- **动画自动渲染**：解析成功后自动在 sandbox iframe 中播放
- **多轮修改**：可以在生成后输入修改意见，基于 `history` 迭代
- **暗号门禁**：可选的 passphrase 验证
- **生成配置面板**：风格、节奏、比例、分辨率、深度、双语字幕、MathJax
- **分享功能**：设置密码和过期时间，生成二维码
- **错误上报**：前端错误通过 `/api/log-error` 记录到后端日志

### 10.4 UI 设计语言

- **粗野主义（Brutalism）**：黑白配色、实线边框、硬阴影 (`box-shadow: 8px 8px 0 #000`)
- **网格背景**：48×48px 网格线
- **零圆角**：`--radius-lg: 0`

---

## 11. 视频导出引擎

### 11.1 双渲染路径

```
HTML 动画
    │
    ├─ 检测到 data-composition-id?
    │   YES → HyperFrames 渲染 (确定性, 快速)
    │          ├─ 创建临时项目目录
    │          ├─ npx hyperframes render
    │          └─ 输出 MP4
    │
    └─ NO  → Playwright 录制 (通用, 兼容所有 HTML)
               ├─ 启动无头 Chromium
               ├─ 录制 WebM
               ├─ FFmpeg 转码 MP4
               └─ 输出 MP4
```

### 11.2 安全措施（Playwright 路径）

| 措施 | 说明 |
|---|---|
| 网络请求拦截 | 只允许已知 CDN 域名（jsdelivr, cdnjs, googleapis, unpkg） |
| CSP 头部 | `default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'` |
| 外部请求阻止 | 所有 `**/*` 路由经 `route.abort()` |
| sandbox iframe | 前端渲染也在 sandbox iframe 中 |

### 11.3 视频生命周期

- 视频文件存储在 `storage/exported_videos/`
- 过期时间可选：10分钟 / 1小时 / 6小时 / 1天 / 7天
- 每 300 秒自动清理过期视频
- 渲染中遇到 HyperFrames 失败自动回退到 Playwright

---

## 12. 部署配置

### 12.1 Dockerfile 结构

```dockerfile
FROM python:3.10-slim
# 1. Debian 源切换至阿里云镜像
# 2. 安装 FFmpeg + Chromium 共享库
# 3. 安装 Node.js 22 (从阿里云镜像下载)
# 4. pip install requirements.txt
# 5. playwright install chromium --with-deps
# 6. npm install -g hyperframes@0.6.121
# 7. COPY 应用代码
# 8. EXPOSE 8000
# 9. CMD uvicorn app:app --host 0.0.0.0 --port 8000
```

### 12.2 docker-compose.yml

```yaml
services:
  guanxianglu:
    build: .
    ports: ["${HOST_PORT:-18000}:8000"]
    volumes:
      - ./credentials.json:/app/credentials.json:ro
    restart: unless-stopped
    healthcheck:
      test: python requests to localhost:8000
      interval: 30s, timeout: 10s, retries: 3
```

### 12.3 credentials.json 配置

| 字段 | 默认值 | 说明 |
|---|---|---|
| `API_KEY` | (必填) | OpenAI 兼容 API 密钥 |
| `BASE_URL` | `""` | API 端点地址 |
| `MODEL` | `""` | 模型名称 |
| `ENABLE_DEBUG_OUTPUT` | `true` | 控制台打印 LLM 请求/响应 |
| `LOG_LEVEL` | `"INFO"` | DEBUG / INFO / WARNING / ERROR |
| `MAX_CONCURRENT_GENERATION_TASKS` | `1` | 最大并发生成数 |
| `MAX_CONCURRENT_EXPORT_TASKS` | `1` | 最大并发导出数 |
| `MAX_PAPER_UPLOAD_BYTES` | `20971520` (20MB) | PDF 上传大小限制 |
| `MAX_PAPER_TEXT_CHARS` | `120000` | PDF 提取文字上限 |
| `ACCESS_PASSPHRASES` | `null` | 暗号列表，`null` = 不启用，`[]` = 无需暗号 |

---

## 13. 项目文件清单

### 13.1 根目录

| 文件 | 大小 | 说明 |
|---|---|---|
| `app.py` | ~493 行 | FastAPI 主应用（路由层） |
| `Dockerfile` | ~58 行 | Docker 镜像构建 |
| `docker-compose.yml` | ~16 行 | Docker Compose 编排 |
| `requirements.txt` | ~15 行 | Python 依赖 |
| `credentials.json` | (不入 git) | 密钥和配置 |
| `example.json` | ~9 行 | 配置模板 |
| `ARCHITECTURE.md` | ~720 行 | 架构文档 |
| `README.md` | ~400 行 | 项目说明 |
| `PROJECT_REPORT.md` | (本文件) | 全面项目报告 |
| `.gitignore` | ~225 行 | Git 忽略规则 |
| `.dockerignore` | ~55 行 | Docker 忽略规则 |

### 13.2 backend/ 目录

| 文件 | 行数 | 职责 |
|---|---|---|
| `config.py` | ~71 | 全局配置、信号量、凭证读取 |
| `models.py` | ~108 | Pydantic 请求/响应模型 + LLM 输出校验模型 |
| `prompts.py` | ~506 | Prompt 构建函数 + HTML 模板拼装 |
| `logger.py` | ~196 | 统一日志（RotatingFileHandler + 控制台彩色） |
| `llm_stream.py` | ~73 | PDF 文本提取（仅保留 extract_pdf_text） |
| `html_postprocessor.py` | ~443 | HTML 后处理增强管道 |
| `share.py` | ~220 | 分享链接 CRUD + 过期清理 |
| `video_api.py` | ~150 | 视频导出路由 |
| `video_exporter.py` | ~598 | Playwright + HyperFrames 双渲染引擎 |
| `thought_filter.py` | ~92 | DeepSeek `<think>` 标签流式过滤器 |
| `start_guanxianglu.py` | ~39 | 本地一键启动脚本 |
| `graph/__init__.py` | ~24 | ChatOpenAI 延迟实例化 |
| `graph/state.py` | ~41 | AnimationState TypedDict |
| `graph/sse_adapter.py` | ~90 | astream_events → SSE 适配器 |
| `graph/nodes/plan.py` | ~172 | analyze_topic / analyze_paper |
| `graph/nodes/generate_copy.py` | ~99 | 5 幕文案生成 |
| `graph/nodes/generate_segments.py` | ~297 | 5 段视觉内容生成（三图共用） |
| `graph/nodes/validate.py` | ~136 | Pydantic 校验 + 重试反馈 |
| `graph/nodes/assemble.py` | ~42 | JSON → HTML 模板拼装 |
| `graph/nodes/postprocess.py` | ~40 | HTML 后处理 |
| `graph/edges/routing.py` | ~25 | 条件路由决策 |
| `graph/graphs/topic_graph.py` | ~56 | 图 A：主题 → 动画 |
| `graph/graphs/paper_graph.py` | ~55 | 图 B：论文 → 动画 |
| `graph/graphs/two_stage_graph.py` | ~77 | 图 C：两阶段合并 |
| `graph/graphs/copy_graph.py` | ~47 | 图 D：主题 → 文案 |
| `graph/graphs/animation_graph.py` | ~51 | 图 E：文案 → 动画 |

### 13.3 frontend/ 目录

| 文件 | 说明 |
|---|---|
| `templates/index.html` | 首页 Jinja2 模板 |
| `static/script.js` | 前端交互逻辑 |
| `static/style.css` | 样式（粗野主义设计） |
| `static/animation-template.html` | 动画 HTML 骨架模板 |
| `static/logo.jpg` | Logo 图标 |
| `static/logger.js` | 前端日志工具 |
| `static/postprocess.js` | 前端 HTML 后处理 |
| `static/one-quotes.json` | 名言数据 |

### 13.4 storage/ 目录（运行时，不入 git）

| 子目录 | 内容 |
|---|---|
| `logs/` | 应用日志（10MB 轮转，5 个备份） |
| `shared_html/` | 分享的 HTML 文件 |
| `exported_videos/` | 导出的 MP4 视频 |
| `temp_render/` | 临时渲染目录 |

---

## 14. 架构质量评估

### 14.1 优点

| 维度 | 评价 |
|---|---|
| **架构清晰度** | ⭐⭐⭐⭐⭐ 分层明确：路由(1层) → 业务逻辑 → AI 编排(nodes/graphs/edges) → LLM |
| **代码复用** | ⭐⭐⭐⭐⭐ SSE adapter 三图共用，generate_segments 三图共用，validate 两处复用 |
| **数据校验** | ⭐⭐⭐⭐⭐ Pydantic 单一数据源，自动生成 prompt 格式说明、结果校验、重试反馈 |
| **容错能力** | ⭐⭐⭐⭐ 最多 2 次自动重试 + 精确修正指令；HTML 后处理自动补全截断标签 |
| **向后兼容** | ⭐⭐⭐⭐⭐ SSE 协议完全不变，前端零改动即可用 v2 路由 |
| **安全措施** | ⭐⭐⭐⭐ 暗号访问控制、分享密码、sandbox iframe、视频导出网络拦截、CSP |
| **可观测性** | ⭐⭐⭐⭐ 结构化日志 + 文件轮转 + 控制台彩色 + 前端错误上报 |
| **部署便利性** | ⭐⭐⭐⭐ Docker 一键构建，docker-compose 含健康检查 |

### 14.2 可改进项

| 维度 | 现状 | 建议 |
|---|---|---|
| **测试覆盖** | ❌ 无测试文件 | 添加 pytest 测试（至少对 validate / assemble / postprocess 节点） |
| **类型安全** | 部分 | AnimationState 用 TypedDict，但部分 dict 参数缺少类型标注 |
| **错误处理** | 基本 | routing.py 中 `__end__` 路径没有显式的错误返回给前端 |
| **文档同步** | 良好 | ARCHITECTURE.md 详尽，但未提及 copy_graph 和 animation_graph |
| **配置验证** | 基本 | credentials.json 缺少 schema 校验，启动时不做完整检查 |
| **API 版本ing** | 无 | v1/v2 路由混在同一文件，但 v1 代码实际已删除 |
| **并发模型** | 简单 | 只有 asyncio.Semaphore，无优先级队列或任务取消机制 |

---

## 15. 已知问题与风险

### 15.1 当前代码问题

1. **copy_graph 路由映射不一致**：`after_validate_copy` 在 `copy_graph.py` 中 map `"generate_animation" → END`，但这个映射名字与其语义不符——文案图通过后直接结束，不是"生成动画"

2. **retry_count 重置逻辑脆弱**：`generate_segments` 成功时硬编码 `"retry_count": 0`，如果上游 validate 增加了计数但下游 generate 成功就清掉，可能导致回溯

3. **ThoughtProcessFilter 状态不跨调用**：每次 graph 运行创建新的 filter，但 `generate_segments` 和 `generate_copy` 每次都新建，正常。但如果重试不重建 LLM，filter 状态会乱

4. **`_load_animation_template()` 路径依赖**：用 `os.path.dirname(os.path.dirname(__file__))` 向上找模板，在生产环境 PO 模式可能失败

5. **全局状态 `shared_html_links`**：在 `config.py` 中定义为模块级 dict，多 worker 模式下不会共享（但在 ASGI 单进程中没问题）

6. **无效 import**：`config.py` L67-70 检查 `API_KEY.startswith("sk-REPLACE_ME")` 但 `startswith` 检查的字符串在实际中可能不存在

### 15.2 架构风险

| 风险 | 级别 | 说明 |
|---|---|---|
| LangGraph 版本锁定 | 中 | `langgraph>=0.2.0` 较宽松，大版本更新可能破坏 API |
| Playwright 内存泄漏 | 中 | 长时间运行的视频导出可能积累未释放的浏览器实例 |
| 大 PDF 超时 | 低 | 120K 字符的论文分析可能需要较长时间，缺少明确的超时控制 |
| 单点故障 | 低 | 无任务持久化——服务重启后正在进行的生成任务会丢失 |

---

## 16. 迁移进度

### 16.1 Phase 进度

| Phase | 状态 | 内容 |
|---|---|---|
| **Phase 1** | ✅ 完成 | 新建 `backend/graph/`、新增 v2 路由、旧路由保留 |
| **Phase 2** | 🔄 进行中 | 旧代码移至 `backend/` 子包、目录重组 |
| **Phase 3** | ⬜ 待开始 | 删除旧的 v1 生成器、简化 `prompts.py` |

### 16.2 待提交的改动

当前工作区有未提交的改动（见 git status），主要涉及：
- 16 个文件，净删除约 10,000 行
- 架构从单文件巨石向分层包结构迁移
- 所有改动都是架构重组，功能逻辑不变

### 16.3 建议的下一步

1. **提交当前重构**：将工作区改动作为一个大的重构 commit
2. **补充测试**：至少为 validate、assemble、postprocess 添加单元测试
3. **更新 ARCHITECTURE.md**：补充 copy_graph 和 animation_graph 的文档
4. **Phase 3 清理**：删除 `llm_stream.py` 中残留的旧生成器函数、简化 `prompts.py`
5. **配置校验**：在 `config.py` 中添加 `credentials.json` 的完整 schema 校验
6. **性能优化**：考虑为编译后的 graph 添加缓存、复用 LLM 实例而非每次新建

---

## 附录 A：关键文件依赖关系图

```
app.py
  ├── config.py          ← 凭证、信号量、LLM 客户端
  ├── models.py          ← 请求模型 + LLM 输出校验模型
  ├── prompts.py         ← Prompt 构建函数 + _assemble_animation_html
  ├── llm_stream.py      ← extract_pdf_text (PDF 提取)
  ├── share.py           ← 分享 CRUD + 页面构建
  ├── video_api.py       ← 视频导出路由
  ├── html_postprocessor.py ← HTML 后处理增强
  ├── logger.py          ← 统一日志系统
  └── graph/             ← ★ LangGraph v2 编排层
      ├── __init__.py    ← ChatOpenAI(get_llm)
      ├── state.py       ← AnimationState
      ├── sse_adapter.py ← stream_graph_to_sse (所有路由共用)
      ├── nodes/         ← 7 个节点
      │   ├── plan.py           → analyze_topic / analyze_paper
      │   ├── generate_copy.py  → generate_copy
      │   ├── generate_segments.py → generate_segments / generate_animation
      │   ├── validate.py       → validate_copy / validate_segments
      │   ├── assemble.py       → assemble_html
      │   └── postprocess.py    → postprocess_html_node
      ├── edges/
      │   └── routing.py        → after_validate_copy / after_validate_segments
      └── graphs/               → 5 张编译的 StateGraph
          ├── topic_graph.py
          ├── paper_graph.py
          ├── two_stage_graph.py
          ├── copy_graph.py
          └── animation_graph.py
```

## 附录 B：Git 提交历史

```
184cf92 v0.1.3 动画优化
c3d64f8 v0.1.2 文案与动画生成分离，整体使用优化
cfa470d v0.1.1 使用HyperFrames实现视频导出功能
1cef131 Initial commit
```

## 附录 C：代码统计

| 目录 | 文件数 | 总行数（估算） |
|---|---|---|
| 根目录 | 7 (不含 .md) | ~600 |
| backend/ (不含 graph/) | 11 | ~2,500 |
| backend/graph/ | 16 | ~1,500 |
| frontend/ | 8 | ~8,000 |
| **总计** | **42** | **~12,600** |

---

> 📝 本报告基于 2026-06-24 代码库状态生成，涵盖了所有源码文件、架构文档和 git 历史的全面分析。
