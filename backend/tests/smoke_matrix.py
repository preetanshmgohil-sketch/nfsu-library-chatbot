"""Smoke matrix: every example query from the institutional requirements."""
import sys
import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=15)

QUERIES = [
    "Find books on forensic DNA analysis.",
    "Show books on cybercrime investigation.",
    "Do we have any books on forensic toxicology?",
    "Find publications about digital evidence and cyber forensics.",
    "Search for books written by Calder Wong.",
    "Find books published after 2020 on forensic psychology.",
    "Show resources on artificial intelligence in criminal investigation.",
    "Find books on criminology available in the library.",
    "Search for resources on questioned document examination.",
    "Find introductory books on forensic science for postgraduate students.",
    "Title search: Handbook of Forensic Science",
    "Find a book called Digital Evidence Handbook",
    "Springer books on fingerprint analysis",
    "ISBN 9780123456789",
    "Show books by Calder Wong",
    "Find theses on cyber forensics",
    "What are the library rules for borrowing?",
    "How can I access research databases?",
    "Tell me about citation tools",
    "Where can I submit my thesis?",
    "Do we have resources on forensic ballistics?",
    "Find journals on digital investigation",
]

failures = 0
for q in QUERIES:
    r = c.post("/api/v1/chat", json={"message": q, "locale": "en"})
    if r.status_code != 200:
        print(f"HTTP {r.status_code} | {q}")
        failures += 1
        continue
    d = r.json()
    kind = d["kind"]
    url = d.get("search_url", "") or ""
    short = url.split("?", 1)[-1] if "?" in url else ""
    facets = d.get("facets") or {}
    # sanity: every reply has non-empty message; searches have a KOHA url
    ok = bool(d.get("message"))
    if kind == "catalog":
        ok = ok and bool(url)
    status = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{status:4} | {kind:8} | {q[:56]:56} | {short[:50]}")
    if facets:
        print(f"       facets={facets}")

print(f"\n{'ALL PASS' if failures == 0 else str(failures) + ' FAILED'} ({len(QUERIES)} queries)")
sys.exit(1 if failures else 0)
