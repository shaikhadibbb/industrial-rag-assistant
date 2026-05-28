import time
import logging
import yaml
import threading
import hashlib
from functools import lru_cache
from typing import List
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine, RetrieverQueryEngine
from llama_index.core.schema import NodeWithScore
from src.retrieval.vector_store import QdrantStore
from src.retrieval.embedder import BGEEmbedder
from src.generation.llm_client import OllamaLLM

logger = logging.getLogger(__name__)

# Module-level singleton and lock
_query_engine_lock = threading.Lock()
_query_engine_instance = None


class DeduplicationPostprocessor:
    """Remove duplicate chunks based on SHA-256 chunk content hash and full-text Jaccard similarity."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle=None
    ) -> List[NodeWithScore]:
        if not nodes:
            return nodes

        seen_hashes = set()
        seen_texts = []
        unique_nodes = []

        for node in nodes:
            # Normalize full chunk text
            full_text = node.node.text.strip()
            normalized_text = " ".join(full_text.lower().split())

            # 1. Deduplicate by SHA-256 content hash (exact text duplicates)
            content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                logger.info("Skipping exact duplicate node via SHA-256 hash.")
                continue

            # 2. Deduplicate by semantic/Jaccard similarity threshold over full text
            is_duplicate = False
            for seen_text in seen_texts:
                if (
                    self._text_similarity(normalized_text, seen_text)
                    > self.similarity_threshold
                ):
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_hashes.add(content_hash)
                seen_texts.append(normalized_text)
                unique_nodes.append(node)

        return unique_nodes

    def _text_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)


class LRUTTLCache:
    """Thread-safe LRU Cache with Time-To-Live (TTL) expiration."""

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl = ttl_seconds
        self.cache = {}
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                val, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return val
                else:
                    del self.cache[key]
            return None

    def set(self, key, val):
        with self.lock:
            if len(self.cache) >= self.maxsize:
                # Discard oldest cache entry
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
            self.cache[key] = (val, time.time())


class RAGQueryEngine:
    """Full RAG Query Engine with HyDE and Reranking."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        start_time = time.time()
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.embed_model = BGEEmbedder(config_path).get_embedding_model()
        self.llm = OllamaLLM(config_path).get_llm()

        # Monkey patch for performance using object.__setattr__ to bypass Pydantic validation
        original_get_query_embedding = self.embed_model.get_query_embedding

        @lru_cache(maxsize=100)
        def cached_query_embedding(query: str):
            return original_get_query_embedding(query)

        object.__setattr__(
            self.embed_model, "get_query_embedding", cached_query_embedding
        )

        Settings.llm = self.llm
        Settings.embed_model = self.embed_model

        self.qdrant_store = QdrantStore(config_path)
        self.vector_store = self.qdrant_store.get_vector_store()
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)

        self.hyde = HyDEQueryTransform(llm=self.llm, include_original=True)
        self.deduplicator = DeduplicationPostprocessor(similarity_threshold=0.85)
        from src.retrieval.cross_encoder_reranker import CrossEncoderReranker

        self.reranker = CrossEncoderReranker(
            model_name=self.config["retrieval"]["reranker_model"],
            top_n=self.config["retrieval"]["reranker_top_n"],
        )

        # Build base engine retriever
        vector_retriever = self.index.as_retriever(
            similarity_top_k=self.config["retrieval"]["similarity_top_k"]
        )

        if self.config["retrieval"].get("use_hybrid", False):
            from src.retrieval.keyword_retriever import KeywordRetriever
            from src.retrieval.hybrid_retriever import HybridRetriever

            logger.info("Initializing Hybrid RRF Retrieval mode...")
            self.keyword_retriever = KeywordRetriever(config_path)
            self.retriever = HybridRetriever(
                vector_retriever=vector_retriever,
                keyword_retriever=self.keyword_retriever,
                similarity_top_k=self.config["retrieval"]["similarity_top_k"],
            )
        else:
            logger.info("Initializing Vector-only Retrieval mode...")
            self.retriever = vector_retriever

        # Build base engine with selected retriever and postprocessors
        base_engine = RetrieverQueryEngine.from_args(
            retriever=self.retriever,
            llm=self.llm,
            node_postprocessors=[self.deduplicator, self.reranker],
        )

        # Wrap with HyDE
        self.engine = TransformQueryEngine(base_engine, query_transform=self.hyde)
        self.query_cache = LRUTTLCache(maxsize=1000, ttl_seconds=3600)

        init_time = time.time() - start_time
        logger.info(f"Query engine initialized in {init_time:.2f}s")

    def query(self, message: str):
        """Executes a query with caching and timing profiles."""
        cached = self.query_cache.get(message)
        if cached is not None:
            logger.info(f"🚀 Cache HIT for query: '{message}'")
            return cached

        logger.info(f"🔍 Cache MISS for query: '{message}'. Profiling spans...")
        t0 = time.time()
        res = self.engine.query(message)
        duration = time.time() - t0
        logger.info(f"⏱️ Timing Span: query_engine_total_s={duration:.2f}s")

        self.query_cache.set(message, res)
        return res

    async def aquery(self, message: str):
        """Executes an async query with caching and timing profiles."""
        cached = self.query_cache.get(message)
        if cached is not None:
            logger.info(f"🚀 Cache HIT for async query: '{message}'")
            return cached

        logger.info(f"🔍 Cache MISS for async query: '{message}'. Profiling spans...")
        t0 = time.time()
        res = await self.engine.aquery(message)
        duration = time.time() - t0
        logger.info(f"⏱️ Timing Span: query_engine_total_s={duration:.2f}s")

        self.query_cache.set(message, res)
        return res


def get_query_engine():
    global _query_engine_instance
    if _query_engine_instance is None:
        with _query_engine_lock:
            if _query_engine_instance is None:
                _query_engine_instance = RAGQueryEngine()
    return _query_engine_instance
