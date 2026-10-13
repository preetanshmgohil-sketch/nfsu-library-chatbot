"""Input sanitization, prompt-injection guardrails, and output validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from ..config import settings

# ---------------------------------------------------------------------------
# Prompt-injection patterns
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: List[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+|any\s+|previous|prior|above|earlier|the\s+above)\s+"
        r"(instructions?|prompts?|rules?|messages?|context)",
        r"disregard\s+(all|any|previous|prior|your|the)\s+",
        r"forget\s+(all|any|previous|prior|your|everything)\s+",
        r"you\s+are\s+now\s+(a|an|the)\s+",
        r"act\s+as\s+(a|an|the)\s+",
        r"pretend\s+(to\s+be|you\s+are|you're)\s+",
        r"roleplay\s+as\s+",
        r"system\s*prompt",
        r"reveal\s+(your|the)\s+(system|hidden|initial)\s+",
        r"show\s+me\s+(your|the)\s+(system|hidden|admin|internal)\s+",
        r"admin\s+password",
        r"api\s*key",
        r"secret\s+key",
        r"jailbreak",
        r"DAN\s+mode",
        r"developer\s+mode",
        r"override\s+(your|the|all)\s+(rules?|instructions?|restrictions?)",
        r"repeat\s+(your|the)\s+(instructions?|prompt|rules?)\s+",
        r"\[INST\]|\[\/INST\]|<<SYS>>|<<\/SYS>>",
        r"<\|im_start\|>|<\|im_end\|>",
        r"ignore\s+instructions",
        r"do\s+anything\s+now",
        r"bypass\s+(your|the|all)\s+",
        r"unlock\s+(all|full)\s+access",
        r"print\s+(the\s+)?(contents?\s+of\s+)?(your|the)\s+config",
    ]
]

# ---------------------------------------------------------------------------
# PII patterns for output scanning
# ---------------------------------------------------------------------------

_PII_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "phone_in",
        re.compile(r"(?<!\d)(?:\+91[-\s]?)?[6-9]\d{9}(?!\d)"),
    ),
    (
        "aadhaar",
        re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),
    ),
    (
        "credit_card",
        re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)"),
    ),
]

_ALLOWED_URL_HOSTS = {
    "catalog.nfsu.ac.in",
    "nfsu.ac.in",
    "www.nfsu.ac.in",
    "onos.in",
    "www.onos.in",
    "koha-community.org",
    "en.wikipedia.org",
}

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass
class GuardrailResult:
    ok: bool
    reason: Optional[str] = None
    sanitized: Optional[str] = None
    flagged: List[str] = field(default_factory=list)


def sanitize_input(raw: str) -> str:
    """Strip control characters, collapse whitespace, trim."""
    text = _CONTROL_CHARS_RE.sub("", raw or "")
    text = text.replace("​", "").replace("﻿", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def check_injection(text: str) -> GuardrailResult:
    """Return failed result when prompt-injection heuristics match."""
    if not settings.block_prompt_injection:
        return GuardrailResult(ok=True, sanitized=text)
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(
                ok=False,
                reason="injection_blocked",
                sanitized=text,
            )
    return GuardrailResult(ok=True, sanitized=text)


def validate_user_message(raw: str) -> GuardrailResult:
    """Full inbound pipeline: length -> sanitize -> injection check."""
    if raw is None or not str(raw).strip():
        return GuardrailResult(ok=False, reason="empty_message")

    if len(raw) > settings.max_user_message_chars:
        return GuardrailResult(
            ok=False,
            reason="message_too_long",
            sanitized=raw[: settings.max_user_message_chars],
        )

    text = sanitize_input(raw)
    if not text:
        return GuardrailResult(ok=False, reason="empty_after_sanitize")

    return check_injection(text)


def _host_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in _ALLOWED_URL_HOSTS:
        return True
    # allow subdomains of nfsu.ac.in
    return host.endswith(".nfsu.ac.in")


def validate_output(text: str) -> GuardrailResult:
    """
    Scan model output for PII leaks and unauthorized URLs.
    URLs pointing outside the allowlist are stripped, not dropped wholesale.
    """
    if not text:
        return GuardrailResult(ok=True, sanitized="")

    flagged: List[str] = []

    # PII: if found, redact rather than refuse the whole answer.
    redacted = text
    for label, pattern in _PII_PATTERNS:
        matches = pattern.findall(redacted)
        if matches:
            flagged.append(label)
            redacted = pattern.sub(f"[{label.upper()} REDACTED]", redacted)

    # URLs: keep allowlisted, strip the rest.
    def _url_sub(match: re.Match[str]) -> str:
        url = match.group(0)
        if _host_allowed(url):
            return url
        flagged.append("unauthorized_url")
        return "[link removed]"

    redacted = _URL_RE.sub(_url_sub, redacted)

    return GuardrailResult(ok=True, sanitized=redacted, flagged=flagged)
