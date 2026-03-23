import asyncio
import aiohttp
import time
import json
from collections import defaultdict
from datetime import datetime
from statistics import mean

BASE_URL = "http://localhost:8000"

REQUESTS_PER_ENDPOINT = 200
RESULTS_FILE = "bench2_results.json"


ENDPOINTS = [
    ("GET", "/api/ping", None),
    ("GET", "/api/status", None),
    ("GET", "/api/random/async", None),
    ("GET", "/api/random/sync", None),
    ("GET", "/api/sum/10/20", None),
    ("GET", "/api/multiply/2.5/4.0", None),
    ("GET", "/api/users/123", None),
    ("GET", "/api/items/test", None),
    ("GET", "/api/score/3.14", None),
    ("POST", "/api/echo", {"hello": "world"}),
    ("POST", "/api/data", {"a": 1, "b": 2}),
]


async def fetch(session, method, url, payload, start_event):
    await start_event.wait()  # ⬅️ синхронный старт

    start = time.perf_counter()
    try:
        if method == "GET":
            async with session.get(url) as resp:
                await resp.text()
        else:
            async with session.post(url, json=payload) as resp:
                await resp.text()

        return url, time.perf_counter() - start, True
    except:
        return url, 0, False


async def run_benchmark():
    start_event = asyncio.Event()
    results = []

    tasks = []

    async with aiohttp.ClientSession() as session:
        # создаём ВСЕ задачи заранее
        for method, path, payload in ENDPOINTS:
            url = BASE_URL + path
            for _ in range(REQUESTS_PER_ENDPOINT):
                tasks.append(
                    asyncio.create_task(
                        fetch(session, method, url, payload, start_event)
                    )
                )

        total_requests = len(tasks)
        print(f"📦 Total requests: {total_requests}")
        print("⏳ Preparing tasks...")

        await asyncio.sleep(0.2)

        print("🚦 FIRE ALL REQUESTS 🚀")

        start_time = time.perf_counter()
        start_event.set()  # ⬅️ ВСЕ стартуют одновременно

        responses = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    # группируем результаты по эндпоинтам
    stats = defaultdict(list)
    success = defaultdict(int)
    fail = defaultdict(int)

    for url, latency, ok in responses:
        if ok:
            stats[url].append(latency)
            success[url] += 1
        else:
            fail[url] += 1

    print("\n=== GLOBAL ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"RPS: {total_requests / total_time:.2f}")

    # Формируем результаты для сохранения
    benchmark_results = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "requests_per_endpoint": REQUESTS_PER_ENDPOINT,
            "base_url": BASE_URL,
            "total_requests": total_requests,
        },
        "global": {
            "total_time": round(total_time, 4),
            "rps": round(total_requests / total_time, 2) if total_time > 0 else 0,
        },
        "endpoints": {},
    }

    print("\n=== PER ENDPOINT ===")
    for url in stats:
        latencies = stats[url]
        endpoint_data = {
            "success": success[url],
            "failed": fail[url],
            "latency_avg_ms": round(mean(latencies) * 1000, 2),
            "latency_min_ms": round(min(latencies) * 1000, 2),
            "latency_max_ms": round(max(latencies) * 1000, 2),
        }
        benchmark_results["endpoints"][url] = endpoint_data

        print(f"\n{url}")
        print(f"  Success: {success[url]} | Failed: {fail[url]}")
        print(f"  Avg: {mean(latencies)*1000:.2f} ms")
        print(f"  Min: {min(latencies)*1000:.2f} ms")
        print(f"  Max: {max(latencies)*1000:.2f} ms")

    # Сохраняем результаты в файл
    with open(RESULTS_FILE, "w") as f:
        json.dump(benchmark_results, f, indent=2)

    print(f"\n📊 Results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())