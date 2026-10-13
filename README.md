# NFSU Secure Library Chatbot — KOHA OPAC Integration

AI-powered conversational assistant for the National Forensic Sciences University
Library, embedded as a floating widget in the KOHA OPAC
([catalog.nfsu.ac.in](https://catalog.nfsu.ac.in)) **without modifying KOHA core**.

---

## What is in the box

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI service — chat API, guardrails, KOHA integration, FAQ brain |
| `widget/dist/nfsu-chatbot.js` | Zero-dependency embeddable widget (Shadow DOM isolated) |
| `integration/koha-embed-snippet.html` | One-block paste-in for the OPAC template |
| `integration/demo-opac.html` | Local OPAC shell for development and QA |
| `docs/screenshot-*.png` | UI states (light, dark, mobile, search, FAQ) |
| `backend/tests/` | Unit tests + 22-query smoke matrix from the institutional requirements |

---

## Architecture

```
KOHA OPAC page
   └── nfsu-chatbot.js  (Shadow DOM widget, bottom-right drawer)
          │  POST /api/v1/chat
          ▼
       FastAPI backend
          ├── security/guardrails.py   input sanitize · prompt-injection block · output PII/URL scan
          ├── security/rate_limit.py   sliding-window per-IP limit
          ├── services/query_parser.py NL → structured intent (title/author/ISBN/subject/year/publisher)
          ├── services/faq.py          offline FAQ knowledge base (no LLM required)
          ├── services/koha.py         KOHA REST (optional) + OPAC deep-link builder (always works)
          ├── services/llm.py          Hugging Face private endpoint (optional)
          └── services/orchestrator.py routes every turn, guarantees a graceful fallback
```

**Modes of operation** (verified live against catalog.nfsu.ac.in)

1. **Public OPAC scrape (default, zero config, zero credentials)** — the
   backend fetches the real `/cgi-bin/koha/opac-search.pl` results page and
   parses title, author, publisher, year, ISBN, edition, availability,
   call number, and branch into structured cards. Multi-word queries that
   return 0 results automatically cascade: requested index → keyword index →
   OR of content words. Unique ISBN/title matches that KOHA redirects to a
   detail page are detected and turned into a single card.
2. **REST mode** — set `KOHA_REST_BASE_URL` + `KOHA_REST_TOKEN` (KOHA 22.05+)
   for structured API results instead of scraping.
3. **LLM-enhanced** — set `LLM_API_TOKEN=hf_...` (Hugging Face Inference
   Providers router) for query rewriting and conversational summaries.
   Recommended models: `Qwen/Qwen2.5-7B-Instruct` (quality, multilingual
   Hindi), `Qwen/Qwen2.5-3B-Instruct` (fast), or
   `meta-llama/Llama-3.1-8B-Instruct`. If the LLM is down, the bot degrades
   to scrape + FAQ automatically — it never shows a cold error.

**Live-verified KOHA contract** (catalog.nfsu.ac.in)

| Item | Value |
| --- | --- |
| Search | `GET /cgi-bin/koha/opac-search.pl?q=…&weight_search=1[&idx=…]` |
| Record | `/cgi-bin/koha/opac-detail.pl?biblionumber=<id>` |
| Indexes | `''` keyword · `ti` title · `au` author · `su` subject · `nb` ISBN · `ns` ISSN · `se` series · `callnum` call number |
| Note | Author index is **`au`** (not `ac`). Subject headings are sparse — keyword + OR fallback is required for recall. |

---

## Quick start (Windows — one command)

```bat
demo.bat     :: starts backend and opens the OPAC demo at http://127.0.0.1:8000/demo
```

The demo is served by the backend itself (same origin — no CORS, no second server).
It is a full NFSU library catalogue page (search, collections, hours, contact) with the
chat widget bottom-right. No developer instructions appear in the UI.

Other launchers:

```bat
start.bat    :: backend only on http://127.0.0.1:8000  (demo at /demo)
stop.bat     :: kill anything on :8000 and :8080
test.bat     :: unit tests + live integration smoke against catalog.nfsu.ac.in
```

First run creates a venv, installs dependencies, and writes `backend\.env`.
Open `backend\.env` and paste your Hugging Face token to enable AI answers:

```env
LLM_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
LLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
```

No endpoint URL needed — the backend uses the HF Inference Providers router.
If your network cannot resolve `catalog.nfsu.ac.in`, set `KOHA_PIN_IP` in
`.env` to the OPAC's current IP (observed: `117.239.182.15`); the Host header
stays correct so the KOHA vhost still answers.

## Quick start (manual)

```bash
# 1. Backend (also serves the demo page)
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                           # then edit values
uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000/demo
```

Run the test suites:

```bash
cd backend
python tests/test_query_parser.py     # parser unit tests
python tests/test_guardrails.py       # security unit tests
python tests/live_verify.py           # LIVE queries against catalog.nfsu.ac.in
python tests/smoke_matrix.py          # 22 requirement example queries
```

---

## Deploying to NFSU

### 1. Host the backend

Any Ubuntu/Debian host or container behind TLS:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Use systemd or Docker + a reverse proxy (nginx/Caddy) that terminates HTTPS.
Serve the widget from the same host:

```nginx
location /static/ {
    alias /srv/nfsu-chatbot/widget/dist/;
}
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}
```

### 2. Configure environment

Copy `backend/.env.example` → `backend/.env` and set at minimum:

```env
ALLOWED_ORIGINS=["https://catalog.nfsu.ac.in"]
KOHA_OPAC_BASE_URL=https://catalog.nfsu.ac.in
WIDGET_ENABLED=true
```

Optional (recommended for production polish):

```env
KOHA_REST_BASE_URL=https://catalog.nfsu.ac.in/api/v1
KOHA_REST_TOKEN=<koha patron token>
LLM_ENDPOINT_URL=https://<your-endpoint>.endpoints.huggingface.cloud
LLM_API_TOKEN=hf_<token>
```

### 3. Embed in KOHA (no core changes)

Paste the block from `integration/koha-embed-snippet.html` immediately before
`</body>` in the OPAC footer include, typically:

```
koha-tmpl/opac-en/includes/opac-bottommenu.inc
```

(or your theme's equivalent footer template). The widget is a single
`<script>` tag — nothing in KOHA Perl, intranet, or database is touched, so
KOHA upgrades will not break it.

### 4. Operator controls

| Control | How |
| --- | --- |
| Disable widget | `WIDGET_ENABLED=false` (or `GET /api/v1/config` returns `enabled:false` and the trigger removes itself) |
| Emergency suspend | `WIDGET_SUSPENDED=true` — instant kill-switch, no redeploy of KOHA |
| Change suggestions / welcome | edit `backend/config/widget_config.json` (per-locale) |
| Change FAQ answers | edit `backend/config/faq_knowledge.json` |
| Add a language | add locale code to `SUPPORTED_LOCALES`, add strings in `widget_config.json` + `faq_knowledge.json` + the widget `STR` table |

---

## Security model

| Layer | Control |
| --- | --- |
| Inbound | 2 000-char cap · control-char strip · whitespace normalize |
| Prompt injection | 25+ regex heuristics (ignore-previous, role-play, DAN, fake `[INST]`/`<<SYS>>`, system-prompt extraction, jailbreak vocabulary) → polite refusal |
| Rate limit | 30 requests / 60 s / IP, `Retry-After` header on 429 |
| Outbound | PII patterns redacted (email, IN phone, Aadhaar, card-like digit runs) · URLs stripped unless host is on the NFSU/ONOS allowlist |
| Network | CORS locked to `catalog.nfsu.ac.in` (+ localhost in dev) · no credentials in CORS |
| LLM | Private HF endpoint only · hardened system prompt · never invents records or URLs · history truncated to 12 turns |
| Data | No message content is logged or stored · session IDs are random UUIDs · analytics counts only |

---

## Capability checklist (institutional requirements)

- [x] Floating icon on every OPAC page, bottom-right, non-obstructive
- [x] Responsive drawer — 380×600 desktop, full-screen ≤480 px
- [x] Welcome message + suggested questions + quick-access chips
- [x] Conversational search without leaving the OPAC
- [x] Deep links to individual KOHA records and search result sets
- [x] Existing OPAC customisations untouched (Shadow DOM, no core edits)
- [x] Enable / disable / temporary suspend facility
- [x] Accessible fallback link to conventional KOHA advanced search
- [x] Title, author, ISBN, subject, publisher, year, and combined queries
- [x] Follow-up refinement (author, widen year, new search chips)
- [x] Spelling / query rewrite when LLM is configured
- [x] Bibliographic metadata cards with availability chip
- [x] FAQ: timings, circulation, membership, ONOS, databases, citation, thesis, ILL, contact
- [x] Light / dark mode with system default + manual override persistence
- [x] WCAG 2.1 AA: focus trap, Esc close, focus return, `aria-live` log, visible focus rings
- [x] `prefers-reduced-motion` respected
- [x] Multilingual scaffolding (English + Hindi end-to-end)
- [x] Privacy-preserving analytics posture (counts only, no content)
- [x] Graceful degradation — LLM down, REST down, or network blip never blocks the user

---

## Design notes

- **Palette** — NFSU institutional crimson `#991B1B` / `#E11D48` (dark) and deep
  navy `#0F172A` on cool lab-paper surfaces. Availability uses a restrained
  teal `#0E7490` / `#22D3EE` (evokes UV-reveal fluorescence) so "available"
  reads instantly without competing with the brand crimson.
- **Type** — Space Grotesk (display), IBM Plex Sans (body), IBM Plex Mono
  (facet strips and the `NFSU LIBRARY` eyebrow). Mono metadata strips on
  result cards echo catalogue-card / lab-readout vernacular.
- **Signature** — the mono facet strip (`SUBJECT: FORENSIC DNA ANALYSIS`)
  surfaces exactly what the parser understood, so users can see and correct
  the interpretation; paired with the slow concentric "scan" pulse on the
  trigger button.
- **Isolation** — everything lives in a Shadow Root, so KOHA's CSS and the
  widget can never bleed into each other.

---

## Support

Backend health: `GET /api/v1/health`
Widget config: `GET /api/v1/config?locale=en`
API docs (dev only): `http://localhost:8000/docs`
