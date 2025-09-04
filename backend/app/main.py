from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.management.endpoints.auth import router as auth_router
from backend.app.api.management.endpoints.auth_keys import router as auth_keys_router
from backend.app.api.management.endpoints.keys import router as keys_router
from backend.app.api.management.endpoints.logs import router as logs_router
from backend.app.api.management.endpoints.status import router as status_router
from backend.app.api.v1.endpoints.chat import router as openai_chat_router
from backend.app.api.v1beta.endpoints.gemini import router as gemini_router
from backend.app.core.config import settings
from backend.app.core.logging import app_logger as logger
from backend.app.core.logging import setup_app_logger, setup_transaction_logger
from backend.app.db.sqlite_migration_manager import MigrationManager
from backend.app.services import key_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DATABASE_TYPE == "sqlite":
        logger.info("Running SQLite database migrations...")
        migration_manager = MigrationManager(settings.SQLITE_DB)
        await migration_manager.run_migrations()
        logger.info("SQLite database migrations completed.")

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
    app.include_router(logs_router, prefix="/api", tags=["Logs"])
    app.include_router(keys_router, prefix="/api", tags=["Keys"])

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
