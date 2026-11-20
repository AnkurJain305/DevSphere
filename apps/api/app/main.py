from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_product_app() -> FastAPI:
    """Versioned product API. Its OpenAPI document does not include /health."""
    product = FastAPI(title="DevSphere API", version="0.1.0")
    product.include_router(v1_router)
    return product


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved.log_level)

    app = FastAPI(title="DevSphere", openapi_url=None, docs_url=None, redoc_url=None)
    app.mount("/api/v1", create_product_app())

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
