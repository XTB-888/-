"""VLM 视觉分析服务"""
import base64
import json
import re
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from app.config import settings
from app.models.schemas import VisionAnalysis
from app.prompts.vision_prompts import build_vision_messages


class VisionService:
    """视觉分析服务，调用 VLM 模型分析物品图片"""

    def __init__(self):
        self.client = ChatOpenAI(
            model=settings.vlm_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=0.7,
            max_tokens=1024,
        )

    @staticmethod
    def encode_image(image_path: str) -> str:
        """将图片文件转为 base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def extract_json(text: str) -> Optional[dict]:
        """从模型输出中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 ``` ... ``` 代码块
        json_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 { ... } 大括号内容
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def analyze(self, image_path: str) -> VisionAnalysis:
        """
        分析图片，返回结构化视觉分析结果

        Args:
            image_path: 图片文件路径

        Returns:
            VisionAnalysis: 结构化分析结果
        """
        # 1. 编码图片
        image_base64 = self.encode_image(image_path)

        # 2. 构建消息
        messages = build_vision_messages(image_base64)

        # 3. 调用 VLM
        response = self.client.invoke(messages)
        content = response.content

        # 4. 提取 JSON
        data = self.extract_json(content)
        if data is None:
            raise ValueError(f"无法从模型输出中提取 JSON: {content[:200]}")

        # 5. 验证并返回
        return VisionAnalysis(
            item_name=data.get("item_name", "神秘物品"),
            visual_features=data.get("visual_features", []),
            personality_traits=data.get("personality_traits", []),
            story_character_hint=data.get("story_character_hint", "一个普通的物品"),
        )

    def analyze_with_fallback(self, image_path: str) -> VisionAnalysis:
        """带 fallback 的分析，失败时返回默认值"""
        try:
            return self.analyze(image_path)
        except Exception as e:
            # Fallback：基于文件名生成默认分析
            filename = Path(image_path).stem
            return VisionAnalysis(
                item_name=filename[:10] or "神秘物品",
                visual_features=["独特的外观"],
                personality_traits=["神秘", "独特"],
                story_character_hint="像一个等待被发现的宝藏",
            )


# 单例
vision_service = VisionService()
