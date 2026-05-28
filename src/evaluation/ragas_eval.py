import json
import logging
import mlflow
import yaml
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from datasets import Dataset
from src.retrieval.query_engine import RAGQueryEngine

logger = logging.getLogger(__name__)


class RagasEvaluator:
    """Evaluates RAG performance using RAGAS metrics."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.query_engine = RAGQueryEngine(config_path)

    def run_evaluation(self, test_set_path: str = "data/test_set.json"):
        """Runs evaluation on a test set."""
        with open(test_set_path, "r") as f:
            test_data = json.load(f)

        mlflow.set_experiment(self.config["mlflow"]["experiment_name"])

        with mlflow.start_run(run_name="ragas-eval"):
            questions = [item["question"] for item in test_data]
            ground_truths = [item["ground_truth"] for item in test_data]

            answers = []
            contexts = []

            for q in questions:
                logger.info(f"Querying: {q}")
                res = self.query_engine.query(q)
                answers.append(res["answer"])
                contexts.append([s["text"] for s in res["sources"]])

            dataset_dict = {
                "question": questions,
                "answer": answers,
                "contexts": contexts,
                "ground_truth": ground_truths,
            }

            dataset = Dataset.from_dict(dataset_dict)

            logger.info("Running RAGAS evaluate...")
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_recall,
                    context_precision,
                ],
            )

            # Log metrics to MLflow
            for metric_name, value in result.items():
                mlflow.log_metric(metric_name, value)

            # Save results
            results_df = result.to_pandas()
            results_df.to_json("evaluation_results.json", orient="records", indent=4)

            print("\n--- Evaluation Results ---")
            print(
                results_df[
                    [
                        "question",
                        "faithfulness",
                        "answer_relevancy",
                        "context_recall",
                        "context_precision",
                    ]
                ]
            )

            return result


if __name__ == "__main__":
    evaluator = RagasEvaluator()
    evaluator.run_evaluation()
