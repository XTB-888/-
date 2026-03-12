"""FableLens 配置管理"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """应用配置，从 .env 文件加载"""

    # 阿里云百炼（通义千问）
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    vlm_model: str = "qwen-vl-max"
    text_model: str = "qwen-plus"

    # 硅基流动（图像生成）
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    image_model: str = "stabilityai/stable-diffusion-xl-base-1.0"

    # 服务配置
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"

    # 路径
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    def ensure_dirs(self):
        """确保必要目录存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
