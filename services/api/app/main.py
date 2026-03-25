from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
import uvicorn

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AfterHours API",
        version="0.1.0",
        summary="Route scoring, report validation, and journey orchestration.",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()


def serve() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        factory=False,
    )

if __name__ == "__main__":
    serve()