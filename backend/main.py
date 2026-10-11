"""FastAPI application entry point: wiring only, no business rules."""
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect

from backend.database import engine
from backend.routers import sessions
from backend.services.exceptions import (
    InvalidTransitionError,
    PersistenceError,
    SessionNotFoundError,
)

logger = logging.getLogger("deepwork")

CORS_ENV_VAR: str = "CORS_ALLOWED_ORIGINS"
DEFAULT_CORS_ORIGINS: str = (
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
)
REQUIRED_TABLES: frozenset[str] = frozenset({"sessions", "interruptions"})

DEV_SERVER_HOST: str = "127.0.0.1"
DEV_SERVER_PORT: int = 8000

API_DESCRIPTION: str = (
    "Schedule focused work sessions, pause/resume them with recorded interruptions, "
    "complete them, and review productivity history.\n\n"
    "**Lifecycle:** `scheduled -> active <-> paused`; terminal states are `completed`, "
    "`overdue`, `interrupted` and `abandoned`."
)


def _allowed_origins() -> list[str]:
    raw_value = os.getenv(CORS_ENV_VAR, DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Warn (do not crash) if migrations have not been applied."""
    missing = REQUIRED_TABLES - set(inspect(engine).get_table_names())
    if missing:
        logger.warning(
            "Database is missing tables %s. Run `alembic upgrade head` first.", sorted(missing)
        )
    yield


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": message})


async def handle_not_found(_request: Request, exc: SessionNotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc.message)


async def handle_invalid_transition(
    _request: Request, exc: InvalidTransitionError
) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc.message)


async def handle_persistence_error(_request: Request, exc: PersistenceError) -> JSONResponse:
    logger.error("Persistence error: %s", exc.message, exc_info=exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, exc.message)


async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error", exc_info=exc)
    return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error.")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Deep Work Session Tracker",
        version="1.0.0",
        description=API_DESCRIPTION,
        lifespan=lifespan,
        openapi_tags=[{"name": "sessions", "description": "Session lifecycle and history."}],
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    application.add_exception_handler(SessionNotFoundError, handle_not_found)  # type: ignore[arg-type]
    application.add_exception_handler(InvalidTransitionError, handle_invalid_transition)  # type: ignore[arg-type]
    application.add_exception_handler(PersistenceError, handle_persistence_error)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, handle_unexpected_error)
    application.include_router(sessions.router)
    return application


app: FastAPI = create_app()


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=DEV_SERVER_HOST, port=DEV_SERVER_PORT, reload=True)