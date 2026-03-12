"""运行 FableLens 评测

用法:
  python run_eval.py              # 3 种风格各跑 1 次
  python run_eval.py --runs 2     # 3 种风格各跑 2 次
"""
import sys
import os

# 确保从 backend 目录运行
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.eval.evaluator import evaluator
from app.models.schemas import StoryStyle


def main():
    runs = 1
    if "--runs" in sys.argv:
        idx = sys.argv.index("--runs")
        if idx + 1 < len(sys.argv):
            runs = int(sys.argv[idx + 1])

    test_image = "C:/Users/monarch/fablelens/backend/uploads/test_book.jpg"

    print("=" * 70)
    print(f"FableLens 评测启动 - 每种风格 {runs} 次，共 {runs * 3} 次")
    print("=" * 70)

    results = evaluator.evaluate_batch(
        image_path=test_image,
        styles=[StoryStyle.HEALING, StoryStyle.ADVENTURE, StoryStyle.DARK],
        runs_per_style=runs,
    )

    evaluator.print_report(results)
    evaluator.save_report(results, "C:/Users/monarch/fablelens/backend/data/eval_results.json")


if __name__ == "__main__":
    main()
