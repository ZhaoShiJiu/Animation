# generate_copy 拆分方案

> 将当前 `generate_copy`（文案 + 动画指导）拆分为三个独立阶段：
> 1. `generate_narrative` — 纯五幕文案
> 2. `generate_direction` — 动画初指导
> 3. `generate_animation`（已有）— 具体视觉实现

---

## 一、目标架构对比

### 当前流程

```
analyze_topic → generate_copy ⇄ validate_copy → generate_animation ⇄ validate_animation → assemble → postprocess
                    ↑                                       ↑
              文案 + 动画指导混在一起                      已有，不改
```

### 拆分后流程

```
analyze_topic → generate_narrative ⇄ validate_narrative
                    ↓
              generate_direction ⇄ validate_direction
                    ↓
              generate_animation ⇄ validate_animation
                    ↓
              assemble → postprocess
```

每个节点一次 LLM 调用、每个校验节点独立重试循环（最多 2 次）。

---

## 二、数据模型变更

### 2.1 新增 `NarrativeAct`（纯文案）

```python
class NarrativeAct(BaseModel):
    """单个五幕的纯文案——不含任何视觉描述。"""
    act: int = Field(ge=1, le=5)
    name: str                                    # 幕名
    goal: str                                    # 该幕目标（≤30字）
    duration_hint: int = Field(ge=3, le=30)      # 建议时长（秒）
    method_used: str                             # 叙事手法
    narration: str                               # 中文旁白（≤35字/句）
    narration_en: str = ""                       # 英文旁白
    on_screen_text: str                          # 画面大字（≤10字）
    emotion: str = ""                            # 该幕画面情绪


class NarrativeOutput(BaseModel):
    """LLM 输出的顶层文案结构。"""
    narrative_type: str = "problem_conflict"
    title: str
    total_duration_hint: int = 60
    acts: list[NarrativeAct] = Field(min_length=5, max_length=5)
```

### 2.2 新增 `DirectionAct`（动画指导）

```python
class DirectionAct(BaseModel):
    """单个五幕的结构化动画指导——每项独立字段，不再是一段自由文本。"""
    act: int = Field(ge=1, le=5)

    # 构图
    composition: str                             # 元素位置（居中/偏左/网格分布）
    main_element: str                            # 画面核心元素描述

    # 颜色
    bg_color: str                                # 背景色 hex
    primary_color: str                           # 主文字/图形色 hex
    accent_color: str                            # 强调色 hex

    # 动效
    easing: str                                  # 缓动函数名（power2.out / back.out(1.7) / ...）
    entrance_direction: str                      # 入场方向（下方/左侧/缩放/透明度）
    entrance_duration_range: str                 # 入场时长范围（如 "0.4–0.6s"）
    stagger: str = ""                            # 逐项延迟（如 "0.12s"）

    # 镜头
    camera_movement: str                         # 镜头运动（推近/拉远/平移/固定）

    # 视觉手法
    visual_technique: str                        # 该幕使用的核心视觉手法
    svg_suggestion: str = ""                     # SVG 建议（形状/结构描述）

    # 过渡
    transition_from_previous: str = ""           # 与前一幕的过渡方式


class DirectionOutput(BaseModel):
    """LLM 输出的顶层动画指导结构。"""
    visual_style: str = "cinematic"
    color_palette_flow: str                      # 五幕色彩流变描述
    acts: list[DirectionAct] = Field(min_length=5, max_length=5)
```

### 2.3 AnimationState 新增字段

```python
class AnimationState(TypedDict, total=False):
    # ... 现有字段保持不变 ...

    # 新增
    narrative_json: dict              # generate_narrative 产出
    narrative_valid: bool
    direction_json: dict              # generate_direction 产出
    direction_valid: bool
```

### 2.4 `AnimationSegment`（已有）保持不变

`generate_animation` 继续产出 `segments`（title / subZh / visualSVG / steps / compareBefore 等字段），Pydantic 模型 `AnimationOutput` 不变。

---

## 三、Prompt 设计

### 3.1 `generate_narrative` 的 system prompt

**职责**：只做文案，引用五幕模板但不涉及任何视觉内容。

```
你是采用「问题冲突型」叙事结构的科学动画编剧。只输出纯文案，不涉及视觉设计。

## 五幕模板
第一幕·认知爆破：反常识/数据震撼切入，一句话抓注意力
第二幕·延迟满足：制造疑问，强化错误认知，让观众好奇
第三幕·层层揭秘：一问一答，信息量逐级递增
第四幕·高潮揭晓：颠覆认知，揭示核心原理
第五幕·记忆钉：金句总结，留下传播点

## 输入
- 主题：{topic}
- 讲解深度：{depth}
- 总时长：约 {duration_sec} 秒

## 输出格式（纯 JSON）
{
  "narrative_type": "problem_conflict",
  "title": "...",
  "total_duration_hint": 60,
  "acts": [
    {
      "act": 1,
      "name": "认知爆破",
      "goal": "3秒抓住注意力",
      "duration_hint": 8,
      "method_used": "反常识",
      "narration": "中文旁白",
      "narration_en": "English",
      "on_screen_text": "大字≤10字",
      "emotion": "紧张、震惊"
    },
    ...
  ]
}

## 要求
- 旁白口语化，中文每句≤35字
- 英文为中文准确翻译
- on_screen_text 与旁白互补不重复
- 输出纯 JSON，不要 Markdown
```

### 3.2 `generate_direction` 的 system prompt

**职责**：基于文案产出结构化的动画指导。

```
你是动画视觉导演。根据已有文案，为每一幕设计具体的动画方案。
请严格遵守对应的五幕动效设计语言。

## 五幕动效设计语言（Motion Design Language）

第一幕「认知爆破」— 冲击入场
  easing: back.out(1.7) 或 elastic.out(1,0.3)
  entrance: 下方弹入（y:80→0, scale:0.8→1.0）
  duration: 0.4–0.6s, stagger: 0.05s
  camera: 推近（scale 1.0→1.05）
  technique: 大号文字过冲回弹
  color: 高对比红/橙/深色→快速切明亮

第二幕「延迟满足」— 悬疑慢揭
  easing: power2.inOut
  entrance: 透明度渐变（0→0.6→1），模糊到清晰
  duration: 1.0–1.5s, stagger: 0.3s
  camera: 固定
  technique: filter:blur→0
  color: 冷灰紫（#7C3AED 系）

第三幕「层层揭秘」— 信息阶梯
  easing: power3.out
  entrance: 左侧滑入（x:-30→0）
  duration: 0.5–0.8s, stagger: 0.12s
  camera: 微平移
  technique: 每层揭示后前层变暗，连接线延伸
  color: 清爽蓝（#2563EB 系）

第四幕「高潮揭晓」— 认知翻转
  easing: power4.out
  entrance: 缩放（1.0→1.15）+ glow
  duration: 0.6–1.0s
  camera: 推近聚焦
  technique: 旧认知淡出+缩小，新认知放大+外发光
  color: 蓝→绿过渡（#059669 系）

第五幕「记忆钉」— 优雅定格
  easing: power4.out
  entrance: 缩放（0.95→1.0, y:30→0）
  duration: 1.2–1.8s
  camera: 拉远收束
  technique: 金句居中放大，装饰元素收缩淡出，最终定格≥2s
  color: 暖金/琥珀（#D97706 系）

## 输入
{完整的 narrative_json}

## 输出格式（纯 JSON）
{
  "visual_style": "cinematic",
  "color_palette_flow": "红→紫→蓝→绿→金",
  "acts": [
    {
      "act": 1,
      "composition": "画面中央偏上，问号图形旋转",
      "main_element": "大号倒计时数字",
      "bg_color": "#1a1a2e",
      "primary_color": "#DC2626",
      "accent_color": "#F97316",
      "easing": "back.out(1.7)",
      "entrance_direction": "下方弹入",
      "entrance_duration_range": "0.4–0.6s",
      "stagger": "0.05s",
      "camera_movement": "推近",
      "visual_technique": "大号文字过冲回弹",
      "svg_suggestion": "大号感叹号或警示三角",
      "transition_from_previous": ""
    },
    ...
  ]
}

## 要求
- 严格遵守每幕对应的动效语言
- 颜色使用指定的 hex 色系
- 输出纯 JSON，不要 Markdown
```

### 3.3 `generate_animation`（已有）按需微调

当前 prompt 已经工作良好。输入改为同时接收 `narrative_json` + `direction_json`，让 LLM 有完整的文案+指导上下文来生成具体 SVG/steps/compare 等视觉内容。无需大改。

---

## 四、节点实现

### 4.1 新文件 `backend/graph/nodes/generate_narrative.py`

```python
async def generate_narrative(state: AnimationState) -> dict:
    topic = state.get("topic", "")
    settings = state.get("settings", {})
    outline = state.get("outline", {})
    feedback = state.get("validation_feedback", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count > max_retries:
        return {"error": "文案重试超限", "narrative_valid": False}

    system_prompt = _build_narrative_system_prompt(topic, settings, outline)
    messages = [SystemMessage(content=system_prompt)]

    user_content = f"请生成五幕文案：{topic}"
    if feedback:
        user_content = f"## ⚠️ 修正\n{feedback}\n\n---\n\n{user_content}"
    messages.append(HumanMessage(content=user_content))

    llm = get_llm(temperature=0.7)
    stream_ctx = get_stream_context()

    try:
        full_response = ""
        thought_filter = ThoughtProcessFilter()
        async for chunk in llm.astream(messages, response_format={"type": "json_object"}):
            visible = thought_filter.feed(chunk.content)
            if visible:
                full_response += visible
                if stream_ctx:
                    stream_ctx.push_token(visible)

        remaining = thought_filter.flush()
        if remaining:
            full_response += remaining
            if stream_ctx:
                stream_ctx.push_token(remaining)

        narrative_json = json.loads(full_response)
        logger.info("generate_narrative 完成 | title=%s", narrative_json.get("title"))
        return {"narrative_json": narrative_json}

    except json.JSONDecodeError as exc:
        return {"narrative_json": {}, "error": f"JSON 解析失败: {exc}"}
    except (ConnectionError, TimeoutError, ValueError) as exc:
        return {"narrative_json": {}, "error": f"LLM 调用失败: {exc}"}
```

### 4.2 新文件 `backend/graph/nodes/generate_direction.py`

结构与 `generate_narrative` 相同，差异点：
- `temperature=0.6`（比文案低，指导需要更精确）
- system prompt 用 3.2 节的模板
- 输入包含完整的 `narrative_json`

### 4.3 校验节点 `backend/graph/nodes/validate.py` 新增

```python
async def validate_narrative(state: AnimationState) -> dict:
    """Pydantic NarrativeOutput 校验。"""
    narrative_json = state.get("narrative_json", {})
    retry_count = state.get("retry_count", 0)

    if not narrative_json:
        return {
            "narrative_valid": False,
            "validation_feedback": "未输出任何 JSON，请输出完整的五幕文案。",
            "retry_count": retry_count + 1,
        }

    try:
        NarrativeOutput.model_validate(narrative_json)
        logger.info("validate_narrative 通过 | acts=%d", len(narrative_json.get("acts", [])))
        return {"narrative_valid": True, "validation_feedback": None, "retry_count": 0}
    except ValidationError as exc:
        # 生成精确到字段的修正指令（同现有逻辑）
        ...


async def validate_direction(state: AnimationState) -> dict:
    """Pydantic DirectionOutput 校验。"""
    # 同 validate_narrative 结构
    ...
```

### 4.4 路由 `backend/graph/edges/routing.py` 新增

```python
def after_validate_narrative(state: AnimationState) -> str:
    if state.get("narrative_valid"):
        return TOKEN_PASSED
    return TOKEN_RETRY if _retry_left(state) else TOKEN_ABORT


def after_validate_direction(state: AnimationState) -> str:
    if state.get("direction_valid"):
        return TOKEN_PASSED
    return TOKEN_RETRY if _retry_left(state) else TOKEN_ABORT
```

---

## 五、图结构变更

### 5.1 `two_stage_graph.py`（主图，影响最大）

```
当前：
  analyze → generate_copy ⇄ validate_copy → generate_animation ⇄ validate_animation → assemble → postprocess

拆分后：
  analyze → generate_narrative ⇄ validate_narrative
              ↓
            generate_direction ⇄ validate_direction
              ↓
            generate_animation ⇄ validate_animation
              ↓
            assemble → postprocess
```

三层独立重试循环。新增 4 个节点、2 个条件边。

### 5.2 `copy_graph.py`（仅文案图）

```
当前：
  analyze → generate_copy ⇄ validate_copy → END

拆分后：
  analyze → generate_narrative ⇄ validate_narrative → END
```

### 5.3 `topic_graph.py`、`paper_graph.py`、`animation_graph.py`

不涉及拆分，保持不变。

---

## 六、SSE 流式节点名调整

```python
# sse_adapter.py
_STREAMING_NODES = {
    "generate_narrative",    # 新增
    "generate_direction",    # 新增
    "generate_segments",
    "generate_copy",         # 可逐步废弃
    "generate_animation",
}
```

前端不需要任何改动——收到的仍然是 `{"token": "..."}` SSE 事件，只是分三个阶段依次流式输出。

---

## 七、前端影响

| 项目 | 变更 |
|------|------|
| SSE 协议 | 不变 |
| 文案评审卡片 | 文案和动画指导分开显示——第一阶段出文案卡片（可编辑+确认），第二阶段出动画指导卡片（可编辑+确认），第三阶段出动画播放器 |
| 编辑能力 | 两个阶段独立可编辑，修改文案后只重新生成指导+动画，修改指导后只重新生成动画 |
| 重新生成 | 支持"仅重作文案"/"仅重做指导"/"仅重做动画"三个粒度 |

### 前端新增 UI 建议

在 `copy-review-template` 之外新增一个 `direction-review-template`：

- 展示每幕的 easing / entrance / camera / color 等字段
- 支持编辑（类似文案编辑的 span→input 切换）
- "确认指导，生成动画"按钮

---

## 八、文件清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/graph/nodes/generate_narrative.py` | 纯文案生成节点 |
| `backend/graph/nodes/generate_direction.py` | 动画指导生成节点 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/models.py` | 新增 `NarrativeAct`、`NarrativeOutput`、`DirectionAct`、`DirectionOutput` |
| `backend/graph/state.py` | 新增 `narrative_json`、`narrative_valid`、`direction_json`、`direction_valid` |
| `backend/graph/nodes/validate.py` | 新增 `validate_narrative`、`validate_direction` |
| `backend/graph/edges/routing.py` | 新增 `after_validate_narrative`、`after_validate_direction` |
| `backend/graph/graphs/two_stage_graph.py` | 重构为三阶段 |
| `backend/graph/graphs/copy_graph.py` | 换用新节点 |
| `backend/graph/sse_adapter.py` | 更新 `_STREAMING_NODES` |
| `backend/prompts.py` | 新增 `build_narrative_system_prompt()`、`build_direction_system_prompt()` |
| `frontend/static/script.js` | 三阶段 UI（文案评审→指导评审→动画播放） |
| `frontend/templates/index.html` | 新增 `direction-review-template` |
| `frontend/static/style.css` | 新卡片样式 |

### 可废弃文件（Phase 3）

| 文件 | 说明 |
|------|------|
| `backend/graph/nodes/generate_copy.py` | 被 `generate_narrative` + `generate_direction` 替代 |
| `backend/prompts.py` 中的 `build_copy_system_prompt()` | 被新 prompt 函数替代 |

---

## 九、LLM 调用次数与延迟估算

| 图 | 当前调用次数 | 拆分后调用次数 |
|----|-------------|---------------|
| `copy_graph` | 2（analyze + copy） | 2（analyze + narrative） |
| `two_stage_graph` | 3（analyze + copy + animation） | 4（analyze + narrative + direction + animation） |
| `topic_graph` | 2（analyze + segments） | 不变 |
| `paper_graph` | 2（analyze + segments） | 不变 |

**延迟估算**（假设单次 LLM 调用 15-30s）：
- `two_stage_graph`：当前 ~45-90s → 拆分后 ~60-120s
- 增加了约 33% 的总延迟

---

## 十、迁移策略

| 阶段 | 内容 | 风险 |
|------|------|------|
| **Phase 1** | 新增模型、节点、校验、路由；新建 `three_stage_graph.py`，挂载到新路由 `/generate/full/v3`；旧路由保留 | 零风险，新旧并行 |
| **Phase 2** | 前端切到 v3 路由，新增三阶段 UI，观察一周 | 低风险，可随时回滚 |
| **Phase 3** | 删除 `generate_copy.py`、废弃 prompt 函数、`/generate/full` 切到新图 | 清理性改动 |
