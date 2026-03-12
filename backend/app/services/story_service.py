"""故事生成服务 - OutlineChain + NarrativeChain"""
import json
import time
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.models.schemas import (
    VisionAnalysis, StoryStyle, StoryOutline, StoryboardPage,
    GeneratedStory,
)
from app.prompts.story_prompts import (
    OUTLINE_SYSTEM_PROMPT, OUTLINE_USER_PROMPT,
    NARRATIVE_SYSTEM_PROMPT, NARRATIVE_USER_PROMPT,
)
from app.services.vision_service import VisionService


class StoryService:
    """故事生成服务"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.text_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=0.85,
            max_tokens=4096,
        )

    @staticmethod
    def _build_rag_context(templates: list[dict]) -> str:
        """将 RAG 检索结果格式化为上下文"""
        if not templates:
            return "（无参考模板，请自由发挥）"

        lines = []
        for i, t in enumerate(templates[:3], 1):
            lines.append(
                f"模板{i}「{t['title']}」\n"
                f"  主题：{t['theme']} | 冲突：{t['conflict_type']}\n"
                f"  情绪弧线：{t['emotion_arc']}\n"
                f"  梗概：{t['synopsis']}\n"
                f"  寓意：{t['moral']}"
            )
        return "\n\n".join(lines)

    def generate_outline(
        self,
        vision: VisionAnalysis,
        style: StoryStyle,
        templates: list[dict],
    ) -> StoryOutline:
        """
        生成故事大纲（4 页分镜）

        Args:
            vision: VLM 视觉分析结果
            style: 故事风格
            templates: RAG 检索到的参考模板

        Returns:
            StoryOutline: 故事大纲
        """
        rag_context = self._build_rag_context(templates)

        prompt = OUTLINE_USER_PROMPT.format(
            item_name=vision.item_name,
            visual_features="、".join(vision.visual_features),
            personality_traits="、".join(vision.personality_traits),
            story_character_hint=vision.story_character_hint,
            style=style.value,
            rag_context=rag_context,
        )

        messages = [
            SystemMessage(content=OUTLINE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        content = response.content

        # 提取 JSON
        data = VisionService.extract_json(content)
        if data is None:
            raise ValueError(f"无法从大纲输出中提取 JSON: {content[:300]}")

        # 构建 StoryOutline
        pages = []
        for p in data.get("pages", []):
            pages.append(StoryboardPage(
                page=p.get("page", len(pages) + 1),
                scene=p.get("scene", ""),
                plot=p.get("plot", ""),
                emotion=p.get("emotion", ""),
                visual_prompt=p.get("visual_prompt", ""),
            ))

        # 确保有 4 页
        while len(pages) < 4:
            pages.append(StoryboardPage(
                page=len(pages) + 1,
                scene="续",
                plot="故事继续...",
                emotion="平静",
                visual_prompt="",
            ))

        return StoryOutline(
            theme=data.get("theme", "未命名主题"),
            pages=pages[:4],
        )

    def generate_narrative(
        self,
        vision: VisionAnalysis,
        style: StoryStyle,
        outline: StoryOutline,
    ) -> GeneratedStory:
        """
        根据大纲生成完整故事文本

        Args:
            vision: VLM 视觉分析结果
            style: 故事风格
            outline: 故事大纲

        Returns:
            GeneratedStory: 完整故事
        """
        prompt = NARRATIVE_USER_PROMPT.format(
            item_name=vision.item_name,
            visual_features="、".join(vision.visual_features),
            personality_traits="、".join(vision.personality_traits),
            story_character_hint=vision.story_character_hint,
            style=style.value,
            theme=outline.theme,
            scene_1=outline.pages[0].scene,
            plot_1=outline.pages[0].plot,
            emotion_1=outline.pages[0].emotion,
            scene_2=outline.pages[1].scene,
            plot_2=outline.pages[1].plot,
            emotion_2=outline.pages[1].emotion,
            scene_3=outline.pages[2].scene,
            plot_3=outline.pages[2].plot,
            emotion_3=outline.pages[2].emotion,
            scene_4=outline.pages[3].scene,
            plot_4=outline.pages[3].plot,
            emotion_4=outline.pages[3].emotion,
        )

        messages = [
            SystemMessage(content=NARRATIVE_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        content = response.content

        # 提取 JSON
        data = VisionService.extract_json(content)
        if data is None:
            raise ValueError(f"无法从故事输出中提取 JSON: {content[:300]}")

        # 确保 page_texts 有 4 段
        page_texts = data.get("page_texts", [])
        while len(page_texts) < 4:
            page_texts.append("...")

        return GeneratedStory(
            title=data.get("title", f"{vision.item_name}的故事"),
            full_text=data.get("full_text", "\n\n".join(page_texts)),
            page_texts=page_texts[:4],
        )

    def generate_full(
        self,
        vision: VisionAnalysis,
        style: StoryStyle,
        templates: list[dict],
    ) -> tuple[StoryOutline, GeneratedStory, dict]:
        """
        完整生成流程：大纲 → 故事

        Returns:
            (outline, story, timings)
        """
        timings = {}

        # Step 1: 生成大纲
        t0 = time.time()
        outline = self.generate_outline(vision, style, templates)
        timings["outline_generation"] = round(time.time() - t0, 2)

        # Step 2: 生成故事
        t0 = time.time()
        story = self.generate_narrative(vision, style, outline)
        timings["narrative_generation"] = round(time.time() - t0, 2)

        return outline, story, timings


# 单例
story_service = StoryService()
