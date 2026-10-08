from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sourcepilot.api import router
from sourcepilot.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database schema changes are applied explicitly with Alembic, never at import time.
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SourcePilot API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "SourcePilot"}

    return app


app = create_app()

