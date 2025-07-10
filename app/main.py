import logging

from fastapi import FastAPI

from app.api.v1.endpoints import gemini
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    setup_logging()
    logger.info("Starting Gemini Balance API application...")
    app = FastAPI(
        title="Gemini Balance API",
        description="A proxy service for Google Gemini API",
        version="1.0.0",
    )

    app.include_router(gemini.router, prefix="/v1", tags=["Gemini"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
