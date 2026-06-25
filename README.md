<div align="center">

# ZSJ-观想录

把一个概念或一篇论文，变成一段可以播放的知识动画。

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/AI-LangGraph-1B1B1B?style=flat-square)
![SSE](https://img.shields.io/badge/Streaming-SSE-black?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-Check%20Repository-lightgrey?style=flat-square)

一个本地优先的 AI 科普视频生成 Web 应用。输入主题或上传 PDF 论文，模型会生成可直接播放的单文件 HTML 动画页面。

</div>

---

## 目录

- [项目简介](#项目简介)
- [功能亮点](#功能亮点)
- [预览与使用场景](#预览与使用场景)
- [快速开始](#快速开始)
- [使用方式](#使用方式)
- [Docker 部署](#docker-部署)
- [配置说明](#配置说明)
- [接口说明](#接口说明)
- [技术栈](#技术栈)
- [AI 架构](#ai-架构)
- [项目结构](#项目结构)
- [使用建议](#使用建议)
- [常见限制](#常见限制)
- [安全提示](#安全提示)

## 项目简介

很多知识并不适合只用文字解释。观想录希望把「抽象概念」「动态过程」「论文方法」快速转化为一段可视化动画，方便用于课堂、演示、短视频原型、知识科普和技术讲解。

你可以输入：

```text
黑洞是如何形成的
```

也可以上传一篇 PDF 论文，并指定讲解重点：

```text
第三章方法、Transformer 注意力机制、实验结果
```

观想录会生成完整的 HTML/CSS/JavaScript/SVG 动画页面，并在浏览器中自动播放。

## 功能亮点

| 功能 | 说明 |
| --- | --- |
| 概念动画生成 | 输入一个知识点，LangGraph 多步流水线生成可播放的动态网页动画 |
| 论文解释 | 上传 PDF 论文，先提炼要点再生成论文动画讲解页面 |
| 两阶段生成 | 先生成结构化五幕文案，审阅编辑后自动生成动画（单次 API 调用完成） |
| 智能重试 | Pydantic 强校验 LLM 输出，失败自动重试并附带精确修正指令（最多 2 次） |
| 指定论文重点 | 可聚焦章节、术语、模型结构、实验结果或结论 |
| SSE 流式输出 | 后端实时推送模型输出 token，前端逐字展示生成过程 |
| 自动渲染 | 自动提取模型返回的 HTML，并放入 sandbox iframe 播放 |
| 多轮修改 | 生成后可继续输入修改意见，基于历史上下文迭代 |
| 专业生成配置 | 支持风格、节奏、比例、分辨率、讲解深度、字幕和 MathJax |
| 分享链接 | 可创建带密码和过期时间的 HTML 分享链接 |
| 访问控制 | 支持暗号入口，适合本地演示或小范围分享 |
| Docker 部署 | 内置 Dockerfile，一行命令构建运行 |

## 预览与使用场景

启动后访问：

```text
http://127.0.0.1:8000
```

适合生成：

- 数学公式推导动画
- 物理过程解释动画
- 算法运行过程动画
- PDF 论文动画讲解
- 模型结构和数据流程演示
- 科普类知识短片原型
- 教学课件中的动态片段
- 产品概念或技术方案演示页面

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd ZhiXiang
```

### 2. 安装依赖

建议使用 Python 3.10 或更高版本。

```bash
pip install -r requirements.txt
```

### 3. 创建配置文件

复制示例配置：

```bash
cp example.json credentials.json
```

编辑 `credentials.json`：

```json
{
    "API_KEY": "sk-your-api-key",
    "BASE_URL": "https://api.openai.com/v1",
    "MODEL": "gpt-4o",
    "ENABLE_DEBUG_OUTPUT": false,
    "MAX_CONCURRENT_GENERATION_TASKS": 1,
    "MAX_PAPER_UPLOAD_BYTES": 20971520,
    "MAX_PAPER_TEXT_CHARS": 120000,
    "ACCESS_PASSPHRASES": []
}
```

如果不需要暗号访问，把 `ACCESS_PASSPHRASES` 设置为空数组 `[]`。

### 4. 启动应用

直接启动 FastAPI：

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

打开浏览器访问：

```text
http://127.0.0.1:8000
```

## 使用方式

### 生成概念动画

在首页输入要解释的概念或主题，选择生成配置后开始生成。后端使用 LangGraph 编排多步 AI 流程：先分析主题 → 生成视觉内容 → Pydantic 校验 → 拼装 HTML → 后处理增强。生成完成后，页面会自动解析模型返回的 HTML 并在浏览器中播放。

示例：

```text
用适合高中生理解的方式，解释牛顿第二定律 F=ma，要求有力、质量、加速度之间关系的动态示意。
```

### 生成论文解释动画

点击首页的「论文解释」按钮，上传 PDF 论文。可以留空重点输入框生成整篇论文讲解，也可以填写具体章节、术语、模型结构或实验结果作为重点。

论文解释流程：
1. 提取 PDF 文本（最长 120K 字符）
2. AI 提炼论文概要（核心贡献、方法亮点、关键结果）
3. 基于概要生成 5 段动画视觉内容
4. Pydantic 校验 + 失败自动重试
5. 拼装 HTML 并后处理增强

论文解释会尝试覆盖：

- 研究背景与问题
- 核心洞察/假设
- 方法框架
- 关键实验/结果
- 结论与启发

> 论文解释依赖 PDF 可提取文本。扫描版或纯图片型 PDF 需要先 OCR。

### 两阶段精细生成

如果对动画质量有更高要求，可以使用两阶段模式（`/generate/full`）：

1. **第一阶段**：生成 5 幕结构化文案（问题冲突型叙事），包含每幕的旁白、视觉描述、动效暗示
2. **第二阶段**：基于文案自动生成 5 段动画视觉内容

两阶段在单次 API 调用中自动完成，不需要手动传递中间结果。文案和动画各自有独立的 Pydantic 校验和重试机制。

## Docker 部署

### 构建镜像

```bash
docker build -t guanxianglu:latest .
```

### 运行容器

```bash
docker run --rm -p 8000:8000 \
  -v "$(pwd)/credentials.json:/app/credentials.json:ro" \
  -v "$(pwd)/storage:/app/storage" \
  guanxianglu:latest
```

默认访问：

```text
http://127.0.0.1:8000
```

## 配置说明

| 字段 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `API_KEY` | 是 | 无 | 大模型 API Key |
| `BASE_URL` | 否 | `""` | OpenAI 兼容接口地址 |
| `MODEL` | 否 | `""` | 模型名称 |
| `ENABLE_DEBUG_OUTPUT` | 否 | `true` | 是否打印调试信息 |
| `LOG_LEVEL` | 否 | `"INFO"` | 日志级别：DEBUG / INFO / WARNING / ERROR |
| `MAX_CONCURRENT_GENERATION_TASKS` | 否 | `1` | 最大并发生成任务数 |
| `MAX_CONCURRENT_EXPORT_TASKS` | 否 | `1` | 最大并发视频导出数 |
| `MAX_PAPER_UPLOAD_BYTES` | 否 | `20971520` | PDF 论文最大上传体积（默认 20MB） |
| `MAX_PAPER_TEXT_CHARS` | 否 | `120000` | 从论文中送入模型的最大文本字符数 |
| `ACCESS_PASSPHRASES` | 否 | `null` | 暗号列表；为空数组时不启用暗号 |

补充说明：

- 后端使用 **langchain-openai**（`ChatOpenAI`）调用 OpenAI 兼容 API，支持 `response_format=json_object`。
- 论文解释使用 `pypdf` 提取 PDF 文本，最长支持 120K 字符。
- 超过文本上限的论文会被截断后再送入模型。
- `credentials.json` 包含敏感信息，请不要提交到公开仓库。

## 接口说明

### AI 生成接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/generate` | **主题 → 动画**。输入 topic + settings，SSE 流式返回 token 和最终 HTML |
| `POST` | `/paper/generate` | **论文 → 动画**。上传 PDF + focus，SSE 流式返回 token 和最终 HTML |
| `POST` | `/generate/full` | **主题 → 文案 → 动画**（两阶段合并）。单次 API 调用，先生成五幕文案再生成动画 |

### 其他接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | Web 页面入口 |
| `GET` | `/config` | 获取公开配置（是否需要暗号） |
| `POST` | `/verify-passphrase` | 校验访问暗号 |
| `POST` | `/share` | 创建带密码和过期时间的 HTML 分享链接 |
| `GET` | `/share/{share_id}` | 访问分享页面 |
| `POST` | `/share/{share_id}` | 校验分享密码并打开分享页面 |
| `POST` | `/export/video` | HTML 动画 → MP4 视频导出（SSE 进度流） |
| `GET` | `/video/{video_id}` | 下载导出视频 |
| `POST` | `/api/log-error` | 前端错误日志上报 |

### SSE 流式响应协议

所有生成接口返回 `text/event-stream`，事件格式：

| 事件 | 说明 |
| --- | --- |
| `{"event":"queued"}` | 任务进入信号量队列等待 |
| `{"event":"started"}` | 开始执行生成 |
| `{"token":"..."}` | LLM 流式输出 token（前端逐字显示） |
| `{"token":"\n\n<html>..."}` | 拼装完成的完整动画 HTML |
| `{"error":"..."}` | 生成失败的错误信息 |
| `{"event":"[DONE]"}` | 流式传输结束 |

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| AI 编排 | **LangGraph**（StateGraph 多步流水线 + 条件路由） |
| LLM 调用 | **langchain-openai**（ChatOpenAI, streaming + json_object） |
| 数据校验 | **Pydantic v2**（请求模型 + LLM 输出强校验 + model_validator） |
| 流式传输 | Server-Sent Events（astream_events → SSE adapter） |
| 动画引擎 | GSAP 3.14（CDN 引入，JavaScript 时间轴动画） |
| PDF 解析 | pypdf |
| 视频导出 | Playwright + HyperFrames（无头浏览器渲染 HTML → MP4） |
| 前端 | 原生 HTML / CSS / JavaScript |
| 模板 | Jinja2 |
| 日志 | logging + RotatingFileHandler（10MB 轮转，5 个备份） |
| 容器化 | Docker（Python 3.10-slim + Node.js 22 + Chromium） |

## AI 架构

项目使用 **LangGraph** 替代单次巨型 prompt 调用，将生成流程拆分为多步可校验的流水线。

### 三张 StateGraph

| 图 | 路由 | 流程 |
| --- | --- | --- |
| `topic_graph` | `/generate` | `analyze_topic → generate_segments ⇄ validate → assemble → postprocess → END` |
| `paper_graph` | `/paper/generate` | `analyze_paper → generate_segments ⇄ validate → assemble → postprocess → END` |
| `two_stage_graph` | `/generate/full` | `analyze_topic → generate_copy ⇄ validate → generate_animation ⇄ validate → assemble → postprocess → END` |

### 关键设计

- **LLM 只输出 JSON**（`response_format={"type": "json_object"}`），服务端拼装 ~15KB 的 HTML 模板，彻底避免 LLM 截断
- **Pydantic 单一数据源**：模型定义同时用于 prompt 格式说明生成、结果强校验、重试反馈
- **智能重试**：校验失败时生成精确到字段的修正指令，注入下一次 LLM 调用的 prompt（最多 2 次）
- **论文先提炼**：120K 字符的论文先被 `analyze_paper` 提炼为 ~300 字 outline，后续节点用精简上下文生成
- **分析节点内部运行**：`analyze_*` 节点的 LLM 调用不向前端流式输出，只有 `generate_*` 节点的 token 对用户可见

### 5 段叙事结构

| 段 | 名称 | 时长 | 视觉元素 | 颜色 |
| --- | --- | --- | --- | --- |
| 0 | 认知爆破 | 6-8s | visualSVG | #DC2626 |
| 1 | 悬念铺垫 | 10-12s | visualSVG | #7C3AED |
| 2 | 层层揭秘 | 20-22s | steps 数组 | #2563EB |
| 3 | 高潮揭晓 | 14s | compareBefore/After | #059669 |
| 4 | 金句收尾 | 6-8s | visualSVG | #D97706 |

## 项目结构

```text
.
├── app.py                         # FastAPI 主应用（路由层）
├── Dockerfile                     # Docker 镜像构建文件
├── requirements.txt               # Python 依赖
├── credentials.json               # 密钥与配置（不入 git）
├── ARCHITECTURE.md                # 详细架构文档
│
├── backend/
│   ├── config.py                  # 全局配置、信号量、凭证读取
│   ├── models.py                  # Pydantic 请求模型 + LLM 输出校验模型
│   ├── prompts.py                 # Prompt 构建函数
│   ├── logger.py                  # 统一日志系统（文件轮转 + 控制台彩色）
│   ├── llm_stream.py              # PDF 文本提取
│   ├── html_postprocessor.py      # HTML 后处理增强管道（CSS/GSAP/纹理注入）
│   ├── share.py                   # 分享链接 CRUD + 过期清理
│   ├── video_api.py               # 视频导出路由
│   ├── video_exporter.py          # Playwright + HyperFrames 渲染引擎
│   │
│   └── graph/                     # LangGraph AI 编排层
│       ├── __init__.py            # ChatOpenAI 延迟实例化
│       ├── state.py               # AnimationState TypedDict
│       ├── sse_adapter.py         # astream_events → SSE 适配器
│       ├── nodes/
│       │   ├── plan.py            # analyze_topic / analyze_paper
│       │   ├── generate_copy.py   # 文案生成（两阶段图用）
│       │   ├── generate_segments.py # 动画视觉内容生成（三图共用）
│       │   ├── validate.py        # Pydantic 校验 + 重试反馈
│       │   ├── assemble.py        # JSON → HTML 模板拼装
│       │   └── postprocess.py     # HTML 后处理 + custom event 输出
│       ├── edges/
│       │   └── routing.py         # 条件边：校验通过/失败路由
│       └── graphs/
│           ├── topic_graph.py     # 图 A：主题 → 动画
│           ├── paper_graph.py     # 图 B：论文 → 动画
│           └── two_stage_graph.py # 图 C：主题 → 文案 → 动画
│
├── frontend/
│   ├── templates/index.html       # 首页 Jinja2 模板
│   └── static/
│       ├── script.js              # 前端交互逻辑
│       ├── style.css              # 样式
│       ├── animation-template.html # 动画 HTML 骨架模板
│       └── ...
│
└── storage/                       # 运行时数据（不入 git）
    ├── logs/                      # 日志文件
    ├── shared_html/               # 分享的 HTML 文件
    ├── exported_videos/           # 导出的 MP4 视频
    └── temp_render/               # 临时渲染目录
```

## 使用建议

为了获得更稳定的动画结果，提示词可以包含：

- 想解释的核心概念
- 受众水平
- 希望呈现的视觉风格
- 是否需要公式、步骤、对比或时间线
- 希望强调的教学目标或结论

论文解释建议：

- 优先上传可复制文本的 PDF
- 对长论文指定重点章节或概念
- 如果论文包含复杂公式或结构图，开启 MathJax 或在重点中明确说明
- 对实验结果类论文，指定要解释的表格、指标或对比结论

## 常见限制

- 模型输出质量取决于所选模型和提示词质量。
- 生成的 HTML 是 AI 生成内容，复杂动画可能需要二次调整。
- PDF 解析依赖文本层，扫描版论文需要 OCR。
- 长论文会受 `MAX_PAPER_TEXT_CHARS` 限制（默认 120K 字符），超过部分会被截断。
- Pydantic 校验失败后最多自动重试 2 次，超过后会返回错误信息。
- 移动端预览能力有限，建议在 PC 端使用。

## 安全提示

- 不要公开提交 `credentials.json`。
- 部署到公网时，请配置暗号、反向代理鉴权或其他访问控制。
- 生成的 HTML 会在 sandbox iframe 中运行，但仍建议只在可信环境中使用。
- 分享链接可能包含 AI 生成的完整 HTML 内容，请谨慎设置密码和过期时间。
