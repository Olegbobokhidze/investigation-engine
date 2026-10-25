"""FastAPI application factory.

Run with `uvicorn --factory investigation_engine.main:create_app`, so settings are read
when the server starts rather than as a side effect of importing this module.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from investigation_engine.api.routes import health
from investigation_engine.core.config import Settings, get_settings
from investigation_engine.core.errors import AppError
from investigation_engine.core.logging import configure_logging


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
