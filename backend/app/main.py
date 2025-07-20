import logging
from contextlib import asynccontextmanager

from app.services.key_manager import key_manager
from fastapi import FastAPI

from app.api.openai.endpoints import chat as openai_chat  # 导入新的 OpenAI 兼容路由
from app.api.v1beta.endpoints import status  # 导入 status 路由
from app.api.v1beta.endpoints import gemini
import os # 导入 os 模块
from pathlib import Path # 导入 Path 模块
from fastapi.staticfiles import StaticFiles # 导入 StaticFiles

# Removed: from app.core.logging import setup_logging
# setup_logging is now a no-op and handled at module level
# in app/core/logging.py

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting background task for KeyManager...")
    key_manager.start_background_task()
    yield
    # Shutdown
    logger.info("Stopping background task for KeyManager...")
    key_manager.stop_background_task()


def create_app() -> FastAPI:
    # Removed: setup_logging()
    # Logging is now configured at module level in app/core/logging.py
    logger.info("Starting Gemini Balance API application...")
    app = FastAPI(
        title="Gemini Balance API",
        description="A proxy service for Google Gemini API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(gemini.router, prefix="/v1beta", tags=["Gemini"])
    app.include_router(
        openai_chat.router, prefix="/v1", tags=["OpenAI"]
    )  # 注册 OpenAI 兼容路由
    app.include_router(
        status.router, prefix="/api", tags=["Status"]
    )  # 注册 status 路由

    # 仅在生产环境且前端文件存在时挂载
    if os.getenv("APP_ENV") == "production":
        frontend_dist = Path("frontend/dist")
        if frontend_dist.exists():
            logger.info(f"Mounting static files from {frontend_dist.absolute()}")
            app.mount(
                "/", StaticFiles(directory=frontend_dist, html=True), name="frontend"
            )
        else:
            logger.warning("Frontend build directory not found, skipping static file mount.")
    else:
        logger.info("Running in development mode, skipping static file mount.")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
