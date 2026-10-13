import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import asyncio
from app.services.koha import koha_service


async def probe():
    queries = [
        "cybercrime investigation",
        "cybercrime OR cyber",
        '"questioned document"',
        "questioned OR document",
        "forensic document",
        "document examination forensic",
    ]
    for q in queries:
        html, url = await koha_service._fetch(
            "/cgi-bin/koha/opac-search.pl", {"q": q, "weight_search": "1"}
        )
        if not html:
            print(f"FAIL {q!r}")
            continue
        recs, total = koha_service._parse_search_results(html, 3)
        print(f"q={q!r:40} recs={len(recs)} total={total}")
        for r in recs[:2]:
            print(f"   {r.title[:65]}")


asyncio.run(probe())
