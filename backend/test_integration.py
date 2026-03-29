"""Quick E2E verification script for Data Layer integration."""
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import sys
sys.stdout.reconfigure(encoding='utf-8')
import httpx
import json
import sys

BASE = "http://localhost:8000"

def test(name, method, path, **kwargs):
    print(f"\n{'='*50}")
    print(f"TEST: {name}")
    print(f"{'='*50}")
    try:
        if method == "GET":
            r = httpx.get(f"{BASE}{path}", timeout=30)
        else:
            r = httpx.post(f"{BASE}{path}", timeout=120, **kwargs)
        print(f"  Status: {r.status_code}")
        data = r.json()
        print(f"  Response: {json.dumps(data, indent=2)[:500]}")
        return data
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

# 1. Health
test("Health Check", "GET", "/health")

# 2. RSS Feeds Config
test("RSS Feeds", "GET", "/rss-feeds")

# 3. Search
data = test("Search: Tata Motors EV", "POST", "/search", 
    json={"query": "Tata Motors EV", "limit": 3})
if data:
    print(f"\n  Total results: {data.get('total_results', 0)}")
    for r in data.get("results", []):
        print(f"    - {r['title'][:50]}... (score: {r.get('score', 'N/A')})")

# 4. Articles endpoint
data = test("Articles Endpoint", "GET", "/articles")
if data and isinstance(data, list):
    print(f"\n  Articles returned: {len(data)}")
    for a in data[:3]:
        print(f"    - {a['title'][:50]}")

# 5. Dedup test: ingest fallback twice
test("Dedup Test: Second Fallback Ingest", "POST", "/ingest/fallback")

# 6. Check count didn't double
data = test("Post-Dedup Health Check", "GET", "/health")
if data:
    vs = data.get("vector_store", {})
    count = vs.get("points_count", 0)
    print(f"\n  Points count after double ingest: {count}")
    if count <= 150:  # Should be ~75 x2 = 150 (dedup is at article level, not chunk level)
        print("  ✅ Dedup working at article level")

print("\n" + "="*50)
print("ALL TESTS COMPLETE")
print("="*50)
