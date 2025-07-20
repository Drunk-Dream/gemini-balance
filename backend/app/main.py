import logging
from contextlib import asynccontextmanager
from pathlib import Path

import redis.asyncio as redis
from app.api.openai.endpoints.chat import router as openai_chat_router
from app.api.v1beta.endpoints.gemini import router as gemini_router
from app.api.v1beta.endpoints.status import router as status_router
from app.core.config import settings
from app.core.logging import setup_app_logger, setup_transaction_logger
from app.services.key_manager import KeyManager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis client
    app.state.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    await app.state.redis_client.ping()  # Test connection
    logger.info("Redis client initialized.")

    # Initialize KeyManager
    app.state.key_manager = KeyManager(
        settings.GOOGLE_API_KEYS if settings.GOOGLE_API_KEYS is not None else [],
        settings.API_KEY_COOL_DOWN_SECONDS,
        settings.API_KEY_FAILURE_THRESHOLD,
        settings.MAX_COOL_DOWN_SECONDS,
        app.state.redis_client,
    )
    logger.info("KeyManager initialized.")

    logger.info("Starting background task for KeyManager...")
    app.state.key_manager.start_background_task()
    yield
    logger.info("Stopping background task for KeyManager...")
    app.state.key_manager.stop_background_task()
    await app.state.redis_client.close()
    logger.info("Redis client closed.")


def create_app() -> FastAPI:
    # Setup loggers first
    setup_app_logger()
    setup_transaction_logger()

    logger.info("Starting Gemini Balance API application...")
    app = FastAPI(
        title="Gemini Balance API",
        description="A proxy service for Google Gemini API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(gemini_router, prefix="/v1beta", tags=["Gemini"])
    app.include_router(openai_chat_router, prefix="/v1", tags=["OpenAI"])
    app.include_router(status_router, prefix="/api", tags=["Status"])

    frontend_dir = Path("frontend/build")

    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        logger.info(f"Serving frontend from: {frontend_dir.absolute()}")
        app.mount(
            "/_app",
            StaticFiles(directory=frontend_dir / "_app"),
            name="static_assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(request: Request):
            return FileResponse(frontend_dir / "index.html")

    else:
        logger.warning(
            "Frontend build directory or index.html not found in "
            f"{frontend_dir.absolute()}. Skipping frontend serving."
        )

        @app.get("/", include_in_schema=False)
        def root():
            return {"message": "Backend is running, but frontend is not available."}

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
