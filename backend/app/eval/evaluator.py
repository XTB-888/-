"""FableLens 自动化评测体系

评测维度：
1. 视觉分析质量 - VLM 输出结构完整性
2. 故事文学质量 - 长度/结构/拟人化/寓意
3. 插图质量 - 生成成功率/风格一致性
4. 端到端性能 - 各步骤耗时
5. Pipeline 稳定性 - 重试/fallback 触发率
"""
import json
import time
import statistics
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from app.chains.fablelens_graph import run_pipeline
from app.models.schemas import StoryStyle, VisionAnalysis, StoryOutline, GeneratedStory


# ============================================================
# 评测指标
# ============================================================

@dataclass
class VisionScore:
    """视觉分析评分"""
    has_item_name: bool = False
    feature_count: int = 0          # 期望 3-5
    trait_count: int = 0            # 期望 3-4
    has_character_hint: bool = False
    score: float = 0.0              # 0-100

    def compute(self):
        s = 0.0
        if self.has_item_name:
            s += 25
        s += min(25, self.feature_count * 6.25)   # 4 个满分
        s += min(25, self.trait_count * 8.33)      # 3 个满分
        if self.has_character_hint:
            s += 25
        self.score = round(s, 1)


@dataclass
class StoryScore:
    """故事质量评分"""
    title_length: int = 0           # 期望 3-10 字
    full_text_length: int = 0       # 期望 400-800 字
    page_count: int = 0             # 期望 4
    has_personification: bool = False  # 是否拟人化
    has_moral: bool = False         # 是否有寓意
    emotion_arc_clear: bool = False # 情绪弧线是否清晰
    score: float = 0.0              # 0-100

    def compute(self, vision_name: str = "", full_text: str = ""):
        s = 0.0

        # 标题（15分）
        if 2 <= self.title_length <= 15:
            s += 15
        elif self.title_length > 0:
            s += 8

        # 长度（25分）
        if 400 <= self.full_text_length <= 900:
            s += 25
        elif 200 <= self.full_text_length < 400:
            s += 15
        elif self.full_text_length >= 100:
            s += 8

        # 分页（15分）
        if self.page_count == 4:
            s += 15
        elif self.page_count >= 3:
            s += 10

        # 拟人化（20分）- 检查物品名称是否在故事中作为角色出现
        if vision_name and full_text:
            # 检查是否有拟人化表达
            personification_markers = ["它", "他", "她", "自己", "心", "想", "说", "感到", "觉得", "记得"]
            marker_count = sum(1 for m in personification_markers if m in full_text)
            if marker_count >= 3:
                s += 20
                self.has_personification = True
            elif marker_count >= 1:
                s += 10
                self.has_personification = True

        # 寓意（15分）- 检查结尾是否有点睛之笔
        if full_text:
            last_paragraph = full_text[-200:] if len(full_text) > 200 else full_text
            moral_markers = ["原来", "才明白", "懂得", "真正的", "从此", "终于", "其实", "不是", "而是"]
            if any(m in last_paragraph for m in moral_markers):
                s += 15
                self.has_moral = True

        # 情绪弧线（10分）
        if self.emotion_arc_clear:
            s += 10

        self.score = round(s, 1)


@dataclass
class ImageScore:
    """插图质量评分"""
    total_pages: int = 4
    generated_count: int = 0        # 成功生成数
    score: float = 0.0              # 0-100

    def compute(self):
        if self.total_pages > 0:
            self.score = round((self.generated_count / self.total_pages) * 100, 1)


@dataclass
class PerformanceScore:
    """性能评分"""
    vision_time: float = 0.0
    rag_time: float = 0.0
    outline_time: float = 0.0
    narrative_time: float = 0.0
    image_time: float = 0.0
    total_time: float = 0.0
    score: float = 0.0              # 0-100

    def compute(self):
        # 总时间评分：<45s=100, 45-60s=80, 60-90s=60, 90-120s=40, >120s=20
        if self.total_time <= 45:
            self.score = 100
        elif self.total_time <= 60:
            self.score = 80
        elif self.total_time <= 90:
            self.score = 60
        elif self.total_time <= 120:
            self.score = 40
        else:
            self.score = 20


@dataclass
class EvalResult:
    """单次评测结果"""
    test_id: str = ""
    style: str = ""
    image_path: str = ""

    vision_score: VisionScore = field(default_factory=VisionScore)
    story_score: StoryScore = field(default_factory=StoryScore)
    image_score: ImageScore = field(default_factory=ImageScore)
    performance_score: PerformanceScore = field(default_factory=PerformanceScore)

    overall_score: float = 0.0      # 加权总分
    pipeline_status: str = ""
    error: str = ""

    # 权重
    WEIGHTS = {"vision": 0.15, "story": 0.40, "image": 0.20, "performance": 0.25}

    def compute_overall(self):
        self.overall_score = round(
            self.vision_score.score * self.WEIGHTS["vision"]
            + self.story_score.score * self.WEIGHTS["story"]
            + self.image_score.score * self.WEIGHTS["image"]
            + self.performance_score.score * self.WEIGHTS["performance"],
            1,
        )


# ============================================================
# 评测引擎
# ============================================================

class Evaluator:
    """FableLens 评测引擎"""

    def evaluate_single(
        self,
        image_path: str,
        style: StoryStyle,
        test_id: str = "eval",
    ) -> EvalResult:
        """执行单次评测"""
        result = EvalResult(test_id=test_id, style=style.value, image_path=image_path)

        # 运行 pipeline
        t0 = time.time()
        try:
            state = run_pipeline(
                task_id=f"eval_{test_id}",
                image_path=image_path,
                style=style,
            )
            result.pipeline_status = state.get("status", "unknown")
        except Exception as e:
            result.pipeline_status = "crashed"
            result.error = str(e)
            return result

        total_time = time.time() - t0
        timings = state.get("step_timings", {})

        # 1. 视觉分析评分
        vision = state.get("vision")
        if vision:
            result.vision_score.has_item_name = bool(vision.item_name and len(vision.item_name) > 0)
            result.vision_score.feature_count = len(vision.visual_features)
            result.vision_score.trait_count = len(vision.personality_traits)
            result.vision_score.has_character_hint = bool(vision.story_character_hint and len(vision.story_character_hint) > 2)
        result.vision_score.compute()

        # 2. 故事质量评分
        story = state.get("story")
        outline = state.get("outline")
        if story:
            result.story_score.title_length = len(story.title)
            result.story_score.full_text_length = len(story.full_text)
            result.story_score.page_count = len(story.page_texts)

            # 检查情绪弧线
            if outline and len(outline.pages) >= 4:
                emotions = [p.emotion for p in outline.pages]
                if len(set(emotions)) >= 3:  # 至少 3 种不同情绪
                    result.story_score.emotion_arc_clear = True

            result.story_score.compute(
                vision_name=vision.item_name if vision else "",
                full_text=story.full_text,
            )

        # 3. 插图评分
        image_urls = state.get("image_urls", [])
        result.image_score.generated_count = len([u for u in image_urls if u])
        result.image_score.compute()

        # 4. 性能评分
        result.performance_score.vision_time = timings.get("vision_analyze", 0)
        result.performance_score.rag_time = timings.get("rag_retrieve", 0)
        result.performance_score.outline_time = timings.get("outline_generate", 0)
        result.performance_score.narrative_time = timings.get("narrative_generate", 0)
        result.performance_score.image_time = timings.get("image_generate_total", 0)
        result.performance_score.total_time = round(total_time, 2)
        result.performance_score.compute()

        # 总分
        result.compute_overall()

        return result

    def evaluate_batch(
        self,
        image_path: str,
        styles: list[StoryStyle] = None,
        runs_per_style: int = 1,
    ) -> list[EvalResult]:
        """批量评测"""
        if styles is None:
            styles = [StoryStyle.HEALING, StoryStyle.ADVENTURE, StoryStyle.DARK]

        results = []
        total = len(styles) * runs_per_style
        idx = 0

        for style in styles:
            for run in range(runs_per_style):
                idx += 1
                test_id = f"{style.value}_{run + 1}"
                print(f"\n[{idx}/{total}] 评测: {test_id}")

                result = self.evaluate_single(image_path, style, test_id)
                results.append(result)

                print(f"  视觉: {result.vision_score.score} | "
                      f"故事: {result.story_score.score} | "
                      f"插图: {result.image_score.score} | "
                      f"性能: {result.performance_score.score} | "
                      f"总分: {result.overall_score}")

        return results

    @staticmethod
    def print_report(results: list[EvalResult]):
        """打印评测报告"""
        print("\n" + "=" * 70)
        print("FableLens 评测报告")
        print("=" * 70)

        if not results:
            print("无评测结果")
            return

        # 汇总
        overall_scores = [r.overall_score for r in results]
        vision_scores = [r.vision_score.score for r in results]
        story_scores = [r.story_score.score for r in results]
        image_scores = [r.image_score.score for r in results]
        perf_scores = [r.performance_score.score for r in results]
        total_times = [r.performance_score.total_time for r in results]

        print(f"\n评测次数: {len(results)}")
        print(f"\n{'维度':<12} {'平均分':<10} {'最低':<10} {'最高':<10} {'标准差':<10}")
        print("-" * 52)

        for name, scores in [
            ("总分", overall_scores),
            ("视觉分析", vision_scores),
            ("故事质量", story_scores),
            ("插图生成", image_scores),
            ("性能", perf_scores),
        ]:
            avg = round(statistics.mean(scores), 1)
            lo = round(min(scores), 1)
            hi = round(max(scores), 1)
            std = round(statistics.stdev(scores), 1) if len(scores) > 1 else 0
            print(f"{name:<12} {avg:<10} {lo:<10} {hi:<10} {std:<10}")

        print(f"\n平均耗时: {round(statistics.mean(total_times), 1)}s")
        print(f"最快: {round(min(total_times), 1)}s | 最慢: {round(max(total_times), 1)}s")

        # 按风格分组
        style_groups: dict[str, list[EvalResult]] = {}
        for r in results:
            style_groups.setdefault(r.style, []).append(r)

        if len(style_groups) > 1:
            print(f"\n{'风格':<8} {'平均总分':<10} {'平均耗时':<10} {'故事均分':<10}")
            print("-" * 38)
            for style, group in style_groups.items():
                avg_overall = round(statistics.mean([r.overall_score for r in group]), 1)
                avg_time = round(statistics.mean([r.performance_score.total_time for r in group]), 1)
                avg_story = round(statistics.mean([r.story_score.score for r in group]), 1)
                print(f"{style:<8} {avg_overall:<10} {avg_time:<10}s {avg_story:<10}")

        # 失败统计
        failures = [r for r in results if "failed" in r.pipeline_status or r.pipeline_status == "crashed"]
        if failures:
            print(f"\n⚠️ 失败次数: {len(failures)}/{len(results)}")
            for f in failures:
                print(f"  {f.test_id}: {f.error[:80]}")

        # 评级
        avg_overall = statistics.mean(overall_scores)
        if avg_overall >= 85:
            grade = "A (优秀)"
        elif avg_overall >= 70:
            grade = "B (良好)"
        elif avg_overall >= 55:
            grade = "C (合格)"
        else:
            grade = "D (需改进)"

        print(f"\n综合评级: {grade} ({round(avg_overall, 1)}分)")
        print("=" * 70)

    @staticmethod
    def save_report(results: list[EvalResult], output_path: str):
        """保存评测结果到 JSON"""
        data = []
        for r in results:
            data.append({
                "test_id": r.test_id,
                "style": r.style,
                "overall_score": r.overall_score,
                "vision_score": r.vision_score.score,
                "story_score": r.story_score.score,
                "image_score": r.image_score.score,
                "performance_score": r.performance_score.score,
                "total_time": r.performance_score.total_time,
                "story_length": r.story_score.full_text_length,
                "image_count": r.image_score.generated_count,
                "pipeline_status": r.pipeline_status,
                "has_personification": r.story_score.has_personification,
                "has_moral": r.story_score.has_moral,
                "emotion_arc_clear": r.story_score.emotion_arc_clear,
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n评测结果已保存到: {output_path}")


# 单例
evaluator = Evaluator()
