"""Deterministic natural-language → structured catalog-search intent parser.

Covers the full capability matrix from the requirements:
title, author, ISBN, subject/keyword, publisher, publication-year,
combined queries, and follow-up refinement filters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchIntent:
    """Structured representation of a catalogue search request."""

    keywords: str = ""
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    subject: Optional[str] = None
    publisher: Optional[str] = None
    year_after: Optional[int] = None
    year_before: Optional[int] = None
    resource_type: Optional[str] = None  # book | journal | thesis | dissertation
    raw_query: str = ""
    is_search: bool = False
    confidence: float = 0.0
    facets: dict = field(default_factory=dict)

    def to_koha_params(self) -> dict:
        """Map intent to KOHA opac-search.pl query params (live NFSU indexes)."""
        idx, q = self._primary_index_and_query()
        params: dict = {"q": q, "weight_search": "1"}
        if idx:
            params["idx"] = idx
        if self.author and idx != "au":
            params.setdefault("author", self.author)
        if self.isbn and idx != "nb":
            params.setdefault("isbn", self.isbn)
        if self.year_after or self.year_before:
            if self.year_after and self.year_before:
                params["publicationyear"] = f"{self.year_after}-{self.year_before}"
            elif self.year_after:
                params["publicationyear"] = f"{self.year_after}-"
            elif self.year_before:
                params["publicationyear"] = f"-{self.year_before}"
        return params

    def _primary_index_and_query(self) -> tuple[str, str]:
        # Indexes verified on catalog.nfsu.ac.in: '' | ti | au | su | nb | ns | se | callnum
        if self.isbn:
            return "nb", self.isbn
        if self.title and self.keywords and self.title == self.keywords:
            return "ti", self.title
        if self.title:
            return "ti", self.title
        if self.author:
            return "au", self.author
        if self.subject:
            return "su", self.subject
        if self.publisher:
            # KOHA has no dedicated publisher index on this OPAC — keyword search
            # still matches publisher strings inside records.
            return "", self.keywords or self.raw_query
        return "", self.keywords or self.raw_query

    def describe(self) -> dict:
        """Facet summary for the UI filter bar."""
        out = {}
        if self.title:
            out["title"] = self.title
        if self.author:
            out["author"] = self.author
        if self.isbn:
            out["isbn"] = self.isbn
        if self.subject:
            out["subject"] = self.subject
        if self.publisher:
            out["publisher"] = self.publisher
        if self.year_after or self.year_before:
            lo = self.year_after or "…"
            hi = self.year_before or "…"
            out["year"] = f"{lo}–{hi}"
        if self.resource_type:
            out["type"] = self.resource_type
        return out


# ---------------------------------------------------------------------------
# Pattern library
# ---------------------------------------------------------------------------

_SEARCH_VERBS = re.compile(
    r"\b("
    r"find|search|show|list|look\s+for|get|fetch|give|recommend|suggest|"
    r"do\s+we\s+have|are\s+there|any\s+books?|any\s+resources?|"
    r"search\s+for|books?\s+on|books?\s+about|books?\s+by|"
    r"resources?\s+on|publications?\s+about|materials?\s+on"
    r")\b",
    re.IGNORECASE,
)

_AUTHOR_PATTERNS = [
    re.compile(
        r"\b(?:books?|publications?|works?|titles?)\s+(?:by|written\s+by|authored\s+by)\s+"
        r"(?P<author>[A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+){0,3})",
    ),
    re.compile(
        r"\b(?:by|written\s+by|authored\s+by)\s+"
        r"(?P<author>[A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+){0,3})(?:'s)?\b",
    ),
    re.compile(
        r"\bauthor\s*[:\-]?\s+"
        r"(?P<author>[A-Z][\w.'\-]+(?:\s+[A-Z][\w.'\-]+){0,3})",
        re.IGNORECASE,
    ),
]

_ISBN_RE = re.compile(r"\b(?:ISBN(?:-1[03])?[:\s]*)?(\d{9}[\dXx]|\d{13})\b")

_YEAR_RANGE_RE = re.compile(
    r"\b(?:published\s+)?(?:between|from)\s+(19|20)\d{2}\s+(?:to|and|–|-)\s+(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
_YEAR_AFTER_RE = re.compile(
    r"\b(?:published\s+)?(?:after|since|from|in)\s+((?:19|20)\d{2})\s*(?:onwards?|later|and\s+up)?\b",
    re.IGNORECASE,
)
_YEAR_BEFORE_RE = re.compile(
    r"\b(?:before|until|upto|up\s+to)\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_YEAR_PUBLISHED_RE = re.compile(
    r"\b(?:published\s+in|year\s*[:\-]?)\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)

_TYPE_MAP = [
    (re.compile(r"\btheses\b|\bthesis\b|\bdissertations?\b|\bphd\b", re.IGNORECASE), "thesis"),
    (re.compile(r"\bjournals?\b|\bperiodicals?\b|\bmagazines?\b", re.IGNORECASE), "journal"),
    (re.compile(r"\be-?books?\b|\bdigital\s+books?\b", re.IGNORECASE), "ebook"),
    (re.compile(r"\bstandards?\b|\biso\b|\bis\s*codes?\b", re.IGNORECASE), "standard"),
]

# Explicit title markers only — bare "books on X" must NOT be read as a title.
# "title" requires an explicit separator; named/called/titled allow optional separator.
_TITLE_RE = re.compile(
    r"\btitle(?:\s+search)?\s*[:\-]\s*[\"'“]?([^\"'”.,;!?]{3,80})[\"'”]?"
    r"|\b(?:titled|named|called)\s*[:\-]?\s*[\"'“]?([^\"'”.,;!?]{3,80})[\"'”]?",
    re.IGNORECASE,
)
_TITLE_QUOTED_RE = re.compile(
    r"[\"'“]([^\"'”]{3,80})[\"'”]"
)
# Leading publisher token: "Springer books on X", "Elsevier journals about Y"
_LEAD_PUB_RE = re.compile(
    r"^\s*([A-Z][A-Za-z&.\-]{2,20})\s+(?:books?|journals?|publications?|press)\b"
)

_PUBLISHER_RE = re.compile(
    r"\b(?:published\s+by|publisher\s*[:\-]?|from)\s+"
    r"([A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,3})",
)

_STOPWORDS = {
    "a", "an", "the", "on", "in", "of", "for", "to", "and", "or", "with",
    "about", "please", "me", "my", "i", "we", "our", "can", "could", "you",
    "do", "does", "did", "is", "are", "was", "were", "have", "has", "had",
    "show", "find", "search", "list", "get", "give", "look", "books", "book",
    "resources", "resource", "materials", "material", "publications",
    "publication", "any", "some", "what", "which", "who", "where", "when",
    "how", "available", "library", "nfsu", "stacks", "copies", "copy",
    "written", "authored", "published", "title", "titles", "work", "works",
}

# ---------------------------------------------------------------------------
# Hindi (Devanagari) → English routing scaffolding.
# The suggestion chips and common library phrases are mapped fully;
# remaining Devanagari tokens map through the term table.
# ---------------------------------------------------------------------------

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

_HI_PHRASES = {
    "फोरेंसिक डीएनए पर पुस्तकें खोजें": "find books on forensic DNA",
    "फोरेंसिक dna पर पुस्तकें खोजें": "find books on forensic DNA",
    "साइबर अपराध जांच की पुस्तकें": "find books on cybercrime investigation",
    "क्या फोरेंसिक टॉक्सिकोलॉजी पर पुस्तकें हैं?": "find books on forensic toxicology",
    "पुस्तकालय समय और नियम": "library timings and rules",
    "मेरी पुस्तक नवीनीकृत करें": "renew my book",
    "ऑफ कैंपस पर onos कैसे उपयोग करें?": "how to access ONOS off campus",
    "डिजिटल फोरेंसिक्स पर शोध प्रबंध खोजें": "find theses on digital forensics",
    "आपराधिक जांच में कृत्रिम बुद्धिमत्ता पर पुस्तकें": "find books on artificial intelligence in criminal investigation",
}

_HI_TERMS = {
    "पुस्तकें": "books", "पुस्तक": "book", "पुस्तकालय": "library",
    "खोजें": "find", "खोज": "search", "दिखाएं": "show", "दिखाइए": "show",
    "दिखाओ": "show", "बताएं": "show",
    "डीएनए": "DNA", "फोरेंसिक": "forensic", "फोरेंसिक्स": "forensics",
    "साइबर": "cyber", "अपराध": "crime", "आपराधिक": "criminal",
    "जांच": "investigation", "विषय": "subject", "लेखक": "author",
    "शोध": "research", "प्रबंध": "thesis", "निबंध": "thesis",
    "समय": "timing", "समय-सारिणी": "timing", "नियम": "rules",
    "नवीनीकृत": "renew", "नवीकरण": "renew", "जमा": "return",
    "टॉक्सिकोलॉजी": "toxicology", "डिजिटल": "digital",
    "कृत्रिम": "artificial", "बुद्धिमत्ता": "intelligence",
    "मनोविज्ञान": "psychology", "विषय": "subject",
    "किताबें": "books", "पत्रिकाएँ": "journals", "पत्रिकाएं": "journals",
    "सदस्यता": "membership", "पंजीकरण": "registration",
    "संपर्क": "contact", "सहायता": "help", "प्रश्न": "question",
    "कब": "when", "क्या": "what", "कैसे": "how", "कहाँ": "where",
    "हैं": "", "है": "", "की": "", "के": "", "का": "", "को": "",
    "पर": "on", "में": "in", "और": "and", "या": "or", "से": "from",
    "मेरी": "my", "मेरा": "my", "मेरे": "my", "आपका": "your",
    "ऑफ": "off", "कैंपस": "campus", "कैसे": "how", "उपयोग": "access",
    "करें": "", "करो": "", "लिए": "for", "वाले": "",
    "प्रारंभिक": "introductory", "छात्रों": "students",
    "अध्ययन": "study", "संसाधन": "resources", "उपलब्ध": "available",
}


def _hindi_to_english(message: str) -> str:
    """Route Hindi library phrases into the English deterministic pipeline."""
    lowered = message.strip().lower()
    if lowered in _HI_PHRASES:
        return _HI_PHRASES[lowered]
    # token-wise mapping for free-form Hindi
    tokens = re.findall(r"[\u0900-\u097F]+|[A-Za-z0-9]+", message)
    mapped: List[str] = []
    for tok in tokens:
        if tok in _HI_PHRASES:
            mapped.append(_HI_PHRASES[tok])
        elif tok in _HI_TERMS:
            replacement = _HI_TERMS[tok]
            if replacement:
                mapped.append(replacement)
        elif _DEVANAGARI_RE.search(tok):
            # unknown Devanagari token — drop rather than send garbage to KOHA
            continue
        else:
            mapped.append(tok)
    return " ".join(mapped).strip()


def _is_hindi(text: str) -> bool:
    return bool(_DEVANAGARI_RE.search(text or ""))


def _clean_keywords(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-']*", text)
    kept = [w for w in words if w.lower() not in _STOPWORDS]
    # If everything was a stopword, the phrase carries no topical signal.
    return " ".join(kept)


def _is_isbn_candidate(value: str) -> bool:
    digits = value.replace("-", "").replace(" ", "")
    if len(digits) == 10:
        return re.fullmatch(r"\d{9}[\dXx]", digits) is not None
    if len(digits) == 13:
        return digits.isdigit()
    return False


def parse_query(message: str) -> SearchIntent:
    """Parse a user message into a SearchIntent (search or non-search)."""
    raw = (message or "").strip()
    intent = SearchIntent(raw_query=raw)

    if not raw:
        return intent

    # Hindi entry point: map to English before the deterministic pipeline.
    if _is_hindi(raw):
        translated = _hindi_to_english(raw)
        if translated:
            intent.raw_query = translated
            text = translated
        else:
            text = raw
    else:
        text = raw

    # --- ISBN ---
    isbn_match = _ISBN_RE.search(text)
    if isbn_match and _is_isbn_candidate(isbn_match.group(1)):
        intent.isbn = isbn_match.group(1).replace("-", "").replace(" ", "")
        intent.is_search = True
        intent.confidence = 0.95
        intent.keywords = intent.isbn
        intent.facets = intent.describe()
        return intent

    # --- Year filters ---
    year_range = _YEAR_RANGE_RE.search(text)
    if year_range:
        years = re.findall(r"((?:19|20)\d{2})", year_range.group(0))
        if len(years) == 2:
            intent.year_after = min(int(years[0]), int(years[1])) - 1
            intent.year_before = max(int(years[0]), int(years[1])) + 1
        text = _YEAR_RANGE_RE.sub(" ", text)
    else:
        year_after = _YEAR_AFTER_RE.search(text)
        if year_after:
            intent.year_after = int(year_after.group(1))
            # avoid treating "in 2020" style with "after 2020"
            text = _YEAR_AFTER_RE.sub(" ", text)
        year_before = _YEAR_BEFORE_RE.search(text)
        if year_before:
            intent.year_before = int(year_before.group(1))
            text = _YEAR_BEFORE_RE.sub(" ", text)
        year_pub = _YEAR_PUBLISHED_RE.search(text)
        if year_pub and intent.year_after is None and intent.year_before is None:
            y = int(year_pub.group(1))
            intent.year_after = y - 1
            intent.year_before = y + 1
            text = _YEAR_PUBLISHED_RE.sub(" ", text)

    # --- Resource type ---
    for pattern, rtype in _TYPE_MAP:
        if pattern.search(text):
            intent.resource_type = rtype
            # keep the term for subject context unless it is the whole query
            break

    # --- Author ---
    for pattern in _AUTHOR_PATTERNS:
        m = pattern.search(text)
        if m:
            author = m.group("author").strip(" .,:;-'\"")
            # reject common false positives (capitalised sentence starters)
            if author.lower() not in _STOPWORDS and len(author) >= 3:
                intent.author = author
                text = pattern.sub(" ", text)
            break

    # --- Publisher ---
    pub_match = _PUBLISHER_RE.search(text)
    if pub_match:
        publisher = pub_match.group(1).strip()
        if publisher.lower() not in _STOPWORDS and len(publisher) >= 2:
            intent.publisher = publisher
            text = _PUBLISHER_RE.sub(" ", text)

    # --- Explicit title ---
    title_match = _TITLE_RE.search(text)
    if title_match:
        candidate = (title_match.group(1) or title_match.group(2) or "").strip()
        if candidate.lower() not in _STOPWORDS and len(candidate) >= 3:
            intent.title = candidate
            text = _TITLE_RE.sub(" ", text)
    else:
        quoted = _TITLE_QUOTED_RE.search(text)
        if quoted:
            candidate = quoted.group(1).strip()
            if candidate.lower() not in _STOPWORDS and len(candidate) >= 3:
                intent.title = candidate
                text = _TITLE_QUOTED_RE.sub(" ", text)

    # --- Leading publisher token: "Springer books on X", "Elsevier journals about Y" ---
    if not intent.publisher:
        lead_pub = _LEAD_PUB_RE.match(text)
        if lead_pub:
            candidate = lead_pub.group(1).strip()
            if candidate.lower() not in _STOPWORDS:
                intent.publisher = candidate
                text = _LEAD_PUB_RE.sub(" ", text, count=1)

    # --- Subject / keywords (everything remaining) ---
    cleaned = _clean_keywords(text)
    intent.subject = cleaned or None
    intent.keywords = cleaned or raw

    # --- Search trigger ---
    has_search_verb = bool(_SEARCH_VERBS.search(raw))
    has_structured_field = any(
        [intent.isbn, intent.author, intent.title, intent.publisher,
         intent.year_after, intent.year_before]
    )
    looks_like_topic = len(cleaned.split()) >= 1 if cleaned else False

    if has_structured_field:
        intent.is_search = True
        intent.confidence = 0.9
    elif has_search_verb and looks_like_topic:
        intent.is_search = True
        intent.confidence = 0.75
    elif looks_like_topic and len(cleaned.split()) >= 2 and _looks_like_noun_phrase(cleaned):
        # e.g. bare "forensic DNA analysis"
        intent.is_search = True
        intent.confidence = 0.55

    if intent.is_search and not intent.title and intent.subject:
        # default subject-led search when no clearer field applies
        pass

    intent.facets = intent.describe()
    return intent


def _looks_like_noun_phrase(text: str) -> bool:
    """Heuristic: multi-word lowercase-ish phrase that reads as a topic."""
    words = text.split()
    if len(words) < 2:
        return False
    # reject questions that slipped through
    if re.search(r"\?|^(who|what|where|when|why|how|can|do|does|is|are)\b", text, re.IGNORECASE):
        return False
    topic_markers = re.compile(
        r"forensic|crime|criminal|evidence|science|investigation|cyber|"
        r"digital|toxicology|psychology|questioned|document|dna|fingerprint|"
        r"ballistics|question|law|legal|AI|artificial|intelligence|data|"
        r"network|security|firensic|fire|accident|speed|paint|glass|fiber|"
        r"drug|narcotic|psychiatry|handwriting|accounting|fraud",
        re.IGNORECASE,
    )
    return bool(topic_markers.search(text)) or len(words) >= 3
