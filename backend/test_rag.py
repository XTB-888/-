"""测试 RAG 寓言模板检索"""
from app.rag.fable_rag import fable_rag
from app.models.schemas import VisionAnalysis, StoryStyle


def test_rag():
    """测试 RAG 检索"""
    print("=" * 60)
    print("测试 RAG 寓言模板检索")
    print("=" * 60)

    # 1. 加载模板库
    print("\n1. 加载模板库...")
    try:
        count = fable_rag.load_templates()
        print(f"✅ 模板库加载完成，共 {count} 条")
    except Exception as e:
        print(f"⚠️ 模板库加载失败（可能已加载或 API Key 未配置）: {e}")
        print("将使用 fallback 模式")

    # 2. 模拟视觉分析结果
    vision = VisionAnalysis(
        item_name="旧雨伞",
        visual_features=["黑色", "布面磨损", "木柄", "边缘有补丁"],
        personality_traits=["沉稳", "忠诚", "有点固执"],
        story_character_hint="像一个守护者",
    )

    # 3. 测试不同风格的检索
    for style in [StoryStyle.HEALING, StoryStyle.ADVENTURE, StoryStyle.DARK]:
        print(f"\n{'=' * 40}")
        print(f"风格: {style.value}")
        print(f"{'=' * 40}")

        try:
            templates = fable_rag.retrieve(
                vision=vision,
                style=style,
                top_k=3,
            )

            if templates:
                for i, t in enumerate(templates, 1):
                    print(f"\n  模板 {i}: {t['title']}")
                    print(f"    主题: {t['theme']}")
                    print(f"    冲突: {t['conflict_type']}")
                    print(f"    情绪: {t['emotion_arc']}")
                    print(f"    相似度: {t['distance']}")
            else:
                print("  ⚠️ 未检索到匹配模板")

        except Exception as e:
            print(f"  ⚠️ 检索失败: {e}")

    print("\n" + "=" * 60)
    print("RAG 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_rag()
