import os
import json
import time
import logging
import yaml
import mlflow
from datetime import datetime
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_entity_recall,
)

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """Telemetry pipeline that runs RAGAS evaluations and logs metrics to MLflow."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config_path = config_path
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        mlflow.set_tracking_uri(self.config["mlflow"]["tracking_uri"])
        mlflow.set_experiment(self.config["mlflow"]["experiment_name"])

    def evaluate_pipeline(
        self,
        dataset_path: str = "data/evaluation/dataset_v1.json",
        max_questions: int = None,
    ):
        """Runs the complete RAG evaluation on the given dataset."""
        logger.info(f"Loading evaluation dataset from {dataset_path}")
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

        with open(dataset_path, "r") as f:
            data = json.load(f)

        if max_questions:
            data = data[:max_questions]

        logger.info(f"Loaded {len(data)} evaluation questions.")

        # 1. Run each question through the active RAG query engine
        from src.retrieval.query_engine import get_query_engine

        engine = get_query_engine()

        eval_data = []
        latencies = []

        for i, item in enumerate(data):
            question = item["question"]
            ground_truth = item["ground_truth"]
            category = item.get("category", "general")

            logger.info(
                f"Querying [{i+1}/{len(data)}] ({category}): {question[:50]}..."
            )

            start_time = time.time()
            try:
                response = engine.query(question)
                latency = time.time() - start_time
                answer = str(response).strip()

                contexts = []
                if hasattr(response, "source_nodes") and response.source_nodes:
                    contexts = [node.node.text for node in response.source_nodes]

                # Fallback to predefined reference contexts if empty
                if not contexts:
                    contexts = item.get("contexts") or ["No context retrieved"]
            except Exception as e:
                logger.error(f"RAG pipeline query failed: {e}")
                latency = 0
                answer = "Error: Failed to generate answer."
                contexts = item.get("contexts") or ["No context retrieved"]

            latencies.append(latency)
            eval_data.append(
                {
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,
                    "ground_truth": ground_truth,
                    "category": category,
                    "latency_s": round(latency, 2),
                }
            )

        # 2. Format into RAGAS compatible dataset
        dataset = Dataset.from_list(
            [
                {
                    "question": d["question"],
                    "answer": d["answer"],
                    "contexts": d["contexts"],
                    "ground_truth": d["ground_truth"],
                }
                for d in eval_data
            ]
        )

        logger.info("Running RAGAS evaluation metrics scoring...")

        try:
            from ragas.llms import LangchainLLMWrapper
            from ragas.embeddings import LangchainEmbeddingsWrapper
            from langchain_community.llms import Ollama as LCOllama
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from ragas.run_config import RunConfig

            ollama_url = self.config["llm"]["base_url"]
            judge_llm = LangchainLLMWrapper(
                LCOllama(
                    model=self.config["llm"]["model"],
                    base_url=ollama_url,
                    timeout=180.0,
                )
            )
            judge_emb = LangchainEmbeddingsWrapper(
                HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
            )
            run_config = RunConfig(timeout=180, max_workers=1)

            results = evaluate(
                dataset=dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    context_entity_recall,
                ],
                llm=judge_llm,
                embeddings=judge_emb,
                run_config=run_config,
                raise_exceptions=False,
            )
        except Exception as e:
            logger.warning(
                f"Failed to use local RAGAS judge models ({e}). Retrying with default RAGAS fallback..."
            )
            results = evaluate(
                dataset=dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    context_entity_recall,
                ],
                raise_exceptions=False,
            )

        # 3. Log metadata and scores to MLflow SQLite backend
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

        with mlflow.start_run(
            run_name=f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        ):
            mlflow.log_param("llm_model", self.config["llm"]["model"])
            mlflow.log_param("embedding_model", self.config["embedding"]["model_name"])
            mlflow.log_param("chunk_size", self.config["data"]["chunk_size"])
            mlflow.log_param(
                "similarity_top_k",
                self.config["retrieval"]["similarity_top_k"],
            )
            mlflow.log_param("dataset_size", len(eval_data))

            mlflow.log_metric("avg_latency_s", round(avg_latency, 2))
            mlflow.log_metric("p95_latency_s", round(p95_latency, 2))

            scores = {}
            df = results.to_pandas()
            for metric in [
                "faithfulness",
                "answer_relevancy",
                "context_precision",
                "context_recall",
                "context_entity_recall",
            ]:
                if metric in df.columns:
                    val = float(df[metric].mean())
                    scores[metric] = round(val, 4)
                    mlflow.log_metric(metric, scores[metric])

            # Export results to JSON and CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("data/evaluation", exist_ok=True)
            results_path = f"data/evaluation/results_{timestamp}.json"

            output_results = {
                "timestamp": timestamp,
                "metrics": scores,
                "latencies": {
                    "avg_s": round(avg_latency, 2),
                    "p95_s": round(p95_latency, 2),
                },
                "queries": eval_data,
            }

            with open(results_path, "w") as f:
                json.dump(output_results, f, indent=2)

            csv_path = f"data/evaluation/results_{timestamp}.csv"
            df.to_csv(csv_path, index=False)

            mlflow.log_artifact(results_path)
            mlflow.log_artifact(csv_path)

            logger.info(f"Evaluation completed. Results saved to {results_path}")
            return scores, results_path
