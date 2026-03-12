"""FableLens 后端入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="FableLens API",
        description="上传现实物品照片 → 自动生成寓言故事 + 连续绘本插图",
        version="0.1.0",
    )

    # CORS（允许前端跨域）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 路由
    app.include_router(router)

    # 静态文件（输出的图片）
    settings.ensure_dirs()
    app.mount("/outputs", StaticFiles(directory=str(settings.output_dir)), name="outputs")
    app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
