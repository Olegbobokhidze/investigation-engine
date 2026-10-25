"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import health
from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.env == "prod")

    app = FastAPI(title="Investigation Engine", version="0.1.0")
    app.include_router(health.router)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    return app


app = create_app()
