"""FableLens API 路由 - LangGraph 版"""
import uuid
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.schemas import (
    GenerateResponse, GenerationTask,
    HealthResponse, StoryStyle, TaskStatus,
)
from app.config import settings
from app.chains.fablelens_graph import run_pipeline

router = APIRouter()

# 内存中的任务存储
tasks: dict[str, GenerationTask] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse()


@router.get("/api/eval-results")
async def get_eval_results():
    """获取最新评测结果"""
    import json
    eval_path = Path("C:/Users/monarch/fablelens/backend/data/eval_results.json")
    if eval_path.exists():
        with open(eval_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@router.post("/api/generate", response_model=GenerateResponse)
async def generate_story(
    file: UploadFile = File(..., description="物品照片"),
    style: str = Form(..., description="故事风格: 治愈/冒险/暗黑"),
):
    """
    上传物品照片 + 选择风格 → LangGraph 驱动完整 pipeline
    VLM → RAG → Outline → Narrative → Image → QualityCheck
    """
    # 1. 验证风格
    try:
        story_style = StoryStyle(style)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的风格: {style}，可选: 治愈/冒险/暗黑")

    # 2. 保存上传文件
    settings.ensure_dirs()
    task_id = str(uuid.uuid4())[:8]
    file_ext = Path(file.filename).suffix if file.filename else ".jpg"
    save_path = settings.upload_dir / f"{task_id}{file_ext}"

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # 3. 创建任务记录
    task = GenerationTask(
        task_id=task_id,
        status=TaskStatus.ANALYZING,
        style=story_style,
        image_path=str(save_path),
    )
    tasks[task_id] = task

    # 4. 运行 LangGraph pipeline
    t0 = time.time()
    try:
        final_state = run_pipeline(
            task_id=task_id,
            image_path=str(save_path),
            style=story_style,
        )

        # 5. 从 final_state 提取结果
        task.vision_analysis = final_state.get("vision")
        task.story_outline = final_state.get("outline")
        task.story = final_state.get("story")
        task.image_urls = final_state.get("image_urls", [])
        task.step_timings = final_state.get("step_timings", {})
        task.step_timings["pipeline_total"] = round(time.time() - t0, 2)

        status_str = final_state.get("status", "")
        if status_str.startswith("completed"):
            task.status = TaskStatus.COMPLETED
        elif "failed" in status_str:
            task.status = TaskStatus.FAILED
            task.error_message = final_state.get("error", "未知错误")
        else:
            task.status = TaskStatus.COMPLETED

        # 质量检查信息
        if not final_state.get("quality_passed", True):
            task.error_message = final_state.get("error", "")

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error_message = f"Pipeline 执行失败: {str(e)}"
        task.step_timings["pipeline_total"] = round(time.time() - t0, 2)

    return _build_response(task)


@router.get("/api/task/{task_id}", response_model=GenerateResponse)
async def get_task(task_id: str):
    """查询任务状态"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _build_response(task)


def _build_response(task: GenerationTask) -> GenerateResponse:
    """统一构建响应"""
    return GenerateResponse(
        task_id=task.task_id,
        status=task.status,
        vision_analysis=task.vision_analysis,
        story=task.story,
        story_outline=task.story_outline,
        image_urls=task.image_urls,
        error_message=task.error_message,
        step_timings=task.step_timings,
    )
