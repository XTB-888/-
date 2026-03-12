"""图像生成服务 - 使用硅基流动 FLUX API（含限流重试）"""
import time
import httpx
from pathlib import Path
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings


class RateLimitError(Exception):
    """API 限流异常"""
    pass


class ImageService:
    """图像生成服务"""

    # 请求间隔（秒），防止 429
    REQUEST_INTERVAL = 2.0

    def __init__(self):
        self.api_key = settings.siliconflow_api_key
        self.base_url = settings.siliconflow_base_url.rstrip("/")
        self.model = "black-forest-labs/FLUX.1-schnell"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._last_request_time = 0.0

    def _wait_rate_limit(self):
        """确保请求间隔"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=3, min=5, max=30),
        reraise=True,
    )
    def generate_image(
        self,
        prompt: str,
        image_size: str = "1024x1024",
        seed: Optional[int] = None,
    ) -> Optional[str]:
        """
        生成单张图片（含限流重试）

        Args:
            prompt: 英文描述
            image_size: 图片尺寸
            seed: 随机种子

        Returns:
            图片 URL 或 None
        """
        self._wait_rate_limit()

        url = f"{self.base_url}/images/generations"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": image_size,
            "batch_size": 1,
        }
        if seed is not None:
            payload["seed"] = seed

        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(url, json=payload, headers=self.headers)

                if resp.status_code == 429:
                    print(f"⚠️ 429 限流，等待重试...")
                    raise RateLimitError("Rate limited")

                resp.raise_for_status()
                data = resp.json()

            images = data.get("images", [])
            if images:
                return images[0].get("url", "")
            return None

        except RateLimitError:
            raise  # 让 tenacity 处理重试
        except Exception as e:
            print(f"⚠️ 图像生成失败: {e}")
            return None

    def download_image(self, image_url: str, save_dir: str, filename: str) -> Optional[str]:
        """下载图片到本地"""
        try:
            save_path = Path(save_dir) / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with httpx.Client(timeout=60) as client:
                resp = client.get(image_url)
                resp.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(resp.content)

            return str(save_path)

        except Exception as e:
            print(f"⚠️ 图片下载失败: {e}")
            return None

    def generate_storyboard(
        self,
        visual_prompts: list[str],
        task_id: str,
        base_seed: Optional[int] = None,
    ) -> tuple[list[str], dict]:
        """
        为 4 页绘本生成插图（含限流保护）

        Args:
            visual_prompts: 4 个英文 visual_prompt
            task_id: 任务 ID
            base_seed: 基础种子

        Returns:
            (image_urls, timings)
        """
        timings = {}
        image_urls = []

        if base_seed is None:
            base_seed = hash(task_id) % 2147483647

        for i, prompt in enumerate(visual_prompts):
            page_num = i + 1
            t0 = time.time()

            # 增强 prompt
            enhanced_prompt = prompt
            if "children book illustration" not in prompt.lower():
                enhanced_prompt += ", children book illustration, watercolor style"

            try:
                url = self.generate_image(
                    prompt=enhanced_prompt,
                    image_size="1024x1024",
                    seed=base_seed + i,
                )
            except RateLimitError:
                print(f"⚠️ 第{page_num}页插图限流重试耗尽，跳过")
                url = None

            if url:
                local_path = self.download_image(
                    image_url=url,
                    save_dir=str(settings.output_dir / task_id),
                    filename=f"page_{page_num}.png",
                )
                if local_path:
                    image_urls.append(f"/outputs/{task_id}/page_{page_num}.png")
                else:
                    image_urls.append(url)
            else:
                image_urls.append("")

            timings[f"image_page_{page_num}"] = round(time.time() - t0, 2)

        return image_urls, timings


# 单例
image_service = ImageService()
