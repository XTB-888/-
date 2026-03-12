"""测试故事生成链（OutlineChain + NarrativeChain）"""
import json
from app.services.story_service import story_service
from app.models.schemas import VisionAnalysis, StoryStyle


def test_story_generation():
    """测试完整故事生成"""
    print("=" * 60)
    print("测试故事生成链")
    print("=" * 60)

    # 模拟 VLM 分析结果
    vision = VisionAnalysis(
        item_name="旧雨伞",
        visual_features=["黑色", "布面磨损", "木柄", "边缘有补丁"],
        personality_traits=["沉稳", "忠诚", "有点固执"],
        story_character_hint="像一个默默守护的卫士",
    )

    # 模拟 RAG 检索结果
    templates = [
        {
            "title": "老橡树与小草",
            "theme": "陪伴与成长",
            "conflict_type": "弱小者的觉醒",
            "emotion_arc": "孤独→温暖→挑战→成长",
            "ending_type": "温馨圆满",
            "synopsis": "一棵老橡树在山坡上独自站了很多年，直到一株小草在它脚下生根。暴风雨中它们互相支撑。",
            "moral": "最微小的存在也能给予最伟大的守护。",
            "keywords": ["守护", "陪伴", "坚韧", "共生"],
        },
    ]

    style = StoryStyle.HEALING

    print(f"\n物品: {vision.item_name}")
    print(f"风格: {style.value}")
    print(f"参考模板: {templates[0]['title']}")

    try:
        print("\n--- 生成中（大纲 + 故事）... ---\n")
        outline, story, timings = story_service.generate_full(
            vision=vision,
            style=style,
            templates=templates,
        )

        print("✅ 大纲生成成功!")
        print(f"  主题: {outline.theme}")
        for p in outline.pages:
            print(f"  第{p.page}页: {p.scene} | {p.plot} | {p.emotion}")
            if p.visual_prompt:
                print(f"    [插图] {p.visual_prompt[:80]}...")

        print(f"\n✅ 故事生成成功!")
        print(f"  标题: {story.title}")
        print(f"  全文长度: {len(story.full_text)} 字")
        print(f"\n--- 完整故事 ---\n")
        print(story.full_text)

        print(f"\n--- 分页文本 ---")
        for i, text in enumerate(story.page_texts, 1):
            print(f"\n第{i}页 ({len(text)}字):")
            print(text[:200] + ("..." if len(text) > 200 else ""))

        print(f"\n--- 耗时 ---")
        for k, v in timings.items():
            print(f"  {k}: {v}s")

    except Exception as e:
        print(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_story_generation()
