import asyncio
import aiohttp
import time
import random
import statistics

BASE_URL = "http://127.0.0.1:8000"

# Все HTTP маршруты
ROUTES = [
    ("GET", "/"),
    ("GET", "/api/hello"),
    ("POST", "/api/echo"),
    ("GET", "/api/users/{id}"),
    ("GET", "/api/items/{name}"),
    ("GET", "/api/score/{value}"),
    ("GET", "/api/sync"),
    ("GET", "/chat"),
]

# Генерация параметров
def build_path(path: str) -> str:
    if "{id}" in path:
        return path.replace("{id}", str(random.randint(1, 100000)))
    if "{name}" in path:
        return path.replace("{name}", random.choice(["apple", "banana", "car"]))
    if "{value}" in path:
        return path.replace("{value}", str(random.random() * 100))
    return path


async def worker(session, duration, stats):
    end_time = time.time() + duration

    while time.time() < end_time:
        method, path = random.choice(ROUTES)
        url = BASE_URL + build_path(path)

        start = time.perf_counter()

        try:
            if method == "GET":
                async with session.get(url) as resp:
                    await resp.read()
                    status = resp.status
            else:
                async with session.post(url, json={"test": "data"}) as resp:
                    await resp.read()
                    status = resp.status

            latency = time.perf_counter() - start

            stats["requests"] += 1
            stats["latencies"].append(latency)

            if status >= 400:
                stats["errors"] += 1

        except Exception:
            stats["errors"] += 1


async def run_benchmark(concurrency=100, duration=10):
    stats = {
        "requests": 0,
        "errors": 0,
        "latencies": [],
    }

    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            worker(session, duration, stats)
            for _ in range(concurrency)
        ]

        start = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start

    # Метрики
    total_requests = stats["requests"]
    rps = total_requests / total_time

    latencies = stats["latencies"]

    if latencies:
        p50 = statistics.quantiles(latencies, n=100)[49]
        p90 = statistics.quantiles(latencies, n=100)[89]
        p99 = statistics.quantiles(latencies, n=100)[98]
        avg = sum(latencies) / len(latencies)
    else:
        p50 = p90 = p99 = avg = 0

    print("\n=== BENCHMARK RESULTS ===")
    print(f"Duration:        {total_time:.2f}s")
    print(f"Concurrency:     {concurrency}")
    print(f"Total Requests:  {total_requests}")
    print(f"RPS:             {rps:.2f}")
    print(f"Errors:          {stats['errors']}")
    print(f"Avg Latency:     {avg*1000:.2f} ms")
    print(f"P50 Latency:     {p50*1000:.2f} ms")
    print(f"P90 Latency:     {p90*1000:.2f} ms")
    print(f"P99 Latency:     {p99*1000:.2f} ms")


if __name__ == "__main__":
    asyncio.run(run_benchmark(concurrency=200, duration=15))