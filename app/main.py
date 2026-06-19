import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.v1.router import api_router
from app.core.config import _get_settings_cached, get_settings
from app.core.redis import close_redis, get_redis
from app.db.session import async_session_factory
from app.services.websocket import start_websocket_stack, stop_websocket_stack
from app.middleware.security import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _get_settings_cached.cache_clear()
    try:
        await start_websocket_stack()
    except (RedisError, OSError, ConnectionError) as exc:
        if get_settings().app_env == "development":
            logger.warning("WebSocket/Redis stack not started: %s", exc)
        else:
            raise
    yield
    await stop_websocket_stack()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Tick Talk API",
        version="1.0.0",
        docs_url="/api/v1/docs" if settings.app_debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.app_env == "development":
        # LAN devices join via http://<ip>:5173 → API on :8000
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"https?://[\w.\-]+(:\d+)?",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def health_ready():
        """Reports whether MySQL and Redis are reachable (login needs both)."""
        checks: dict[str, str] = {}
        try:
            async with async_session_factory() as db:
                await db.execute(text("SELECT 1"))
            checks["mysql"] = "ok"
        except Exception as exc:
            checks["mysql"] = f"error: {exc}"

        try:
            redis = await get_redis()
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"

        ready = all(v == "ok" for v in checks.values())
        return {
            "ready": ready,
            "checks": checks,
            "hint": None
            if ready
            else "Start Docker Desktop, then run: cd \"Tick Talk\" && docker compose up -d",
        }

    @app.exception_handler(OperationalError)
    async def database_unavailable(_request: Request, exc: OperationalError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Database is not running. Open Docker Desktop, then run "
                    "docker compose up -d from the Tick Talk project folder."
                ),
                "error": str(exc.orig) if exc.orig else str(exc),
            },
        )

    @app.exception_handler(RedisError)
    async def redis_unavailable(_request: Request, exc: RedisError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Redis is not running. Open Docker Desktop, then run "
                    "docker compose up -d from the Tick Talk project folder."
                ),
                "error": str(exc),
            },
        )

    @app.get("/")
    async def root():
        return {
            "name": "Tick Talk API",
            "health": "/health",
            "api": "/api/v1",
            "docs": "/api/v1/docs" if settings.app_debug else None,
            "frontend": settings.app_public_url,
            "hint": "Open the Vue app (e.g. http://localhost:5173), not this port, for the UI.",
        }

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
