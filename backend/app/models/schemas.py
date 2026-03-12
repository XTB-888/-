"""FableLens 核心数据模型（Pydantic Schema）"""
from __future__ import annotations
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# 枚举
# ============================================================

class StoryStyle(str, Enum):
    """故事风格"""
    HEALING = "治愈"
    ADVENTURE = "冒险"
    DARK = "暗黑"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    RETRIEVING = "retrieving"
    WRITING = "writing"
    ILLUSTRATING = "illustrating"
    CHECKING = "checking"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================
# 视觉分析结果
# ============================================================

class VisionAnalysis(BaseModel):
    """VLM 对物品图片的结构化分析"""
    item_name: str = Field(..., description="物品名称，如'旧雨伞'")
    visual_features: list[str] = Field(..., description="视觉特征列表，如['黑色','布面磨损']")
    personality_traits: list[str] = Field(..., description="拟人化性格特征，如['沉稳','忠诚']")
    story_character_hint: str = Field(..., description="角色暗示，如'像一个守护者'")


# ============================================================
# 故事大纲与分镜
# ============================================================

class StoryboardPage(BaseModel):
    """单页分镜"""
    page: int = Field(..., description="页码 1-4")
    scene: str = Field(..., description="场景描述，如'雨夜街角'")
    plot: str = Field(..., description="本页剧情摘要")
    emotion: str = Field(..., description="情绪基调，如'温暖而忧伤'")
    visual_prompt: str = Field("", description="用于生成插图的英文 prompt")


class StoryOutline(BaseModel):
    """故事大纲"""
    theme: str = Field(..., description="主题，如'陪伴与成长'")
    pages: list[StoryboardPage] = Field(..., description="4 页分镜")


# ============================================================
# 完整故事
# ============================================================

class GeneratedStory(BaseModel):
    """生成的完整故事"""
    title: str = Field(..., description="故事标题")
    full_text: str = Field(..., description="完整故事文本 500-800 字")
    page_texts: list[str] = Field(..., description="按页拆分的故事文本，共 4 段")


# ============================================================
# 生成任务
# ============================================================

class GenerationTask(BaseModel):
    """一次完整的生成任务"""
    task_id: str = Field(..., description="任务唯一 ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    style: StoryStyle = Field(..., description="故事风格")
    image_path: str = Field("", description="上传图片路径")

    # 各阶段产物
    vision_analysis: Optional[VisionAnalysis] = None
    story_outline: Optional[StoryOutline] = None
    story: Optional[GeneratedStory] = None
    image_urls: list[str] = Field(default_factory=list, description="4 张插图 URL/路径")

    # 元信息
    error_message: str = ""
    step_timings: dict[str, float] = Field(default_factory=dict, description="各步骤耗时(秒)")


# ============================================================
# API 请求/响应
# ============================================================

class GenerateRequest(BaseModel):
    """前端发起生成请求"""
    style: StoryStyle = Field(..., description="故事风格")


class GenerateResponse(BaseModel):
    """生成结果响应"""
    task_id: str
    status: TaskStatus
    vision_analysis: Optional[VisionAnalysis] = None
    story: Optional[GeneratedStory] = None
    story_outline: Optional[StoryOutline] = None
    image_urls: list[str] = Field(default_factory=list)
    error_message: str = ""
    step_timings: dict[str, float] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "0.1.0"
    project: str = "FableLens"
