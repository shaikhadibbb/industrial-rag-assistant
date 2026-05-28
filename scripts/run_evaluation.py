#!/usr/bin/env python3
"""Run evaluation pipeline against dataset."""

import argparse
import sys
import logging
from src.evaluation.evaluator import RAGEvaluator

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Run RAGAS Evaluation Pipeline"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/evaluation/dataset_v1.json",
        help="Path to evaluation dataset",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help="Limit number of questions to evaluate",
    )
    args = parser.parse_args()

    logger.info("🔬 Starting RAGAS Evaluation Pipeline...")
    try:
        evaluator = RAGEvaluator()
        scores, results_path = evaluator.evaluate_pipeline(
            dataset_path=args.dataset, max_questions=args.max_questions
        )
        print("\n" + "=" * 50)
        print("   RAGAS EVALUATION METRICS SUMMARY")
        print("=" * 50)
        for metric, val in scores.items():
            print(f"   {metric:<25}: {val:.4f}")
        print("=" * 50)
        print(f"Results File: {results_path}\n")
    except Exception as e:
        logger.error(f"Evaluation pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
