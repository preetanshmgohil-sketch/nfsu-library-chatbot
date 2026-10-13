import sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=120)
for q in ["Find books on forensic DNA analysis", "What are the library timings?", "Find books on forensic DNA analysis"]:
    t0 = time.time()
    r = c.post("/api/v1/chat", json={"message": q, "locale": "en"})
    dt = time.time() - t0
    d = r.json()
    cards = d.get("cards") or []
    print(f"{dt:5.1f}s  cards={len(cards):2}  {q}")

import asyncio, sys as s2
s2.path.insert(0, ".")
from app.services.koha import koha_service

async def t():
    t0 = time.time()
    html, url = await koha_service._fetch(
        "/cgi-bin/koha/opac-search.pl", {"q": "forensic DNA", "weight_search": "1"}
    )
    print(f"raw KOHA single fetch: {time.time()-t0:.1f}s  html={len(html) if html else 0}")
    # full cascade timing
    t0 = time.time()
    result = await koha_service.search("", "forensic DNA analysis")
    print(f"full cascade: {time.time()-t0:.1f}s  records={len(result.records)}")

asyncio.run(t())
