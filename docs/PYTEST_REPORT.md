# Pytest 集成报告 — AI Animation Backend

> **项目**：ZSJ-观想录 (AI Animation Backend v2.0.0)  
> **日期**：2026-06-27  
> **结果**：✅ 252 个测试全部通过  

---

## 1. 项目背景

本项目是一个 FastAPI + LangGraph AI 动画生成后端，通过 Docker 部署。核心功能是将用户输入的主题或 PDF 论文，经由 LLM 编排管道生成可播放的 GSAP 动画 HTML 页面。此次改造之前，项目测试覆盖率为零。

**核心难点**：`backend/config.py` 在模块导入时即执行 `open("credentials.json")`，任何通过 `app` 的导入链在没有真实凭证文件时会直接崩溃。

---

## 2. 目录结构

```
tests/
├── __init__.py
├── conftest.py                    # 全局 fixtures + builtins.open 拦截
├── fake_credentials.json          # 提交到 git 的假凭证（无真实密钥）
├── helpers.py                     # FakeChunk、FakeAIMessage 等辅助工具
│
├── unit/                          # 纯单元测试（无需 FastAPI / LLM）
│   ├── test_thought_filter.py     # 22 tests — 流式思考标签过滤器
│   ├── test_models.py             # 31 tests — Pydantic 模型校验
│   ├── test_html_postprocessor.py # 41 tests — HTML 后处理 + 诊断
│   ├── test_prompts.py            # 29 tests — Prompt 构建函数
│   └── test_routing.py            # 21 tests — LangGraph 条件路由
│
├── graph/                         # LangGraph 图测试
│   ├── test_graph_compilation.py  # 12 tests — 5 个 StateGraph 编译验证
│   ├── test_validate.py           # 19 tests — validate_copy / validate_segments 节点
│   ├── test_assemble.py           #  7 tests — HTML 拼装节点
│   └── test_postprocess_node.py   #  4 tests — 后处理节点
│
├── integration/                   # 集成测试
│   ├── test_config.py             # 13 tests — 配置加载
│   ├── test_share.py              # 18 tests — 分享链接 CRUD
│   └── test_pdf.py                #  7 tests — PDF 文本提取
│
└── api/                           # API 路由测试
    ├── test_routes_basic.py       # 10 tests — GET /, /config, /verify-passphrase
    ├── test_routes_generate.py    # 10 tests — SSE 流式生成路由（mock LLM）
    └── test_routes_share.py       #  8 tests — /share 路由
```

---

## 3. 关键设计决策

### 3.1 零配置运行 — `builtins.open` 拦截

`conftest.py` 的模块级代码在 pytest 收集测试之前执行，用自定义函数替换 `builtins.open`：

```python
_original_open = builtins.open

def _patched_open(file, mode="r", *args, **kwargs):
    """当尝试打开不存在的 credentials.json 时，重定向到测试用假凭证。"""
    if isinstance(file, str) and os.path.basename(file) == "credentials.json":
        if not os.path.exists(file):
            fake = os.path.join(os.path.dirname(__file__), "fake_credentials.json")
            if os.path.exists(fake):
                return _original_open(fake, mode, *args, **kwargs)
    return _original_open(file, mode, *args, **kwargs)

builtins.open = _patched_open
```

这意味着：
- 无需手动 `cp fake_credentials.json credentials.json` 
- 真实的 `credentials.json` 如果存在则正常使用（不会拦截）
- `tests/fake_credentials.json` 提交到 git，不含真实密钥

### 3.2 Fixture 分层

| Fixture | 作用域 | 功能 |
|---------|--------|------|
| `patch_config` | autouse=True | 所有测试自动注入 `backend.config.*` 假值 |
| `mock_llm` | function | Mock `get_llm()` 返回 `AsyncMock` |
| `sample_segments` | function | 5 段合法 AnimationSegment 数据 |
| `sample_html` | function | 最小合法动画 HTML |
| `sample_copy_json` | function | 合法 CopySchema（5 幕文案） |

### 3.3 Mock 策略

| 被测层 | Mock 什么 | 方式 |
|--------|----------|------|
| 纯单元测试 | 无 | 直接测试纯函数 |
| 图节点测试 | 无（validate/assemble 不调 LLM） | 直接用 sample 数据 |
| 集成测试 | pypdf、文件系统路径 | `mocker.patch` + `tmp_path` |
| API 基础路由 | 无 | TestClient 真实请求 |
| API 生成路由 | 图节点函数（`generate_segments` 等） | `mocker.patch` 替换为返回假数据的 async 函数 |

---

## 4. 测试覆盖详情

### 4.1 纯单元测试（144 tests）

#### ThoughtProcessFilter (`test_thought_filter.py`) — 22 tests

| 测试类别 | 测试方法 | 覆盖点 |
|---------|---------|--------|
| 基础功能 | `test_no_think_tags_passthrough` | 无标签文本原样输出 |
| | `test_empty_input` | 空输入处理 |
| | `test_feed_empty_then_content` | 空 feed 不影响后续 |
| 标签剥离 | `test_strip_think_tag_basic` | `<think>...</think>` 剥离 |
| | `test_strip_thinking_tag` | `<thinking>...</thinking>` 剥离 |
| | `test_strip_reasoning_tag` | `<reasoning>...</reasoning>` 剥离 |
| | `test_strip_chinese_think_prefix` | "思考过程：…最终答案：…" 剥离 |
| | `test_strip_chinese_answer_prefix` | "答案：" 前缀剥离 |
| 流式分片 | `test_streaming_chunks` | 多个小 chunk 逐步喂入，标签跨 chunk |
| | `test_streaming_start_marker_split` | 开始标签 `<thi` + `nk>` 跨 chunk |
| | `test_streaming_end_marker_split` | 两个 think 块分 chunk 到达 |
| 多块/嵌套 | `test_multiple_think_blocks` | 多个 think 块 |
| | `test_consecutive_think_tags` | 连续的 think 块 |
| flush 行为 | `test_flush_in_thought_discards` | 思考中 flush 丢弃缓冲区 |
| | `test_flush_out_of_thought_returns_buffer` | 非思考中 flush 返回缓冲 |
| 边界情况 | `test_only_think_tag` | 全部是 think 内容 |
| | `test_text_before_think` | think 前有文本 |
| | `test_case_insensitive` | `<THINK>...</THINK>` 大小写 |
| | `test_partial_start_tag_not_triggered` | 不完整标签不误触发 |
| | `test_mixed_content_no_tags` | 中英混合无标签 |
| 重用 | `test_filter_reuse` | 同一实例多次使用 |
| | `test_filter_reuse_after_flush` | flush 后继续使用 |

> **覆盖目标**：~95% ✅

#### Pydantic 模型 (`test_models.py`) — 31 tests

| 测试类别 | 覆盖模型 | 关键覆盖点 |
|---------|---------|-----------|
| `TestAnimationSegment` | AnimationSegment | 最小合法、title 长度、hex 颜色校验、visualSVG/steps/compareBefore 互斥校验（4 种组合）、全部可选字段 |
| `TestAnimationOutput` | AnimationOutput | 恰好 5 段、少于/多于 5 段、JSON 字符串反序列化 |
| `TestCopySchema` | CopySchema, CopyAct | 合法文案、空 acts、缺 title、默认值、act 各字段 |
| `TestChatRequest` | ChatRequest | 最小请求、带 settings |
| `TestPassphraseRequest` | PassphraseRequest | 合法暗号 |
| `TestShareRequest` | ShareRequest | 密码 4-20 位校验、过短/过长报错 |
| `TestVideoExportRequest` | VideoExportRequest | 默认值、width/fps/expires_in 范围校验 |
| `TestLogErrorRequest` | LogErrorRequest | 空 errors、带 error |

> **覆盖目标**：~90% ✅

#### HTML 后处理器 (`test_html_postprocessor.py`) — 41 tests

| 测试类别 | 关键覆盖点 |
|---------|-----------|
| `TestDetectionFunctions` (12) | `_has_css_variables`、`_has_font_smoothing`、`_has_noise_texture`、`_has_gsap_cdn`、`_has_timelines_registration`、`_has_viewport_meta` 正/负向检测 |
| `TestStripMarkdownFences` (4) | 无 fence、`` ```html ``、`` ``` ``、`` ```HTML `` |
| `TestEnsureClosingTags` (4) | 已闭合、缺 `</body>`、缺 `</html>`、两者皆缺 |
| `TestValidateJsonSegments` (4) | 无 segments、合法 JSON、非法 JSON、空 segment |
| `TestPostprocessHtml` (13) | 完整流程、无 HTML 结构、CSS 变量注入、不重复注入、viewport meta、字体平滑、噪点纹理、GSAP patch、无 CDN 不注入、全关闭、markdown fence 剥离、自动闭合、移除空 `<p>` |
| `TestDiagnoseHtml` (4) | 完整 HTML 无 error、缺 GSAP 是 error、`@keyframes` warning、`setTimeout` warning |

> **覆盖目标**：~85% ✅

#### Prompt 构建 (`test_prompts.py`) — 29 tests

| 测试类别 | 覆盖函数 |
|---------|---------|
| `TestBuildGenerationSettings` (11) | `build_generation_setting_instructions()` — 所有 setting 选项组合 |
| `TestResolutionDims` (4) | `_build_resolution_dims()` — 720p/1080p/2k/未知回退 |
| `TestBuildCopySystemPrompt` (5) | `build_copy_system_prompt()` — topic、五幕结构、visual_description 规范、输出格式、settings 传递 |
| `TestBuildAnimationFromCopyPrompt` (5) | `build_animation_from_copy_system_prompt()` — copy 标题、act 摘要、输出格式、颜色提示、禁止 markdown |
| `TestAssembleAnimationHtml` (7) | `_assemble_animation_html()` — 合法 HTML、segment 数据、默认时长、自定义时长、分辨率、duration 替换、少于5段补齐 |

> **覆盖目标**：~80% ✅

#### 路由逻辑 (`test_routing.py`) — 21 tests

| 测试类别 | 覆盖函数 |
|---------|---------|
| `TestRetryLeft` (5) | `_retry_left()` — retry_count < / = / > max_retries，默认值 |
| `TestAfterValidateCopy` (5) | `after_validate_copy()` — passed / retry / abort / 首次失败 / 有效覆盖超限 retry_count |
| `TestAfterValidateSegments` (5) | `after_validate_segments()` — 同上 5 种状态 |
| `TestTokens` (3) | 三个令牌常量值不变 |

> **覆盖目标**：100% ✅

### 4.2 图测试（42 tests）

#### 编译验证 (`test_graph_compilation.py`) — 12 tests

验证 5 个 StateGraph 全部能成功编译，且包含正确的节点集合。特别验证了 `two_stage_graph` 有两层独立的校验（`validate_copy` + `validate_animation`）。

#### 校验节点 (`test_validate.py`) — 19 tests

| 节点 | 测试场景 |
|------|---------|
| `validate_copy` (8) | 合法通过、空字典、完全缺失、缺 title、act 结构不完整、retry_count 递增、通过重置 retry_count |
| `validate_segments` (11) | 合法通过、空字符串、纯空白、非法 JSON、少于5段、多于5段、互斥违规、title 超长、retry_count 递增、缺 segments 键 |

#### 拼装节点 (`test_assemble.py`) — 7 tests

验证 `assemble_html` 能正确产出完整 HTML、正确处理空/不足 segments、正确传递 settings、从 copy_json 提取时长、显式 seg_durations 优先、异常降级为 error。

#### 后处理节点 (`test_postprocess_node.py`) — 4 tests

验证空 HTML 报错、合法 HTML 被增强、CSS 变量注入、异常时降级返回原始 HTML。

### 4.3 集成测试（38 tests）

#### 配置 (`test_config.py`) — 13 tests

验证 `conftest.py` 注入的假配置值正确生效：API_KEY、BASE_URL、MODEL、DEBUG、并发数、passphrase、duration hints、过期配置、信号量创建、时区、存储路径。

#### 分享 (`test_share.py`) — 18 tests

| 类别 | 覆盖 |
|------|------|
| 路径 | `get_share_paths` 生成正确的 meta/html 路径 |
| 序列化 | `serialize_share_record` ISO 格式、`parse_share_datetime` 时区处理 |
| CRUD | 保存→加载、不存在的返回 None、删除（内存+磁盘）、内存缓存、过期自动删除、无过期永久有效、`cleanup_expired_shares_once` 批量清理 |
| 页面 | `build_share_access_page`（无错误/有错误）、`build_shared_viewer_page`、`create_qr_data_url` |

#### PDF (`test_pdf.py`) — 7 tests

Mock `pypdf.PdfReader`，验证：合法提取、非 PDF 报错、空文件报错、超大文件报错、损坏 PDF 报错、无文字报错、超长截断+truncated 标记。

### 4.4 API 路由测试（28 tests）

#### 基础路由 (`test_routes_basic.py`) — 10 tests

| 路由 | 测试 |
|------|------|
| `GET /` | 返回 HTML、200 状态码 |
| `GET /config` | 返回 JSON、`requiresPassphrase` 是 bool |
| `POST /verify-passphrase` | 正确暗号→200、错误暗号→403、空列表→任何密码通过 |
| `POST /api/log-error` | 正常提交→200、空 errors→200 |
| 静态文件 | `/static/script.js` 和 `/static/style.css` 可访问 |

#### 生成路由 (`test_routes_generate.py`) — 10 tests

所有 LLM 调用节点均通过 `mocker.patch` 替换为返回假数据的 async 函数。

| 路由 | 关键验证 |
|------|---------|
| `POST /generate` | SSE 流返回、空 topic、带 settings |
| `POST /generate/copy` | SSE 流 |
| `POST /generate/animation` | 缺/空 copy_json→400、有效→200 |
| `POST /generate/full` | 缺/空 topic→400、有效→200 |
| `POST /paper/generate` | 缺文件→422 |

#### 分享路由 (`test_routes_share.py`) — 8 tests

端到端验证：创建→读取→密码验证的完整流程。包括永久有效、错误密码返回 403、不存在返回 404。

---

## 5. Docker 集成

### `docker-compose.test.yml`

```yaml
services:
  test:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: animation-test
    command: >
      sh -c "pip install pytest pytest-asyncio pytest-mock httpx &&
             python -m pytest tests/ -v"
    environment:
      - PYTHONUNBUFFERED=1
```

复用生产 `Dockerfile`，额外安装测试依赖后运行全量测试。不修改生产镜像构建。

### 运行方式

```bash
# 本地 venv（零配置，自动拦截 credentials.json）
pytest tests/ -v

# 仅单元测试
pytest tests/unit/ -v

# 带覆盖率
pytest tests/ -v --cov=backend --cov=app --cov-report=term-missing

# Docker 内运行
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

---

## 6. 新增/修改文件清单

### 新增文件（20 个）

| 文件 | 说明 |
|------|------|
| `pytest.ini` | pytest 配置（testpaths、asyncio_mode、markers） |
| `docker-compose.test.yml` | Docker 测试环境 |
| `tests/fake_credentials.json` | 假凭证 |
| `tests/conftest.py` | 全局 fixtures + `builtins.open` 拦截 |
| `tests/helpers.py` | FakeChunk、FakeAIMessage、辅助生成器 |
| `tests/unit/test_thought_filter.py` | 22 tests |
| `tests/unit/test_models.py` | 31 tests |
| `tests/unit/test_html_postprocessor.py` | 41 tests |
| `tests/unit/test_prompts.py` | 29 tests |
| `tests/unit/test_routing.py` | 21 tests |
| `tests/graph/test_graph_compilation.py` | 12 tests |
| `tests/graph/test_validate.py` | 19 tests |
| `tests/graph/test_assemble.py` | 7 tests |
| `tests/graph/test_postprocess_node.py` | 4 tests |
| `tests/integration/test_config.py` | 13 tests |
| `tests/integration/test_share.py` | 18 tests |
| `tests/integration/test_pdf.py` | 7 tests |
| `tests/api/test_routes_basic.py` | 10 tests |
| `tests/api/test_routes_generate.py` | 10 tests |
| `tests/api/test_routes_share.py` | 8 tests |

### 修改文件（1 个）

| 文件 | 变更 |
|------|------|
| `requirements.txt` | 追加 `pytest>=8.0,<9.0`、`pytest-asyncio>=0.24.0`、`pytest-mock>=3.14.0`、`httpx>=0.27.0` |

---

## 7. CI 建议（可选）

可在 GitHub Actions 或腾讯云 CODING 中添加测试步骤：

```yaml
# .github/workflows/test.yml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run tests
      run: docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

---

## 8. 后续建议

1. **添加 `pytest-cov`**：在 `requirements.txt` 中追加 `pytest-cov>=5.0`，CI 中生成覆盖率报告
2. **Playwright/视频导出测试**：当前 VideoExporter 相关逻辑未直接测试（需要真实 Chromium + FFmpeg），可添加 `@pytest.mark.slow` 的容器化端到端测试
3. **`pyproject.toml` 迁移**：将 `pytest.ini` 和 `requirements.txt` 的测试依赖迁移到 `pyproject.toml` 的 `[project.optional-dependencies] test` 和 `[tool.pytest.ini_options]` 段
4. **pre-commit hook**：添加 `pre-commit` 配置，在提交前自动运行 `pytest tests/unit/`
