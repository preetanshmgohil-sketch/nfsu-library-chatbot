import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import httpx

c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)
r = c.get("/")
print("root:", r.status_code, r.json())
r = c.get("/api/v1/health")
print("health:", r.status_code, r.json())
r = c.get("/demo")
print("demo status:", r.status_code, "len:", len(r.text))
checks = [
    "This page simulates",
    "uvicorn app.main",
    "Ignore previous instructions",
    'data-api-base="http://127.0.0.1:8000"',
]
for bad in checks:
    print(("LEAK" if bad in r.text else "clean"), "->", bad[:60])
print("widget src same-origin:", "/static/nfsu-chatbot.js" in r.text)
r2 = c.get("/static/nfsu-chatbot.js")
print("widget static:", r2.status_code, len(r2.content))
r3 = c.post("/api/v1/chat", json={"message": "Find books on forensic DNA analysis", "locale": "en"})
d = r3.json()
print("chat cards:", len(d.get("cards") or []))
print("chat keys:", sorted(d.keys())[:12])
# FAQ path should be instant
import time
t0 = time.time()
r4 = c.post("/api/v1/chat", json={"message": "What are the library timings?", "locale": "en"})
print(f"faq: {time.time()-t0:.2f}s status={r4.status_code}")
# repeat query should hit cache
t0 = time.time()
r5 = c.post("/api/v1/chat", json={"message": "Find books on forensic DNA analysis", "locale": "en"})
print(f"cached repeat: {time.time()-t0:.2f}s cards={len(r5.json().get('cards') or [])}")
# check any error message with wrong path
r6 = c.post("/api/v1/chat", json={"message": "zzzznotfoundzzz xyzabc", "locale": "en"})
d6 = r6.json()
print("empty-ish reply has cgi-bin path:", "cgi-bin" in str(d6))
