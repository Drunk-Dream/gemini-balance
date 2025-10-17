from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.api.endpoints.auth import router as auth_router
from backend.app.api.api.endpoints.auth_keys import router as auth_keys_router
from backend.app.api.api.endpoints.realtime_logs import router as realtime_logs_router
from backend.app.api.api.endpoints.request_keys import router as request_keys_router
from backend.app.api.api.endpoints.request_logs import router as request_logs_router
from backend.app.api.v1.endpoints.chat import router as openai_chat_router
from backend.app.api.v1beta.endpoints.gemini import router as gemini_router
from backend.app.core.concurrency import ConcurrencyManager
from backend.app.core.config import Settings, print_non_sensitive_settings
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import initialize_logging
from backend.app.db import get_migration_manager
from backend.app.services.request_key_manager.background_tasks import (
    BackgroundTaskManager,
)
from backend.app.services.request_service.gemini_request_service import (
    GeminiRequestService,
)
from backend.app.services.request_service.openai_request_service import (
    OpenAIRequestService,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings

    log_broadcaster = initialize_logging(settings)
    app.state.log_broadcaster = log_broadcaster

    logger.info("Starting Gemini Balance Application...")
    print_non_sensitive_settings(logger, settings)

    logger.info("Running database migrations...")
    migration_manager = get_migration_manager(settings)
    await migration_manager.run_migrations()
    logger.info("Database migrations completed.")

    logger.info("Initializing ConcurrencyManager...")
    concurrency_manager = ConcurrencyManager.get_instance(settings)
    app.state.concurrency_manager = concurrency_manager

    logger.info("Initializing BackgroundTaskManager...")
    background_task_manager = BackgroundTaskManager.get_instance(settings)
    app.state.background_task_manager = background_task_manager

    logger.info("Initializing KeyManager states...")
    await background_task_manager.initialize_key_states()

    logger.info("Starting background task for KeyManager...")
    await background_task_manager.start_background_task()

    logger.info("Initializing RequestService Client...")
    gemini_request_service = GeminiRequestService(settings=settings)
    app.state.gemini_request_service = gemini_request_service
    openai_request_service = OpenAIRequestService(settings=settings)
    app.state.openai_request_service = openai_request_service

    yield

    logger.info("Stopping background task for KeyManager...")
    await background_task_manager.stop_background_task()


def create_app() -> FastAPI:

    app = FastAPI(
        title="Gemini Balance API",
        description="A proxy service for Google Gemini API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(gemini_router, prefix="/v1beta", tags=["Gemini"])
    app.include_router(openai_chat_router, prefix="/v1", tags=["OpenAI"])
    app.include_router(auth_router, prefix="/api", tags=["Auth"])
    app.include_router(auth_keys_router, prefix="/api", tags=["Auth Keys"])
    app.include_router(realtime_logs_router, prefix="/api", tags=["Realtime Logs"])
    app.include_router(request_logs_router, prefix="/api", tags=["Request Logs"])
    app.include_router(request_keys_router, prefix="/api", tags=["Request Keys"])

    frontend_dir = Path("frontend/build")

    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        logger.info(f"Serving frontend from: {frontend_dir.absolute()}")
        app.mount(
            "/_app",
            StaticFiles(directory=frontend_dir / "_app"),
            name="static_assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            file_path = frontend_dir / full_path
            if file_path.is_file():
                return FileResponse(file_path)
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
