import logging
from contextlib import asynccontextmanager
from pathlib import Path

from app.api.openai.endpoints.chat import router as openai_chat_router
from app.api.v1beta.endpoints.auth import router as auth_router
from app.api.v1beta.endpoints.auth_keys import router as auth_keys_router
from app.api.v1beta.endpoints.gemini import router as gemini_router
from app.api.v1beta.endpoints.keys import router as keys_router  # 新增导入
from app.api.v1beta.endpoints.status import router as status_router
from app.core.logging import setup_app_logger, setup_transaction_logger
from app.services import key_manager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing KeyManager...")
    await key_manager.initialize()
    logger.info("Starting background task for KeyManager...")
    await key_manager.start_background_task()
    yield
    logger.info("Stopping background task for KeyManager...")
    key_manager.stop_background_task()


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
    app.include_router(auth_router, prefix="/api", tags=["Auth"])
    app.include_router(status_router, prefix="/api", tags=["Status"])
    app.include_router(auth_keys_router, prefix="/api", tags=["Auth Keys"])
    app.include_router(keys_router, prefix="/api", tags=["Keys"])  # 新增路由

    frontend_dir = Path("frontend/build")

    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        logger.info(f"Serving frontend from: {frontend_dir.absolute()}")
        app.mount(
            "/_app",
            StaticFiles(directory=frontend_dir / "_app"),
            name="static_assets",
        )

        @app.get("/favicon.svg", include_in_schema=False)
        async def favicon():
            return FileResponse(frontend_dir / "favicon.svg")

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
