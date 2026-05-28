#!/usr/bin/env python3
"""Run evaluation and generate a formatted benchmark markdown summary report."""

import os
import sys
import json
import logging
from datetime import datetime
from src.evaluation.evaluator import RAGEvaluator

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Target Thresholds
TARGETS = {
    "faithfulness": 0.70,
    "answer_relevancy": 0.75,
    "context_precision": 0.75,
    "context_recall": 0.70,
    "context_entity_recall": 0.65,
    "p95_latency": 2.0,  # 2.0 seconds
}


def generate_markdown_report(scores, latencies, results_path):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    avg_l = latencies.get("avg_s", 0)
    p95_l = latencies.get("p95_s", 0)

    report_lines = [
        f"# 📊 RAG Benchmarking Summary Report",
        f"",
        f"**Generated At:** `{timestamp}`",
        f"**Source Results:** `{results_path}`",
        f"",
        f"## 📈 Telemetry Metrics vs Production Targets",
        f"",
        f"| Metric | Score | Target | Status |",
        f"| :--- | :---: | :---: | :---: |",
    ]

    all_pass = True

    # 1. RAGAS Metrics
    for metric in [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "context_entity_recall",
    ]:
        score = scores.get(metric, 0.0)
        target = TARGETS[metric]
        status = "✅ PASS" if score >= target else "❌ FAIL"
        if score < target:
            all_pass = False
        report_lines.append(
            f"| {metric.replace('_', ' ').title()} | **{score:.4f}** | {target:.2f} | {status} |"
        )

    # 2. Latency
    status_p95 = "✅ PASS" if p95_l <= TARGETS["p95_latency"] else "❌ FAIL"
    if p95_l > TARGETS["p95_latency"]:
        all_pass = False

    report_lines.extend(
        [
            f"| p95 Latency (Seconds) | **{p95_l:.2f}s** | {TARGETS['p95_latency']:.2f}s | {status_p95} |",
            f"| Average Latency (Seconds) | {avg_l:.2f}s | - | - |",
            f"",
            f"## 🏁 Overall Status",
            f"",
            f"**Evaluation Result:** "
            + (
                "**ALL PASS 🎉 (Production Ready)**"
                if all_pass
                else "**NEEDS IMPROVEMENT ⚠️ (Below Target)**"
            ),
            f"",
            f"---",
            f"",
            f"### 💡 Next Steps / Guidelines",
            f"1. Audit the lowest performing metric (typically faithfulness or context recall).",
            f"2. Optimize search settings (top_k, hybrid weight, rerank limits) inside `configs/config.yaml`.",
            f"3. Run another benchmark using `python scripts/run_benchmark.py` to log comparative MLflow runs.",
        ]
    )

    report_content = "\n".join(report_lines)
    os.makedirs("data/evaluation", exist_ok=True)
    report_path = (
        f"data/evaluation/benchmark_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    with open(report_path, "w") as f:
        f.write(report_content)

    return report_content, report_path


def main():
    logger.info("🎬 Initializing system-wide RAG benchmark evaluation...")
    try:
        evaluator = RAGEvaluator()
        # For evaluation speed in manual trigger, we can restrict to top 15 queries
        # but run all if specified
        scores, results_path = evaluator.evaluate_pipeline(max_questions=15)

        # Read the generated results to extract latencies
        with open(results_path, "r") as f:
            results_data = json.load(f)

        latencies = results_data["latencies"]

        # Generate the report
        report_content, report_path = generate_markdown_report(
            scores, latencies, results_path
        )

        print("\n" + report_content)
        print(f"\n📁 Benchmark Report saved to: {report_path}\n")

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
