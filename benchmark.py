import asyncio
import aiohttp
import time
import json
from datetime import datetime
from statistics import mean

BASE_URL = "http://localhost:8000"

TOTAL_REQUESTS = 1000
CONCURRENCY = 100
RESULTS_FILE = "benchmark_results.json"


async def fetch(session, url, method="GET", json=None):
    start = time.perf_counter()
    try:
        if method == "GET":
            async with session.get(url) as response:
                await response.text()
        elif method == "POST":
            async with session.post(url, json=json) as response:
                await response.text()

        latency = time.perf_counter() - start
        return latency, True
    except Exception as e:
        return 0, False


async def worker(name, session, queue, results):
    while True:
        item = await queue.get()
        if item is None:
            break

        url, method, payload = item
        latency, success = await fetch(session, url, method, payload)

        results.append((latency, success))
        queue.task_done()


async def run_benchmark(endpoint, method="GET", payload=None):
    queue = asyncio.Queue()
    results = []

    # Заполняем очередь
    for _ in range(TOTAL_REQUESTS):
        await queue.put((endpoint, method, payload))

    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(CONCURRENCY):
            task = asyncio.create_task(worker(i, session, queue, results))
            tasks.append(task)

        start_time = time.perf_counter()

        await queue.join()

        total_time = time.perf_counter() - start_time

        # Останавливаем воркеры
        for _ in tasks:
            await queue.put(None)

        await asyncio.gather(*tasks)

    # Аналитика
    latencies = [r[0] for r in results if r[1]]
    success_count = sum(1 for r in results if r[1])
    fail_count = TOTAL_REQUESTS - success_count

    result_data = {
        "endpoint": endpoint,
        "method": method,
        "total_requests": TOTAL_REQUESTS,
        "concurrency": CONCURRENCY,
        "success": success_count,
        "failed": fail_count,
        "total_time": round(total_time, 4),
        "rps": round(TOTAL_REQUESTS / total_time, 2) if total_time > 0 else 0,
    }

    if latencies:
        result_data["latency_avg_ms"] = round(mean(latencies) * 1000, 2)
        result_data["latency_min_ms"] = round(min(latencies) * 1000, 2)
        result_data["latency_max_ms"] = round(max(latencies) * 1000, 2)

    print(f"\n=== Benchmark: {endpoint} ===")
    print(f"Total requests: {TOTAL_REQUESTS}")
    print(f"Concurrency: {CONCURRENCY}")
    print(f"Success: {success_count}, Failed: {fail_count}")
    print(f"Total time: {total_time:.2f}s")
    print(f"RPS: {TOTAL_REQUESTS / total_time:.2f}")

    if latencies:
        print(f"Avg latency: {mean(latencies) * 1000:.2f} ms")
        print(f"Min latency: {min(latencies) * 1000:.2f} ms")
        print(f"Max latency: {max(latencies) * 1000:.2f} ms")

    return result_data


async def main():
    all_results = []

    all_results.append(await run_benchmark(f"{BASE_URL}/api/ping"))
    all_results.append(await run_benchmark(f"{BASE_URL}/api/random/async"))
    all_results.append(await run_benchmark(f"{BASE_URL}/api/sum/10/20"))

    # POST тест
    all_results.append(await run_benchmark(
        f"{BASE_URL}/api/echo",
        method="POST",
        payload={"test": "data"}
    ))

    # Сохраняем результаты в файл
    output = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "total_requests": TOTAL_REQUESTS,
            "concurrency": CONCURRENCY,
            "base_url": BASE_URL,
        },
        "results": all_results,
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n📊 Results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())