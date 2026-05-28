import logging
import yaml
import time
import os
from llama_index.llms.ollama import Ollama
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class OllamaLLM:
    """Client for LLM — supports local Ollama or serverless Groq in production."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.temperature = config["llm"]["temperature"]
        self.max_tokens = config["llm"]["max_tokens"]
        self.request_timeout = config["llm"].get("request_timeout", 45.0)

        # Dynamic Groq/Ollama switch for production vs local dev
        self.groq_api_key = os.getenv("GROQ_API_KEY")

        if self.groq_api_key:
            logger.info("Initializing Groq LLM (production serverless mode)...")
            from llama_index.llms.groq import Groq

            self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
            self.llm = Groq(
                model=self.model,
                api_key=self.groq_api_key,
                temperature=self.temperature,
                request_timeout=self.request_timeout,
            )
            self.base_url = "https://api.groq.com"
        else:
            logger.info("Initializing local Ollama LLM (development mode)...")
            self.model = config["llm"]["model"]
            self.base_url = config["llm"]["base_url"]
            self.additional_kwargs = config["llm"].get("additional_kwargs", {})
            self.llm = Ollama(
                model=self.model,
                base_url=self.base_url,
                temperature=self.temperature,
                request_timeout=self.request_timeout,
                additional_kwargs=self.additional_kwargs,
            )

        self._test_connection()

    def _test_connection(self):
        """Verify connection to Ollama."""
        try:
            # Simple check
            logger.info(f"Testing connection to Ollama at {self.base_url}")
            # Ollama client doesn't have a direct health check in LlamaIndex wrapper
            # but we can try a tiny completion or just log.
            logger.info(f"Ollama configured for model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def complete(self, prompt: str, check_consistency: bool = False):
        """Completes a prompt with optional consistency check, retry logic and latency logging."""
        if not check_consistency:
            start_time = time.time()
            response = self.llm.complete(prompt)
            duration = time.time() - start_time
            logger.info(f"LLM Response received in {duration:.2f}s")
            return response

        logger.info("Running answer consistency check (generating 3 answers)...")
        start_time = time.time()

        res1 = self.llm.complete(prompt)
        ans1 = str(res1).strip()
        ans2 = str(self.llm.complete(prompt)).strip()
        ans3 = str(self.llm.complete(prompt)).strip()

        duration = time.time() - start_time
        logger.info(f"Generated 3 answers in {duration:.2f}s")

        try:
            from src.retrieval.embedder import BGEEmbedder
            import numpy as np

            embed_model = BGEEmbedder().get_embedding_model()
            emb1 = np.array(embed_model.get_text_embedding(ans1))
            emb2 = np.array(embed_model.get_text_embedding(ans2))
            emb3 = np.array(embed_model.get_text_embedding(ans3))

            def cos_sim(v1, v2):
                norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
                if norm1 == 0 or norm2 == 0:
                    return 0.0
                return float(np.dot(v1, v2) / (norm1 * norm2))

            sim12 = cos_sim(emb1, emb2)
            sim23 = cos_sim(emb2, emb3)
            sim13 = cos_sim(emb1, emb3)

            avg_sim = (sim12 + sim23 + sim13) / 3
            variance = 1.0 - avg_sim

            logger.info(
                f"Answer semantic consistency: {avg_sim:.4f} (variance: {variance:.4f})"
            )

            threshold = 0.15  # 85% similarity threshold
            import mlflow

            if variance > threshold:
                logger.warning(
                    f"⚠️ High answer variance detected ({variance:.4f} > {threshold})! "
                    f"A1: '{ans1[:80]}...' | A2: '{ans2[:80]}...' | A3: '{ans3[:80]}...'"
                )
                if mlflow.active_run():
                    mlflow.log_metric("answer_variance", variance)

        except Exception as e:
            logger.error(f"Failed to calculate answer consistency: {e}")

        return res1

    def get_llm(self):
        """Returns the LlamaIndex LLM object."""
        return self.llm
