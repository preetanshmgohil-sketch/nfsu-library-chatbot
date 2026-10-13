"""FAQ intent matching against the local knowledge base (no LLM required)."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_KB_PATH = Path(__file__).resolve().parents[2] / "config" / "faq_knowledge.json"


@dataclass
class FaqMatch:
    intent_id: str
    answer: str
    links: List[Dict[str, str]] = field(default_factory=list)
    score: float = 0.0


class FaqService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._kb: dict = {}
        self.reload()

    def reload(self) -> None:
        with self._lock:
            with _KB_PATH.open("r", encoding="utf-8") as fh:
                self._kb = json.load(fh)

    @property
    def kb(self) -> dict:
        return self._kb

    def get_fallback(self, key: str, locale: str = "en") -> str:
        fb = self._kb.get("fallbacks", {})
        locale_block = fb.get(locale) or fb.get("en") or {}
        return locale_block.get(key, fb.get("en", {}).get(key, ""))

    def get_greeting(self, locale: str = "en") -> str:
        greetings = self._kb.get("greetings", {})
        options = greetings.get(locale) or greetings.get("en") or ["Hello!"]
        return options[0]

    def match(self, message: str, locale: str = "en") -> Optional[FaqMatch]:
        """Keyword-overlap scoring over FAQ intents. LLM-free path.

        Scoring: +1 per single-word keyword hit, +2 per multi-word phrase hit.
        Threshold 1.0 = at least one confident keyword signal.
        """
        if not message:
            return None

        text = message.lower()
        words = set(re.findall(r"[a-z0-9]+", text))

        best: Optional[FaqMatch] = None
        for intent in self._kb.get("intents", []):
            keywords = [k.lower() for k in intent.get("keywords", [])]
            score = 0.0
            for kw in keywords:
                if " " in kw:
                    if kw in text:
                        score += 2.0
                elif kw in words:
                    score += 1.0
                elif len(kw) >= 5 and any(w.startswith(kw) for w in words):
                    # light stemming: "borrowing" matches "borrow"
                    score += 1.0
            if score <= 0:
                continue
            match = FaqMatch(
                intent_id=intent["id"],
                answer=intent["answer"],
                links=intent.get("links", []),
                score=score,
            )
            if best is None or match.score > best.score:
                best = match

        if best and best.score >= 1.0:
            return best
        return None


faq_service = FaqService()
