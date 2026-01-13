from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.api.files_routes import router as files_router
from app.api.agents_routes import router as agents_router
from app.api.chats_routes import router as chats_router
from app.core.settings import settings


def create_app() -> FastAPI:
    application = FastAPI(
        title="AI Chatbot Backend",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger("app")

    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    # Ensure backend origin itself is allowed so Swagger "Try it out" works
    if "http://localhost:8000" not in allowed_origins:
        allowed_origins.append("http://localhost:8000")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=600,
    )

    # Prometheus metrics
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
    )

    @application.middleware("http")
    async def logging_and_metrics_middleware(request: Request, call_next: Callable):
        start_time = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        finally:
            duration = time.perf_counter() - start_time
            path = request.url.path
            method = request.method
            status = getattr(response, "status_code", 500)
            REQUEST_COUNT.labels(method=method, path=path, status=str(status)).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            logger.info(f"{method} {path} -> {status} in {duration:.3f}s")
        return response

    @application.get("/health")
    def health_check() -> dict:
        return {"status": "ok"}

    @application.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    application.include_router(files_router)
    application.include_router(agents_router)
    application.include_router(chats_router)
    return application


app = create_app()
