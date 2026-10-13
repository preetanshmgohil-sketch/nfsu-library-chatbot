"""Widget configuration, health, and control endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import settings
from ..services.faq import faq_service
from ..services.llm import llm_service

router = APIRouter(prefix="/api/v1", tags=["ops"])

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "widget_config.json"


def _load_widget_config() -> dict:
    try:
        import json

        with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


@router.get("/health")
async def health():
    return {
        "status": "ok" if settings.widget_enabled else "disabled",
        "suspended": settings.widget_suspended,
        "llm_configured": llm_service.configured,
        "koha_mode": (
            "rest"
            if (settings.koha_rest_base_url and settings.koha_rest_token)
            else ("opac_scrape" if settings.koha_scrape_enabled else "opac_deep_link")
        ),
    }


@router.get("/config")
async def widget_config(locale: str = "en"):
    """
    Runtime widget configuration.

    `enabled` lets the embedding page hide the trigger without touching KOHA.
    `suspended` is an operator kill-switch served by the backend.
    """
    if settings.widget_suspended or not settings.widget_enabled:
        return JSONResponse(
            status_code=200,
            content={
                "enabled": False,
                "suspended": settings.widget_suspended,
                "message": "The library assistant is temporarily unavailable.",
            },
        )

    cfg = _load_widget_config()
    loc = locale if locale in settings.supported_locales else settings.default_locale

    suggestions = (
        cfg.get("suggestions", {}).get(loc)
        or cfg.get("suggestions", {}).get(settings.default_locale)
        or []
    )
    welcome = (
        cfg.get("welcome", {}).get(loc)
        or cfg.get("welcome", {}).get(settings.default_locale)
        or faq_service.get_greeting(loc)
    )

    return {
        "enabled": True,
        "suspended": False,
        "version": cfg.get("version", "1.0.0"),
        "welcome": welcome,
        "suggestions": suggestions,
        "default_locale": settings.default_locale,
        "supported_locales": settings.supported_locales,
        "theme": cfg.get("theme", {"default": "system"}),
        "opac_base_url": settings.koha_opac_base_url,
        "advanced_search_url": f"{settings.koha_opac_base_url}/opac-search.pl",
    }
