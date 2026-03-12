"""故事生成 Prompt 模板（v2 优化版）"""

OUTLINE_SYSTEM_PROMPT = """你是一位资深的寓言故事编剧，擅长将物品拟人化并创作富有哲理的短篇寓言。
你的作品兼具文学性与哲思深度，情绪弧线清晰，每个故事都有独特的寓意。"""

OUTLINE_USER_PROMPT = """请根据以下信息，为一个 4 页绘本创作故事大纲。

## 物品信息（来自视觉分析）
- 物品名称：{item_name}
- 视觉特征：{visual_features}
- 拟人性格：{personality_traits}
- 角色定位：{story_character_hint}

## 故事风格
{style}

## 参考寓言模板（从模板库检索，仅供参考，不要照搬）
{rag_context}

## 输出要求
请严格按以下 JSON 格式输出，不要包含任何其他文字：

```json
{{
  "theme": "故事主题，2-6个字",
  "pages": [
    {{
      "page": 1,
      "scene": "场景名称，2-6个字",
      "plot": "本页剧情摘要，20-40字",
      "emotion": "情绪基调，2-4个字",
      "visual_prompt": "用于生成插图的英文描述，50-80词，包含场景、角色、光线、氛围、画风（children book illustration style）"
    }},
    {{
      "page": 2,
      "scene": "...",
      "plot": "...",
      "emotion": "...",
      "visual_prompt": "..."
    }},
    {{
      "page": 3,
      "scene": "...",
      "plot": "...",
      "emotion": "...",
      "visual_prompt": "..."
    }},
    {{
      "page": 4,
      "scene": "...",
      "plot": "...",
      "emotion": "...",
      "visual_prompt": "..."
    }}
  ]
}}
```

## 创作要求
1. 物品「{item_name}」必须是故事主角，全程拟人化，赋予它人格和情感
2. 4 页结构：引入→转折→高潮→结局，4 页的 emotion 必须各不相同
3. 主题要有寓意深度，适合成人阅读，结尾要有点睛之笔
4. visual_prompt 必须是英文，描述具体画面，必须包含 "children book illustration, watercolor style" 风格词
5. 每页 visual_prompt 中的主角外观描述要保持一致（颜色、形态、特征），用相同的英文短语描述主角
6. 不要使用"从前"、"很久以前"等俗套开头
"""


NARRATIVE_SYSTEM_PROMPT = """你是一位才华横溢的寓言作家，文笔优美、富有诗意，擅长用简洁而有力的语言讲述深刻的故事。
你的文字有画面感，善用比喻和通感，让读者仿佛身临其境。"""

NARRATIVE_USER_PROMPT = """请根据以下故事大纲，撰写一篇完整的寓言故事。

## 物品信息
- 物品名称：{item_name}
- 视觉特征：{visual_features}
- 拟人性格：{personality_traits}
- 角色定位：{story_character_hint}

## 故事风格
{style}

## 故事大纲
主题：{theme}

第 1 页 - {scene_1}
剧情：{plot_1}
情绪：{emotion_1}

第 2 页 - {scene_2}
剧情：{plot_2}
情绪：{emotion_2}

第 3 页 - {scene_3}
剧情：{plot_3}
情绪：{emotion_3}

第 4 页 - {scene_4}
剧情：{plot_4}
情绪：{emotion_4}

## 输出要求
请严格按以下 JSON 格式输出，不要包含任何其他文字：

```json
{{
  "title": "故事标题，3-10个字，富有诗意",
  "full_text": "完整故事文本，500-800字，分段落书写，段落之间用\\n\\n分隔",
  "page_texts": [
    "第1页文本，120-200字，对应第1页大纲",
    "第2页文本，120-200字，对应第2页大纲",
    "第3页文本，120-200字，对应第3页大纲",
    "第4页文本，120-200字，对应第4页大纲"
  ]
}}
```

## 写作要求
1. 文笔优美，有文学性，适合朗读，善用比喻和通感
2. 物品「{item_name}」是主角，全程用"它"指代，赋予它思想和情感
3. 对话不超过全文的 20%，以叙述和描写为主
4. 结尾必须有点睛之笔，用一句话揭示寓意，但不说教
5. 每页文本独立成段，但整体连贯，情绪递进
6. full_text 是四页文本的完整连贯版本，用段落分隔
7. 每页至少 120 字，全文至少 500 字
8. 不要使用"从前"、"很久以前"等俗套开头
"""
