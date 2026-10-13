"""Chat orchestrator: guardrails → intent → (catalogue | FAQ | LLM) → output guard."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from ..config import settings
from ..security.guardrails import validate_output, validate_user_message
from .faq import faq_service
from .koha import koha_service
from .llm import LLMUnavailable, llm_service
from .query_parser import SearchIntent, _hindi_to_english, _is_hindi, parse_query

logger = logging.getLogger(__name__)


@dataclass
class ChatTurn:
    message: str
    cards: List[dict] = field(default_factory=list)
    links: List[dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    search_url: str = ""
    advanced_search_url: str = ""
    facets: dict = field(default_factory=dict)
    kind: str = "text"  # text | catalog | faq | error
    locale: str = "en"
    session_id: str = ""


DEFAULT_SUGGESTIONS = {
    "en": [
        "Find forensic DNA books",
        "Show books on cybercrime investigation",
        "Library timing & rules",
        "Renew my book",
        "How do I access ONOS off campus?",
        "Find theses on digital forensics",
    ],
    "hi": [
        "फोरेंसिक DNA पर पुस्तकें खोजें",
        "साइबर अपराध जांच की पुस्तकें",
        "पुस्तकालय समय और नियम",
        "मेरी पुस्तक नवीनीकृत करें",
        "ऑफ कैंपस पर ONOS कैसे उपयोग करें?",
        "डिजिटल फोरेंसिक्स पर शोध प्रबंध खोजें",
    ],
}


class ChatOrchestrator:
    async def handle(
        self,
        message: str,
        session_id: Optional[str] = None,
        history: Optional[List[dict]] = None,
        locale: str = "en",
    ) -> ChatTurn:
        session_id = session_id or uuid.uuid4().hex
        locale = locale if locale in settings.supported_locales else settings.default_locale
        turn = ChatTurn(message=message, locale=locale, session_id=session_id)

        # --- Inbound guardrails ---
        guard = validate_user_message(message)
        if not guard.ok:
            turn.message = self._fallback_for(guard.reason, locale)
            turn.kind = "error"
            turn.suggestions = self._suggestions(locale)
            return turn

        clean = guard.sanitized or message

        # --- Deterministic FAQ path (works with LLM down) ---
        # Hindi is routed through the translation table before FAQ matching
        # so the English keyword knowledge base still fires.
        faq_probe = _hindi_to_english(clean) if _is_hindi(clean) else clean
        faq = faq_service.match(faq_probe, locale=locale)
        if faq and not self._looks_like_catalog_request(faq_probe):
            turn.message = faq.answer
            turn.links = faq.links
            turn.kind = "faq"
            turn.suggestions = self._suggestions(locale)
            return turn

        # --- Catalogue search path ---
        intent = parse_query(clean)
        if intent.is_search:
            await self._run_catalog_search(turn, intent, clean, history, locale)
            return turn

        # --- Ambiguous: FAQ miss + no search intent → LLM or guided fallback ---
        await self._run_general(turn, clean, history, locale, faq_answer=faq.answer if faq else None)
        return turn

    # ------------------------------------------------------------------

    async def _run_catalog_search(
        self,
        turn: ChatTurn,
        intent: SearchIntent,
        clean: str,
        history: Optional[List[dict]],
        locale: str,
    ) -> None:
        # Optional LLM query rewrite (spelling / expansion) — non-blocking on failure
        query = intent.keywords or clean
        if llm_service.configured:
            rewritten = await llm_service.rewrite_query(clean)
            if rewritten and 3 <= len(rewritten) <= 120:
                # Re-parse the rewritten form; keep original structured fields.
                rewritten_intent = parse_query(rewritten)
                if rewritten_intent.keywords:
                    query = rewritten_intent.keywords
                    if not intent.author:
                        intent.author = rewritten_intent.author
                    if not intent.title:
                        intent.title = rewritten_intent.title

        idx, q = intent._primary_index_and_query()
        if not q:
            q = query or clean

        extra = {}
        if intent.author and idx != "au":
            extra["author"] = intent.author
        if intent.isbn and idx != "nb":
            extra["isbn"] = intent.isbn
        if intent.publisher and idx != "pn":
            extra["publisher"] = intent.publisher

        result = await koha_service.search(idx=idx, q=q, extra_params=extra or None)

        turn.search_url = result.search_url
        turn.advanced_search_url = result.advanced_search_url
        turn.facets = intent.describe()
        turn.cards = [r.to_dict() for r in result.records]
        turn.kind = "catalog"

        if result.records:
            # If LLM is up, let it write a short conversational summary;
            # otherwise a deterministic lead-in is still warm and useful.
            if llm_service.configured:
                context_lines = [
                    f"- {r.title} ({r.author or 'n/a'}, {r.year or 'n/a'}) "
                    f"[{r.availability}] {r.url}"
                    for r in result.records
                ]
                try:
                    summary = await llm_service.chat(
                        user_message=clean,
                        history=history,
                        context="Top catalogue matches:\n" + "\n".join(context_lines),
                    )
                    validated = validate_output(summary)
                    turn.message = validated.sanitized or self._lead_in(result.total, locale)
                except LLMUnavailable:
                    turn.message = self._lead_in(result.total, locale)
            else:
                turn.message = self._lead_in(result.total, locale)
        else:
            turn.message = faq_service.get_fallback("no_results", locale)
            turn.kind = "catalog"

        turn.suggestions = self._refine_suggestions(intent, locale)

    async def _run_general(
        self,
        turn: ChatTurn,
        clean: str,
        history: Optional[List[dict]],
        locale: str,
        faq_answer: Optional[str] = None,
    ) -> None:
        if faq_answer:
            turn.message = faq_answer
            turn.kind = "faq"
            turn.suggestions = self._suggestions(locale)
            return

        if llm_service.configured:
            try:
                answer = await llm_service.chat(clean, history=history)
                validated = validate_output(answer)
                turn.message = validated.sanitized or faq_service.get_fallback(
                    "llm_down", locale
                )
                turn.kind = "text"
                turn.suggestions = self._suggestions(locale)
                return
            except LLMUnavailable:
                pass

        turn.message = faq_service.get_fallback("llm_down", locale)
        turn.kind = "text"
        turn.links = [{"label": "Open KOHA search", "url": koha_service.build_advanced_search_url()}]
        turn.suggestions = self._suggestions(locale)

    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_catalog_request(text: str) -> bool:
        intent = parse_query(text)
        return bool(intent.is_search and intent.confidence >= 0.7)

    @staticmethod
    def _lead_in(total: int, locale: str) -> str:
        if locale == "hi":
            return f"मुझे कैटलॉग में {total} मिलान मिले। नीचे दिए गए रिकॉर्ड देखें, या अधिक विवरण के लिए KOHA लिंक खोलें।"
        if total == 1:
            return "I found a match in the catalogue. Here it is — open the KOHA record for full details and availability."
        return f"I found {total} matches in the catalogue. Open any KOHA record for full details, or refine with an author, year, or subject."

    @staticmethod
    def _fallback_for(reason: Optional[str], locale: str) -> str:
        mapping = {
            "injection_blocked": "injection_blocked",
            "rate_limited": "rate_limited",
            "message_too_long": "error",
            "empty_message": "error",
            "empty_after_sanitize": "error",
        }
        key = mapping.get(reason or "", "error")
        return faq_service.get_fallback(key, locale)

    @staticmethod
    def _suggestions(locale: str) -> List[str]:
        return DEFAULT_SUGGESTIONS.get(locale, DEFAULT_SUGGESTIONS["en"])

    @staticmethod
    def _refine_suggestions(intent: SearchIntent, locale: str) -> List[str]:
        if locale == "hi":
            base = [
                "नई खोज शुरू करें",
                "पुस्तकालय समय और नियम",
                "ONOS एक्सेस सहायता",
            ]
        else:
            base = [
                "Start a new search",
                "Library timing & rules",
                "ONOS access help",
            ]
        if intent.author:
            base.insert(0, f"More books by {intent.author}" if locale == "en" else f"{intent.author} की और पुस्तकें")
        if intent.year_after or intent.year_before:
            base.insert(0, "Widen the year range" if locale == "en" else "वर्ष सीमा बढ़ाएँ")
        return base[:4]


orchestrator = ChatOrchestrator()
