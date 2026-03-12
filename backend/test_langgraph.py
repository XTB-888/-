"""测试 LangGraph 完整 pipeline"""
import time
import json
from app.chains.fablelens_graph import run_pipeline
from app.models.schemas import StoryStyle


def test_pipeline():
    print("=" * 60)
    print("测试 LangGraph Pipeline")
    print("=" * 60)

    test_image = "C:/Users/monarch/fablelens/backend/uploads/test_book.jpg"

    t0 = time.time()
    print("\n运行 pipeline（VLM → RAG → Outline → Narrative → Image → QC）...\n")

    final_state = run_pipeline(
        task_id="test_lg",
        image_path=test_image,
        style=StoryStyle.HEALING,
    )

    total = round(time.time() - t0, 2)

    print(f"\n{'=' * 60}")
    print(f"Pipeline 完成！总耗时: {total}s")
    print(f"状态: {final_state.get('status')}")
    print(f"质量检查: {'通过' if final_state.get('quality_passed') else '有问题'}")

    if final_state.get("error"):
        print(f"问题: {final_state['error']}")

    vision = final_state.get("vision")
    if vision:
        print(f"\n--- 视觉分析 ---")
        print(f"  物品: {vision.item_name}")
        print(f"  特征: {', '.join(vision.visual_features)}")
        print(f"  性格: {', '.join(vision.personality_traits)}")
        print(f"  角色: {vision.story_character_hint}")

    templates = final_state.get("templates", [])
    if templates:
        print(f"\n--- RAG 检索 ({len(templates)} 条) ---")
        for t in templates[:3]:
            print(f"  {t['title']} ({t['theme']})")

    outline = final_state.get("outline")
    if outline:
        print(f"\n--- 故事大纲: {outline.theme} ---")
        for p in outline.pages:
            print(f"  第{p.page}页: {p.scene} | {p.emotion}")

    story = final_state.get("story")
    if story:
        print(f"\n--- 故事: {story.title} ({len(story.full_text)}字) ---")
        print(story.full_text[:300] + "...")

    image_urls = final_state.get("image_urls", [])
    if image_urls:
        print(f"\n--- 插图 ({len(image_urls)} 张) ---")
        for i, url in enumerate(image_urls, 1):
            print(f"  第{i}页: {url[:60]}...")

    timings = final_state.get("step_timings", {})
    if timings:
        print(f"\n--- 各步骤耗时 ---")
        for k, v in sorted(timings.items()):
            print(f"  {k}: {v}s")

    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    test_pipeline()
