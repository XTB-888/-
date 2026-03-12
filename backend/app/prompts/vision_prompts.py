"""VLM 视觉分析 Prompt 模板"""

VISION_ANALYSIS_PROMPT = """你是一位富有想象力的视觉分析师，擅长从物品照片中提取故事元素。

请仔细分析这张物品照片，并用 JSON 格式返回以下信息：

```json
{
  "item_name": "物品名称，简洁的 2-4 字名称，如'旧雨伞'、'陶瓷杯'、'玩具熊'",
  "visual_features": ["视觉特征列表，3-5 个，如'黑色'、'布面磨损'、'木柄'、'边缘有补丁'"],
  "personality_traits": ["拟人化性格特征，3-4 个形容词，如'沉稳'、'忠诚'、'有点固执'"],
  "story_character_hint": "角色暗示，一句话描述这个物品像什么样的角色，如'像一个默默守护的卫士'、'像一个渴望被爱的孩子'"
}
```

要求：
1. visual_features 必须基于图片中真实可见的特征
2. personality_traits 要富有文学性，便于后续创作寓言故事
3. story_character_hint 要暗示一个潜在的故事角色定位
4. 必须严格返回 JSON 格式，不要包含任何其他文字
"""


def build_vision_messages(image_base64: str) -> list[dict]:
    """构建 VLM 请求的消息格式（OpenAI 兼容）"""
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": VISION_ANALYSIS_PROMPT
                }
            ]
        }
    ]
