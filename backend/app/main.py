"""NFSU Library Chatbot — FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import chat, ops
from .services.faq import faq_service

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

# Project root = backend/..
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WIDGET_DIST = _PROJECT_ROOT / "widget" / "dist"
_DEMO_HTML = _PROJECT_ROOT / "integration" / "demo-opac.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    faq_service.reload()
    logger.info(
        "NFSU Library Chatbot up — env=%s llm=%s koha=%s",
        settings.environment,
        "on" if settings.llm_enabled else "off",
        settings.koha_opac_base_url,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origins_regex or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=600,
)

app.include_router(chat.router)
app.include_router(ops.router)

if _WIDGET_DIST.is_dir():
    app.mount("/static", StaticFiles(directory=str(_WIDGET_DIST)), name="static")


def _demo_page_html() -> str:
    """Serve the OPAC demo shell rewritten for same-origin hosting."""
    if not _DEMO_HTML.is_file():
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>Demo unavailable</title></head><body>"
            "<p style='font-family:system-ui;padding:2rem'>Demo page not found. "
            "The backend API is still running at this origin.</p></body></html>"
        )
    html = _DEMO_HTML.read_text(encoding="utf-8")
    html = html.replace(
        'src="../widget/dist/nfsu-chatbot.js"',
        'src="/static/nfsu-chatbot.js"',
    ).replace(
        'data-api-base="http://127.0.0.1:8000"',
        'data-api-base=""',
    )
    return html


@app.get("/demo", include_in_schema=False)
async def demo_page() -> Response:
    return Response(content=_demo_page_html(), media_type="text/html; charset=utf-8")


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.app_name,
        "status": "ok",
        "demo": "/demo",
        "health": "/api/v1/health",
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Something went wrong while processing that. Please try again.",
            "kind": "error",
        },
    )
