"""Chat endpoint."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..security.rate_limit import rate_limiter
from ..services.orchestrator import orchestrator

router = APIRouter(prefix="/api/v1", tags=["chat"])


class HistoryItem(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=settings.max_user_message_chars)
    session_id: Optional[str] = None
    locale: str = "en"
    history: Optional[List[HistoryItem]] = None


class ChatResponse(BaseModel):
    message: str
    kind: str
    cards: list = []
    links: list = []
    suggestions: list = []
    search_url: str = ""
    advanced_search_url: str = ""
    facets: dict = {}
    session_id: str
    locale: str = "en"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request):
    ip = _client_ip(request)

    decision = rate_limiter.check(ip)
    if not decision.allowed:
        return JSONResponse(
            status_code=429,
            content={
                "message": "You are sending questions very quickly. Please wait a moment and try again.",
                "kind": "error",
                "retry_after": decision.retry_after_seconds,
                "session_id": payload.session_id or "",
                "locale": payload.locale,
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    history = [h.model_dump() for h in (payload.history or [])]

    turn = await orchestrator.handle(
        message=payload.message,
        session_id=payload.session_id,
        history=history,
        locale=payload.locale,
    )

    return ChatResponse(
        message=turn.message,
        kind=turn.kind,
        cards=turn.cards,
        links=turn.links,
        suggestions=turn.suggestions,
        search_url=turn.search_url,
        advanced_search_url=turn.advanced_search_url,
        facets=turn.facets,
        session_id=turn.session_id,
        locale=turn.locale,
    )
