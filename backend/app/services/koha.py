"""KOHA catalogue integration — wired to the LIVE NFSU OPAC.

Verified against catalog.nfsu.ac.in (KOHA, public OPAC):

  Search : GET /cgi-bin/koha/opac-search.pl
           idx ∈ {'', ti, au, su, nb, ns, se, callnum}   q=<query>
           + weight_search=1
  Record : /cgi-bin/koha/opac-detail.pl?biblionumber=<id>

Two result modes:
1. **Public OPAC scrape (default, zero credentials)** — fetches the real
   search-results page and parses title / author / publisher / year /
   ISBN / availability / call number into structured cards.
2. **REST mode (optional)** — KOHA /api/v1 when a token is configured.

Deep-link URLs are always correct even when scraping is unavailable.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlencode

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Short TTL cache so repeat questions (and the demo page) feel instant.
_CACHE_TTL_SECONDS = 300.0
_CACHE_MAX = 256
_search_cache: "dict[str, Tuple[float, CatalogResult]]" = {}


def _cache_get(key: str) -> Optional[CatalogResult]:
    hit = _search_cache.get(key)
    if not hit:
        return None
    expires_at, result = hit
    if time.monotonic() > expires_at:
        _search_cache.pop(key, None)
        return None
    return result


def _cache_put(key: str, result: CatalogResult) -> None:
    if len(_search_cache) >= _CACHE_MAX:
        _search_cache.clear()
    _search_cache[key] = (time.monotonic() + _CACHE_TTL_SECONDS, result)

# KOHA OPAC indexes verified on catalog.nfsu.ac.in
IDX_KEYWORD = ""
IDX_TITLE = "ti"
IDX_AUTHOR = "au"
IDX_SUBJECT = "su"
IDX_ISBN = "nb"
IDX_ISSN = "ns"
IDX_SERIES = "se"
IDX_CALLNUM = "callnum"


@dataclass
class BibRecord:
    biblionumber: str
    title: str
    author: str = ""
    publisher: str = ""
    year: str = ""
    isbn: str = ""
    subject: str = ""
    edition: str = ""
    material_type: str = ""
    call_number: str = ""
    branch: str = ""
    availability: str = "unknown"  # available | checked_out | unknown
    availability_note: str = ""
    url: str = ""
    thumbnail: str = ""

    def to_dict(self) -> dict:
        return {
            "biblionumber": self.biblionumber,
            "title": self.title,
            "author": self.author,
            "publisher": self.publisher,
            "year": self.year,
            "isbn": self.isbn,
            "subject": self.subject,
            "edition": self.edition,
            "material_type": self.material_type,
            "call_number": self.call_number,
            "branch": self.branch,
            "availability": self.availability,
            "availability_note": self.availability_note,
            "url": self.url,
            "thumbnail": self.thumbnail,
        }


@dataclass
class CatalogResult:
    records: List[BibRecord] = field(default_factory=list)
    total: int = 0
    search_url: str = ""
    advanced_search_url: str = ""
    source: str = "opac_scrape"  # opac_scrape | rest | deep_link
    query_params: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "records": [r.to_dict() for r in self.records],
            "total": self.total,
            "search_url": self.search_url,
            "advanced_search_url": self.advanced_search_url,
            "source": self.source,
        }


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = (
        text.replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&rsquo;", "'")
        .replace("&lsquo;", "'")
        .replace("&rdquo;", '"')
        .replace("&ldquo;", '"')
        .replace("&nbsp;", " ")
        .replace("&ndash;", "-")
        .replace("&mdash;", "—")
        .replace("&hellip;", "…")
    )
    return re.sub(r"\s+", " ", text).strip()


class KohaService:
    def __init__(self) -> None:
        self.opac_base = settings.koha_opac_base_url.rstrip("/")
        self.rest_base = (settings.koha_rest_base_url or "").rstrip("/") or None
        self.rest_token = settings.koha_rest_token
        # Optional IP pin for environments where the hostname does not resolve
        # (keeps Host header = hostname so the KOHA vhost still answers).
        self.pin_ip = (settings.koha_pin_ip or "").strip() or None

    # ------------------------------------------------------------------
    # HTTP helper — handles optional IP pin + Host header
    # ------------------------------------------------------------------

    def _request_url(self, path: str) -> tuple[str, Dict[str, str]]:
        headers: Dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json",
        }
        if self.pin_ip:
            # Connect by IP, preserve vhost via Host header, skip SNI verify.
            host = self.opac_base.split("://", 1)[-1].split("/", 1)[0]
            headers["Host"] = host
            url = f"https://{self.pin_ip}{path}"
            return url, headers
        return f"{self.opac_base}{path}", headers

    async def _fetch(self, path: str, params: Optional[dict] = None) -> tuple[Optional[str], str]:
        """Returns (html, final_url). final_url matters: KOHA redirects
        unique ISBN/title matches straight to the detail page."""
        url, headers = self._request_url(path)
        verify = not bool(self.pin_ip)
        try:
            async with httpx.AsyncClient(
                timeout=settings.koha_scrape_timeout_seconds,
                headers=headers,
                follow_redirects=True,
                verify=verify,
            ) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    return resp.text, str(resp.url)
                logger.warning("KOHA fetch %s -> %s", path, resp.status_code)
        except Exception as exc:  # noqa: BLE001 — never fail the user
            logger.warning("KOHA fetch failed %s: %s", path, type(exc).__name__)
        return None, ""

    # ------------------------------------------------------------------
    # URL builders (always correct for the live NFSU OPAC)
    # ------------------------------------------------------------------

    def build_opac_search_url(
        self,
        idx: str,
        q: str,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> str:
        params: Dict[str, str] = {"q": q, "weight_search": "1"}
        # KOHA treats empty idx as "Library catalog" (keyword) — omit it.
        if idx:
            params["idx"] = idx
        if extra_params:
            for key, value in extra_params.items():
                if key not in ("idx", "q", "weight_search") and value:
                    params[key] = str(value)
        return f"{self.opac_base}/cgi-bin/koha/opac-search.pl?{urlencode(params)}"

    def build_advanced_search_url(self) -> str:
        return f"{self.opac_base}/cgi-bin/koha/opac-search.pl"

    def build_record_url(self, biblionumber: str) -> str:
        return (
            f"{self.opac_base}/cgi-bin/koha/opac-detail.pl"
            f"?biblionumber={quote_plus(str(biblionumber))}"
        )

    # ------------------------------------------------------------------
    # Public search
    # ------------------------------------------------------------------

    async def search(
        self,
        idx: str,
        q: str,
        limit: Optional[int] = None,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> CatalogResult:
        limit = min(limit or settings.koha_default_results, settings.koha_max_results)
        search_url = self.build_opac_search_url(idx, q, extra_params)
        advanced = self.build_advanced_search_url()

        cache_key = f"{idx}|{q}|{limit}|{extra_params or ''}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        # 1) REST mode when configured
        if self.rest_base and self.rest_token:
            try:
                records = await self._rest_search(idx, q, limit, extra_params)
                if records:
                    return CatalogResult(
                        records=records[:limit],
                        total=len(records),
                        search_url=search_url,
                        advanced_search_url=advanced,
                        source="rest",
                    )
            except Exception:
                pass

        # 2) Public OPAC scrape — real records, no credentials required
        if settings.koha_scrape_enabled:
            records, total, source = await self._scrape_search(idx, q, extra_params, limit)

            # Academic KOHA installs often have sparse subject headings, and
            # multi-word queries are AND-matched. Cascade:
            #   1) requested index
            #   2) keyword index
            #   3) OR of content words (proven to work on catalog.nfsu.ac.in)
            if not records and idx:
                records, total, source = await self._scrape_search(
                    "", q, extra_params, limit
                )

            if not records:
                or_query = self._or_fallback_query(q)
                if or_query:
                    records, total, source = await self._scrape_search(
                        "", or_query, extra_params, limit
                    )

            if records:
                result = CatalogResult(
                    records=records,
                    total=total,
                    search_url=search_url,
                    advanced_search_url=advanced,
                    source=source,
                )
                _cache_put(cache_key, result)
                return result

        # 3) Deep-link fallback — still a working KOHA URL for the browser
        result = CatalogResult(
            records=[],
            total=0,
            search_url=search_url,
            advanced_search_url=advanced,
            source="deep_link",
        )
        _cache_put(cache_key, result)
        return result

    @staticmethod
    def _or_fallback_query(q: str) -> str:
        """Build 'word1 OR word2' from content words when AND-search returns 0."""
        stop = {
            "a", "an", "the", "on", "in", "of", "for", "to", "and", "or", "with",
            "about", "books", "book", "resources", "resource", "materials",
            "publications", "any", "some", "find", "show", "search", "list",
            "do", "we", "have", "available", "library", "please",
        }
        words = re.findall(r"[A-Za-z][A-Za-z0-9\-']*", q or "")
        content = [w for w in words if w.lower() not in stop and len(w) >= 3]
        if len(content) < 2:
            return ""
        return " OR ".join(content[:5])

    async def _scrape_search(
        self,
        idx: str,
        q: str,
        extra_params: Optional[Dict[str, str]],
        limit: int,
    ) -> tuple[List[BibRecord], int, str]:
        path_params: Dict[str, object] = {"q": q, "weight_search": "1"}
        if idx:
            path_params["idx"] = idx
        if extra_params:
            for key, value in extra_params.items():
                if key not in ("idx", "q", "weight_search") and value:
                    path_params[key] = value

        html, final_url = await self._fetch("/cgi-bin/koha/opac-search.pl", path_params)
        if not html:
            return [], 0, "deep_link"

        # KOHA redirects a unique ISBN/title match straight to the detail page.
        if "opac-detail.pl" in final_url or 'id="biblio-title"' in html or "holdingst" in html:
            record = self._parse_detail_as_record(html, final_url)
            if record:
                return [record], 1, "opac_scrape_detail"

        records, total = self._parse_search_results(html, limit)
        return records, total, "opac_scrape"

    # ------------------------------------------------------------------
    # Live OPAC HTML parser (KOHA opac-results.tt markup)
    # ------------------------------------------------------------------

    def _parse_search_results(self, html: str, limit: int) -> tuple[List[BibRecord], int]:
        records: List[BibRecord] = []

        # Total count: "Results of search for 'x'" / "1 to 20 of 43 results"
        total = 0
        m = re.search(r"of\s+<[^>]*>\s*(\d+)\s*</[^>]+>\s*results", html, re.I)
        if not m:
            m = re.search(r"(\d+)\s+results?\s+found", html, re.I)
        if not m:
            m = re.search(r"of\s+(\d+)\s+results", html, re.I)
        if m:
            try:
                total = int(m.group(1))
            except ValueError:
                total = 0

        # Each result lives in a title_summary_<biblionumber> block.
        blocks = re.finditer(
            r'<div[^>]+id="title_summary_(\d+)"[^>]*>(.*?)(?=<div[^>]+id="title_summary_\d+"|<div[^>]+id="noresults"|<nav[^>]+pagination|$)',
            html,
            re.S | re.I,
        )

        for match in blocks:
            if len(records) >= limit:
                break
            biblionumber = match.group(1)
            block = match.group(2)

            # --- Title + author from the anchor ---
            title = ""
            author = ""
            am = re.search(
                r'<a[^>]+href="[^"]*opac-detail\.pl\?biblionumber=' + re.escape(biblionumber) +
                r'"[^>]*class="title"[^>]*>(.*?)</a>',
                block,
                re.S | re.I,
            )
            if not am:
                am = re.search(r'<a[^>]+class="title"[^>]*>(.*?)</a>', block, re.S | re.I)
            if am:
                raw = am.group(1)
                resp = re.search(
                    r'<span[^>]+class="title_resp_stmt"[^>]*>(.*?)</span>', raw, re.S | re.I
                )
                if resp:
                    author = _strip_tags(resp.group(1)).strip(" /")
                    raw = raw[: resp.start()]
                title = _strip_tags(raw).strip(" /")

            # Fallback author list
            if not author:
                auth_link = re.search(
                    r'opac-search\.pl\?q=au:[^"]*"[^"]*"[^>]*>(.*?)</a>', block, re.S | re.I
                )
                if auth_link:
                    author = _strip_tags(auth_link.group(1)).replace("[author]", "").strip()

            # --- Publisher / year / place ---
            publisher = ""
            year = ""
            pub_block = re.search(
                r'class="results_summary publisher"[^>]*>(.*?)</div>', block, re.S | re.I
            )
            if pub_block:
                pb = pub_block.group(1)
                pm = re.search(r'class="publisher_name"[^>]*>(.*?)</span>', pb, re.S | re.I)
                if pm:
                    publisher = _strip_tags(pm.group(1)).strip(" ,")
                ym = re.search(r'class="publisher_date"[^>]*>(.*?)</span>', pb, re.S | re.I)
                if ym:
                    year = _strip_tags(ym.group(1)).strip(" .,")

            # --- ISBN / edition / material type ---
            isbn = ""
            im = re.search(r"rft\.isbn=([0-9Xx\-]+)", block)
            if im:
                isbn = im.group(1).replace("-", "")

            edition = ""
            em = re.search(
                r'class="results_summary edition"[^>]*>(.*?)</div>', block, re.S | re.I
            )
            if em:
                edition = _strip_tags(em.group(1)).replace("Edition:", "").strip()

            material_type = ""
            tm = re.search(
                r'class="results_material_type"[^>]*>(.*?)</span>', block, re.S | re.I
            )
            if tm:
                material_type = _strip_tags(tm.group(1)).replace("Material type:", "").strip()

            # --- Availability ---
            availability = "unknown"
            availability_note = ""
            call_number = ""
            branch = ""
            av_block = re.search(
                r'class="results_summary availability"[^>]*>(.*?)</div>', block, re.S | re.I
            )
            if av_block:
                ab = av_block.group(1)
                if re.search(r"reallyavailable", ab, re.I):
                    availability = "available"
                elif re.search(r"checked\s*out|on\s*loan|notavailable", ab, re.I):
                    availability = "checked_out"
                cm = re.search(r'class="CallNumber"[^>]*>(.*?)</span>', ab, re.S | re.I)
                if cm:
                    call_number = _strip_tags(cm.group(1)).strip()
                bm = re.search(r'class="ItemBranch"[^>]*>(.*?)</span>', ab, re.S | re.I)
                if bm:
                    branch = _strip_tags(bm.group(1)).strip()
                availability_note = _strip_tags(ab)[:180]

            if not title:
                continue

            records.append(
                BibRecord(
                    biblionumber=biblionumber,
                    title=title,
                    author=author,
                    publisher=publisher,
                    year=year,
                    isbn=isbn,
                    edition=edition,
                    material_type=material_type,
                    call_number=call_number,
                    branch=branch,
                    availability=availability,
                    availability_note=availability_note,
                    url=self.build_record_url(biblionumber),
                )
            )

        if total == 0 and records:
            total = len(records)
        return records, total

    def _parse_detail_as_record(self, html: str, final_url: str) -> Optional[BibRecord]:
        """KOHA auto-redirects unique matches to opac-detail.pl — build one card."""
        biblionumber = ""
        m = re.search(r"biblionumber=(\d+)", final_url) or re.search(
            r"biblionumber=(\d+)", html
        )
        if m:
            biblionumber = m.group(1)
        if not biblionumber:
            return None

        title = ""
        tm = re.search(r'<span[^>]+class="biblio-title"[^>]*>(.*?)</span>', html, re.S | re.I)
        if tm:
            title = _strip_tags(tm.group(1)).strip(" /")
        if not title:
            tm = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
            if tm:
                title = _strip_tags(tm.group(1))
                title = re.sub(r"\s*[-|].*Koha.*$", "", title, flags=re.I).strip(" /")
        if not title:
            return None

        author = ""
        am = re.search(
            r'<a[^>]+href="[^"]*opac-search\.pl\?q=au:[^"]*"[^>]*>(.*?)</a>', html, re.S | re.I
        )
        if am:
            author = _strip_tags(am.group(1)).replace("[author]", "").strip()

        publisher = ""
        year = ""
        pm = re.search(r'class="publisher_name"[^>]*>(.*?)</span>', html, re.S | re.I)
        if pm:
            publisher = _strip_tags(pm.group(1)).strip(" ,")
        ym = re.search(r'class="publisher_date"[^>]*>(.*?)</span>', html, re.S | re.I)
        if ym:
            year = _strip_tags(ym.group(1)).strip(" .,")

        isbn = ""
        im = re.search(r"rft\.isbn=([0-9Xx\-]+)", html) or re.search(
            r"(?i)ISBN[:\s]*([0-9Xx\-]{10,17})", html
        )
        if im:
            isbn = im.group(1).replace("-", "")

        availability = "unknown"
        call_number = ""
        branch = ""
        if re.search(r"reallyavailable", html, re.I):
            availability = "available"
        elif re.search(r"checked\s*out|on\s*loan", html, re.I):
            availability = "checked_out"
        cm = re.search(r'class="CallNumber"[^>]*>(.*?)</span>', html, re.S | re.I)
        if cm:
            call_number = _strip_tags(cm.group(1)).strip()
        bm = re.search(r'class="ItemBranch"[^>]*>(.*?)</span>', html, re.S | re.I)
        if bm:
            branch = _strip_tags(bm.group(1)).strip()

        return BibRecord(
            biblionumber=biblionumber,
            title=title,
            author=author,
            publisher=publisher,
            year=year,
            isbn=isbn,
            call_number=call_number,
            branch=branch,
            availability=availability,
            url=self.build_record_url(biblionumber),
        )

    # ------------------------------------------------------------------
    # REST mode (optional)
    # ------------------------------------------------------------------

    async def _rest_search(
        self,
        idx: str,
        q: str,
        limit: int,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> List[BibRecord]:
        assert self.rest_base and self.rest_token
        endpoint = f"{self.rest_base}/records"
        params: Dict[str, object] = {"q": q, "limit": limit}
        if idx:
            params["idx"] = idx
        if extra_params:
            for key, value in extra_params.items():
                if key not in ("idx", "q") and value:
                    params[key] = value

        headers = {
            "Authorization": f"Bearer {self.rest_token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=12.0, headers=headers) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            payload = resp.json()

        items = payload if isinstance(payload, list) else payload.get("records", [])
        records: List[BibRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            biblionumber = str(
                item.get("biblio_id") or item.get("biblionumber") or item.get("id") or ""
            )
            records.append(
                BibRecord(
                    biblionumber=biblionumber,
                    title=str(item.get("title") or item.get("title_statement") or "Untitled"),
                    author=str(item.get("author") or ""),
                    publisher=str(item.get("publisher") or ""),
                    year=str(item.get("publicationyear") or item.get("year") or ""),
                    isbn=str(item.get("isbn") or ""),
                    availability=str(item.get("availability") or "unknown"),
                    url=self.build_record_url(biblionumber) if biblionumber else "",
                    thumbnail=str(item.get("thumbnail_url") or ""),
                )
            )
        return records


koha_service = KohaService()
