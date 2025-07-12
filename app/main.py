import logging

from fastapi import FastAPI

from app.api.openai.endpoints import chat as openai_chat  # 导入新的 OpenAI 兼容路由
from app.api.v1beta.endpoints import gemini

# Removed: from app.core.logging import setup_logging
# setup_logging is now a no-op and handled at module level
# in app/core/logging.py

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    # Removed: setup_logging()
    # Logging is now configured at module level in app/core/logging.py
    logger.info("Starting Gemini Balance API application...")
    app = FastAPI(
        title="Gemini Balance API",
        description="A proxy service for Google Gemini API",
        version="1.0.0",
    )

    app.include_router(gemini.router, prefix="/v1beta", tags=["Gemini"])
    app.include_router(
        openai_chat.router, prefix="/v1", tags=["OpenAI"]
    )  # 注册 OpenAI 兼容路由

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
