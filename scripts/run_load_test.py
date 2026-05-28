import asyncio
import time
import json
import argparse
import sys
import os
import random
from typing import List, Dict, Any
import httpx

# Ensure we can import modules from workspace
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DEFAULT_QUESTIONS = [
    "What should be done if the compressor's high-pressure warning transducer value approaches the limit?",
    "What is the consequence of internal corrosion in a compressed air receiver vessel?",
    "Where are soft start starters usually positioned and why?",
    "How often must internal condensing water be drained from an air receiver vessel?",
    "What is an open cooling system without circulating water and how is it supplied?",
    "What is the standard regulation method for compressors with a capacity greater than 5 kW?",
    "What troubleshooting value does a compressor's integrated memory storage provide?",
    "What is the hazard of running a corroded air vessel without a daily drain routine?"
]

def load_questions_from_dataset(dataset_path: str) -> List[str]:
    try:
        if os.path.exists(dataset_path):
            with open(dataset_path, "r") as f:
                data = json.load(f)
                questions = [item["question"] for item in data if "question" in item]
                if questions:
                    return questions
    except Exception as e:
        print(f"Warning: Could not load questions from {dataset_path} ({e}). Using defaults.")
    return DEFAULT_QUESTIONS

async def send_query(
    client: httpx.AsyncClient, 
    url: str, 
    question: str, 
    headers: Dict[str, str]
) -> Dict[str, Any]:
    payload = {"question": question, "session_id": f"load_test_{random.randint(1000, 9999)}"}
    start_time = time.time()
    try:
        response = await client.post(url, json=payload, headers=headers, timeout=60.0)
        duration = time.time() - start_time
        if response.status_code == 200:
            return {"success": True, "latency": duration, "status_code": 200}
        else:
            return {"success": False, "latency": duration, "status_code": response.status_code, "error": response.text}
    except Exception as e:
        duration = time.time() - start_time
        return {"success": False, "latency": duration, "status_code": 0, "error": str(e)}

async def worker(
    queue: asyncio.Queue, 
    client: httpx.AsyncClient, 
    url: str, 
    headers: Dict[str, str], 
    results: List[Dict[str, Any]]
):
    while True:
        try:
            question = await queue.get()
        except asyncio.QueueEmpty:
            break
            
        res = await send_query(client, url, question, headers)
        results.append(res)
        queue.task_done()

async def run_benchmark(
    url: str, 
    questions: List[str], 
    num_requests: int, 
    concurrency: int, 
    api_key: str
) -> Dict[str, Any]:
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    # Select random questions for the run
    selected_questions = [random.choice(questions) for _ in range(num_requests)]
    
    queue = asyncio.Queue()
    for q in selected_questions:
        await queue.put(q)
        
    results = []
    
    print(f"🚀 Starting load test on {url}...")
    print(f"📊 Concurrency: {concurrency} workers | Total Requests: {num_requests}")
    
    start_time = time.time()
    
    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        # Create worker tasks
        tasks = []
        for _ in range(concurrency):
            task = asyncio.create_task(worker(queue, client, url, headers, results))
            tasks.append(task)
            
        # Wait until the queue is fully processed
        await queue.join()
        
        # Cancel workers
        for task in tasks:
            task.cancel()
            
    total_duration = time.time() - start_time
    
    # Calculate stats
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    latencies = sorted([r["latency"] for r in successes])
    
    stats = {
        "total_duration_s": round(total_duration, 2),
        "total_requests": len(results),
        "success_count": len(successes),
        "failure_count": len(failures),
        "success_rate": round(len(successes) / len(results) * 100, 2) if results else 0,
        "throughput_req_sec": round(len(results) / total_duration, 2) if total_duration > 0 else 0,
    }
    
    if latencies:
        stats.update({
            "min_latency_s": round(latencies[0], 3),
            "max_latency_s": round(latencies[-1], 3),
            "p50_latency_s": round(latencies[int(len(latencies) * 0.50)], 3),
            "p90_latency_s": round(latencies[int(len(latencies) * 0.90)], 3) if len(latencies) >= 10 else round(latencies[-1], 3),
            "p95_latency_s": round(latencies[int(len(latencies) * 0.95)], 3) if len(latencies) >= 20 else round(latencies[-1], 3),
            "p99_latency_s": round(latencies[int(len(latencies) * 0.99)], 3) if len(latencies) >= 100 else round(latencies[-1], 3),
            "avg_latency_s": round(sum(latencies) / len(latencies), 3)
        })
    else:
        stats.update({
            "min_latency_s": 0,
            "max_latency_s": 0,
            "p50_latency_s": 0,
            "p90_latency_s": 0,
            "p95_latency_s": 0,
            "p99_latency_s": 0,
            "avg_latency_s": 0
        })
        
    return stats

def main():
    parser = argparse.ArgumentParser(description="Async RAG API Load Tester")
    parser.add_argument("--url", default="http://localhost:8000/query", help="FastAPI endpoint URL")
    parser.add_argument("--requests", type=int, default=30, help="Total requests to make")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent virtual users")
    parser.add_argument("--dataset", default="data/evaluation/dataset_v1.json", help="Path to evaluation dataset JSON")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", ""), help="API key for X-API-Key authentication")
    parser.add_argument("--save-report", action="store_true", help="Save output to docs/performance.md")
    
    args = parser.parse_args()
    
    questions = load_questions_from_dataset(args.dataset)
    
    stats = asyncio.run(run_benchmark(
        url=args.url,
        questions=questions,
        num_requests=args.requests,
        concurrency=args.concurrency,
        api_key=args.api_key
    ))
    
    print("\n" + "="*40)
    print("📊 LOAD TEST RESULTS:")
    print("="*40)
    for k, v in stats.items():
        print(f"{k:25}: {v}")
    print("="*40 + "\n")
    
    if args.save_report:
        report_dir = "docs"
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "performance.md")
        
        report_content = f"""# System Performance & Load Test Report

Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Benchmark Summary

| Metric | Value |
| :--- | :--- |
| **Total Requests** | {stats['total_requests']} |
| **Concurrency** | {args.concurrency} concurrent tasks |
| **Duration** | {stats['total_duration_s']} s |
| **Throughput** | {stats['throughput_req_sec']} req/sec |
| **Success Rate** | {stats['success_rate']}% ({stats['success_count']}/{stats['total_requests']}) |

## Latency Profiles (Successful Requests)

| Percentile | Latency |
| :--- | :--- |
| **Minimum** | {stats['min_latency_s']:.3f} s |
| **p50 (Median)** | {stats['p50_latency_s']:.3f} s |
| **p90** | {stats['p90_latency_s']:.3f} s |
| **p95 (Target <2s)** | {stats['p95_latency_s']:.3f} s |
| **p99** | {stats['p99_latency_s']:.3f} s |
| **Maximum** | {stats['max_latency_s']:.3f} s |
| **Average** | {stats['avg_latency_s']:.3f} s |

> [!NOTE]
> Standard production RAG systems require a p95 latency of <2.0 seconds. The cache hits significantly improve subsequent query times to <0.05 seconds.
"""
        with open(report_path, "w") as f:
            f.write(report_content)
        print(f"💾 Report saved successfully to {report_path}")

if __name__ == "__main__":
    main()
