"""
nodes/plan.py — 分析节点：对输入做一次小调用，产出结构化的理解。
"""
import json
import logging

from langchain_core.messages import SystemMessage, HumanMessage

from backend.graph import get_llm
from backend.graph.state import AnimationState
from backend.prompts import build_generation_setting_instructions

logger = logging.getLogger(__name__)

# ── analyze_topic 的 system prompt ──

_TOPIC_ANALYSIS_PROMPT = """你是一个科学动画的策划专家。分析以下概念，输出一个 JSON 对象。

## 输出格式
{
  "category": "物理/数学/计算机/生物/经济/医学/工程/天文/社科/其他",
  "difficulty": "入门/中级/专业",
  "core_idea": "一句话核心概念（20字以内）",
  "visual_metaphors": ["最适合的视觉比喻1", "视觉比喻2", "视觉比喻3"],
  "key_terms": ["关键术语1", "关键术语2", "关键术语3"],
  "narrative_angle": "反常识切入/数据震撼/好奇心驱动/实用场景/假设危机",
  "target_audience": "普通观众/学生/专业人士"
}

## 要求
- core_idea 要精炼到可以做成标题
- visual_metaphors 是具体可画的（如"多米诺骨牌"而非"因果链"）
- narrative_angle 选最能抓住注意力的角度
- 只输出 JSON，不要 Markdown，不要解释"""


async def analyze_topic(state: AnimationState) -> dict:
    """分析输入主题，产出结构化 outline。

    这是一个小调用（~100 token），为后续 generate_segments / generate_copy
    节点提供聚焦的上下文，压缩 prompt 体积、提升生成质量。
    """
    topic = state.get("topic", "")
    settings = state.get("settings", {})

    if not topic.strip():
        return {
            "outline": {"category": "未分类", "difficulty": "标准",
                         "core_idea": topic, "visual_metaphors": [],
                         "key_terms": [], "narrative_angle": "好奇心驱动"},
        }

    si = build_generation_setting_instructions(settings)
    llm = get_llm(temperature=0.6)

    messages = [
        SystemMessage(content=_TOPIC_ANALYSIS_PROMPT),
        HumanMessage(content=f"概念：{topic}\n讲解深度：{si['depth']}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content.strip()
        # 去除可能的 markdown 代码块
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:raw.rfind("```")].strip()
        outline = json.loads(raw)
        logger.info("analyze_topic 完成 | category=%s | difficulty=%s",
                    outline.get("category"), outline.get("difficulty"))
        return {"outline": outline}
    except json.JSONDecodeError as exc:
        logger.warning("analyze_topic JSON 解析失败: %s，使用默认 outline", exc)
        return {
            "outline": {
                "category": "未分类",
                "difficulty": "标准",
                "core_idea": topic,
                "visual_metaphors": [],
                "key_terms": [],
                "narrative_angle": "好奇心驱动",
            }
        }
    except Exception as exc:
        logger.warning("analyze_topic LLM 调用失败: %s，使用默认 outline", exc)
        return {
            "outline": {
                "category": "未分类",
                "difficulty": "标准",
                "core_idea": topic,
                "visual_metaphors": [],
                "key_terms": [],
                "narrative_angle": "好奇心驱动",
            }
        }


# ── analyze_paper 的 system prompt ──

_PAPER_ANALYSIS_PROMPT = """你是一个学术论文的科普解读专家。阅读以下论文内容，输出一个 JSON 对象。

## 输出格式
{
  "category": "研究领域（物理/计算机/生物/医学/...）",
  "difficulty": "入门/中级/专业",
  "core_idea": "论文核心贡献（一句话，20字以内）",
  "visual_metaphors": ["最适合表达核心贡献的视觉比喻1", "比喻2", "比喻3"],
  "key_terms": ["关键术语1", "术语2", "术语3", "术语4"],
  "narrative_angle": "反常识切入/数据震撼/好奇心驱动/实用场景",
  "paper_summary": "论文内容摘要（100字以内，覆盖背景-方法-结果-结论）",
  "method_highlights": ["方法亮点1", "方法亮点2"],
  "key_result": "最重要的实验结果"
}

## 要求
- 准确提取论文核心贡献，不要曲解
- visual_metaphors 要具体可画
- paper_summary 要足够精炼，供后续动画生成使用
- 只输出 JSON，不要 Markdown，不要解释"""


async def analyze_paper(state: AnimationState) -> dict:
    """分析论文全文，提炼结构化 outline。

    论文最长可达 120K 字符，此节点将其压缩为 ~300 字的 outline，
    后续 generate_segments 节点用此精简上下文替代原文，大幅减少 prompt 体积。
    """
    pdf_text = state.get("pdf_text", "")
    filename = state.get("pdf_filename", "")
    focus = state.get("focus", "")
    truncated = state.get("pdf_truncated", False)

    if not pdf_text.strip():
        return {
            "outline": {"category": "未分类", "core_idea": "论文解读",
                         "visual_metaphors": [], "key_terms": [],
                         "paper_summary": "未能提取论文内容"},
            "error": "论文内容为空",
        }

    si = build_generation_setting_instructions(state.get("settings", {}))
    llm = get_llm(temperature=0.5)

    focus_note = f"用户指定重点：{focus}\n" if focus else ""
    truncation_note = "注意：论文原文因长度限制已被截断。\n" if truncated else ""

    system_content = _PAPER_ANALYSIS_PROMPT
    user_content = (
        f"论文文件名：{filename}\n"
        f"{focus_note}"
        f"{truncation_note}"
        f"讲解深度：{si['depth']}\n\n"
        f"论文内容：\n{pdf_text}"
    )

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:raw.rfind("```")].strip()
        outline = json.loads(raw)
        logger.info("analyze_paper 完成 | category=%s | summary_len=%d",
                    outline.get("category"), len(outline.get("paper_summary", "")))
        return {"outline": outline}
    except json.JSONDecodeError as exc:
        logger.warning("analyze_paper JSON 解析失败: %s", exc)
        return {
            "outline": {
                "category": "未分类",
                "core_idea": filename,
                "visual_metaphors": [],
                "key_terms": [],
                "paper_summary": pdf_text[:200],
            }
        }
    except Exception as exc:
        logger.warning("analyze_paper LLM 调用失败: %s", exc)
        return {
            "outline": {
                "category": "未分类",
                "core_idea": filename,
                "visual_metaphors": [],
                "key_terms": [],
                "paper_summary": pdf_text[:200],
            }
        }
