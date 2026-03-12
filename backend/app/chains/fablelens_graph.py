"""FableLens LangGraph 工作流

完整 pipeline：
  upload → vision_analyze → rag_retrieve → outline_generate → narrative_generate → image_generate → quality_check → done
"""
import time
import uuid
from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END

from app.models.schemas import (
    VisionAnalysis, StoryStyle, StoryOutline, GeneratedStory, TaskStatus,
)
from app.services.vision_service import vision_service
from app.services.story_service import story_service
from app.services.image_service import image_service
from app.rag.fable_rag import fable_rag


# ============================================================
# State 定义
# ============================================================

class FableLensState(TypedDict):
    """工作流全局状态"""
    # 输入
    task_id: str
    image_path: str
    style: StoryStyle

    # 各阶段产物
    vision: Optional[VisionAnalysis]
    templates: list[dict]
    outline: Optional[StoryOutline]
    story: Optional[GeneratedStory]
    image_urls: list[str]

    # 控制
    status: str
    error: str
    retry_counts: dict[str, int]  # 各节点重试次数
    step_timings: dict[str, float]

    # 质量检查
    quality_passed: bool


# ============================================================
# 节点函数
# ============================================================

MAX_RETRIES = 2


def vision_analyze(state: FableLensState) -> dict:
    """Step 1: VLM 视觉分析"""
    t0 = time.time()
    retries = state.get("retry_counts", {}).get("vision", 0)

    try:
        if retries >= MAX_RETRIES:
            # 超过重试次数，使用 fallback
            result = vision_service.analyze_with_fallback(state["image_path"])
        else:
            result = vision_service.analyze(state["image_path"])

        timings = {**state.get("step_timings", {}), "vision_analyze": round(time.time() - t0, 2)}
        return {
            "vision": result,
            "status": "vision_done",
            "step_timings": timings,
        }

    except Exception as e:
        new_retries = {**state.get("retry_counts", {}), "vision": retries + 1}
        if retries + 1 >= MAX_RETRIES:
            # 最后一次用 fallback
            result = vision_service.analyze_with_fallback(state["image_path"])
            timings = {**state.get("step_timings", {}), "vision_analyze": round(time.time() - t0, 2)}
            return {
                "vision": result,
                "status": "vision_done",
                "retry_counts": new_retries,
                "step_timings": timings,
            }
        return {
            "status": "vision_retry",
            "error": str(e),
            "retry_counts": new_retries,
        }


def rag_retrieve(state: FableLensState) -> dict:
    """Step 2: RAG 检索寓言模板"""
    t0 = time.time()

    try:
        # 确保模板库已加载
        if fable_rag.collection is None or (fable_rag._use_chroma and fable_rag.collection.count() == 0):
            fable_rag.load_templates()

        templates = fable_rag.retrieve(
            vision=state["vision"],
            style=state["style"],
            top_k=5,
        )
    except Exception as e:
        print(f"⚠️ RAG 检索失败: {e}")
        templates = []

    timings = {**state.get("step_timings", {}), "rag_retrieve": round(time.time() - t0, 2)}
    return {
        "templates": templates,
        "status": "rag_done",
        "step_timings": timings,
    }


def outline_generate(state: FableLensState) -> dict:
    """Step 3: 生成故事大纲"""
    t0 = time.time()
    retries = state.get("retry_counts", {}).get("outline", 0)

    try:
        outline = story_service.generate_outline(
            vision=state["vision"],
            style=state["style"],
            templates=state.get("templates", []),
        )
        timings = {**state.get("step_timings", {}), "outline_generate": round(time.time() - t0, 2)}
        return {
            "outline": outline,
            "status": "outline_done",
            "step_timings": timings,
        }

    except Exception as e:
        new_retries = {**state.get("retry_counts", {}), "outline": retries + 1}
        if retries + 1 >= MAX_RETRIES:
            return {
                "status": "outline_failed",
                "error": f"大纲生成失败: {e}",
                "retry_counts": new_retries,
            }
        return {
            "status": "outline_retry",
            "error": str(e),
            "retry_counts": new_retries,
        }


def narrative_generate(state: FableLensState) -> dict:
    """Step 4: 生成完整故事"""
    t0 = time.time()
    retries = state.get("retry_counts", {}).get("narrative", 0)

    try:
        story = story_service.generate_narrative(
            vision=state["vision"],
            style=state["style"],
            outline=state["outline"],
        )
        timings = {**state.get("step_timings", {}), "narrative_generate": round(time.time() - t0, 2)}
        return {
            "story": story,
            "status": "narrative_done",
            "step_timings": timings,
        }

    except Exception as e:
        new_retries = {**state.get("retry_counts", {}), "narrative": retries + 1}
        if retries + 1 >= MAX_RETRIES:
            return {
                "status": "narrative_failed",
                "error": f"故事生成失败: {e}",
                "retry_counts": new_retries,
            }
        return {
            "status": "narrative_retry",
            "error": str(e),
            "retry_counts": new_retries,
        }


def image_generate(state: FableLensState) -> dict:
    """Step 5: 生成绘本插图"""
    t0 = time.time()

    outline = state.get("outline")
    if not outline:
        return {"image_urls": [], "status": "image_done"}

    visual_prompts = []
    for page in outline.pages:
        if page.visual_prompt:
            visual_prompts.append(page.visual_prompt)
        else:
            visual_prompts.append(
                f"{page.scene}, children book illustration, watercolor style, warm lighting"
            )

    try:
        if image_service.api_key and image_service.api_key != "sk-your-siliconflow-api-key-here":
            urls, img_timings = image_service.generate_storyboard(
                visual_prompts=visual_prompts,
                task_id=state["task_id"],
            )
            timings = {**state.get("step_timings", {}), **img_timings, "image_generate_total": round(time.time() - t0, 2)}
            return {
                "image_urls": urls,
                "status": "image_done",
                "step_timings": timings,
            }
        else:
            return {"image_urls": [], "status": "image_done"}

    except Exception as e:
        print(f"⚠️ 图像生成失败: {e}")
        timings = {**state.get("step_timings", {}), "image_generate_total": round(time.time() - t0, 2)}
        return {
            "image_urls": [],
            "status": "image_done",
            "step_timings": timings,
        }


def quality_check(state: FableLensState) -> dict:
    """Step 6: 质量自检"""
    t0 = time.time()
    issues = []

    story = state.get("story")
    outline = state.get("outline")
    vision = state.get("vision")

    # 检查故事长度
    if story:
        text_len = len(story.full_text)
        if text_len < 200:
            issues.append(f"故事过短({text_len}字)")
        if len(story.page_texts) < 4:
            issues.append(f"分页不足({len(story.page_texts)}页)")

    # 检查大纲完整性
    if outline:
        if len(outline.pages) < 4:
            issues.append(f"大纲页数不足({len(outline.pages)}页)")
        empty_prompts = sum(1 for p in outline.pages if not p.visual_prompt)
        if empty_prompts > 0:
            issues.append(f"{empty_prompts}页缺少 visual_prompt")

    # 检查图片
    image_urls = state.get("image_urls", [])
    empty_images = sum(1 for u in image_urls if not u)
    if empty_images > 0:
        issues.append(f"{empty_images}张插图生成失败")

    passed = len(issues) == 0
    timings = {**state.get("step_timings", {}), "quality_check": round(time.time() - t0, 2)}

    if issues:
        print(f"⚠️ 质量检查发现问题: {', '.join(issues)}")

    return {
        "quality_passed": passed,
        "status": "completed" if passed else "completed_with_issues",
        "error": "; ".join(issues) if issues else "",
        "step_timings": timings,
    }


# ============================================================
# 路由函数（条件边）
# ============================================================

def should_retry_vision(state: FableLensState) -> str:
    if state.get("status") == "vision_retry":
        return "vision_analyze"
    return "rag_retrieve"


def should_retry_outline(state: FableLensState) -> str:
    if state.get("status") == "outline_retry":
        return "outline_generate"
    if state.get("status") == "outline_failed":
        return END
    return "narrative_generate"


def should_retry_narrative(state: FableLensState) -> str:
    if state.get("status") == "narrative_retry":
        return "narrative_generate"
    if state.get("status") == "narrative_failed":
        return END
    return "image_generate"


# ============================================================
# 构建 Graph
# ============================================================

def build_fablelens_graph() -> StateGraph:
    """构建 FableLens 工作流图"""
    graph = StateGraph(FableLensState)

    # 添加节点
    graph.add_node("vision_analyze", vision_analyze)
    graph.add_node("rag_retrieve", rag_retrieve)
    graph.add_node("outline_generate", outline_generate)
    graph.add_node("narrative_generate", narrative_generate)
    graph.add_node("image_generate", image_generate)
    graph.add_node("quality_check", quality_check)

    # 设置入口
    graph.set_entry_point("vision_analyze")

    # 添加条件边（带重试）
    graph.add_conditional_edges("vision_analyze", should_retry_vision)
    graph.add_edge("rag_retrieve", "outline_generate")
    graph.add_conditional_edges("outline_generate", should_retry_outline)
    graph.add_conditional_edges("narrative_generate", should_retry_narrative)
    graph.add_edge("image_generate", "quality_check")
    graph.add_edge("quality_check", END)

    return graph


# 编译 Graph
fablelens_graph = build_fablelens_graph().compile()


def run_pipeline(task_id: str, image_path: str, style: StoryStyle) -> FableLensState:
    """
    运行完整 pipeline

    Args:
        task_id: 任务 ID
        image_path: 图片路径
        style: 故事风格

    Returns:
        最终状态
    """
    initial_state: FableLensState = {
        "task_id": task_id,
        "image_path": image_path,
        "style": style,
        "vision": None,
        "templates": [],
        "outline": None,
        "story": None,
        "image_urls": [],
        "status": "started",
        "error": "",
        "retry_counts": {},
        "step_timings": {},
        "quality_passed": False,
    }

    # 执行 Graph
    final_state = fablelens_graph.invoke(initial_state)
    return final_state
