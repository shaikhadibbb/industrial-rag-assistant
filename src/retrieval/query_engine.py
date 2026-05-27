import time
import logging
import yaml
from functools import lru_cache
from typing import List, Optional
import numpy as np
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.query_engine import TransformQueryEngine, RetrieverQueryEngine
from llama_index.core.postprocessor import SentenceTransformerRerank, SimilarityPostprocessor
from llama_index.core.schema import NodeWithScore
from llama_index.core.memory import ChatMemoryBuffer
from src.retrieval.vector_store import QdrantStore
from src.retrieval.embedder import BGEEmbedder
from src.generation.llm_client import OllamaLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level singleton
_query_engine_instance = None

class DeduplicationPostprocessor:
    """Remove duplicate chunks based on text similarity and page number."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def postprocess_nodes(
        self, 
        nodes: List[NodeWithScore], 
        query_bundle=None
    ) -> List[NodeWithScore]:
        if not nodes:
            return nodes
        
        seen_pages = set()
        seen_texts = []
        unique_nodes = []
        
        for node in nodes:
            page = node.node.metadata.get("page_label", 
                   node.node.metadata.get("page_number", "unknown"))
            text = node.node.text[:100]
            
            if page in seen_pages:
                continue
            
            is_duplicate = False
            for seen_text in seen_texts:
                if self._text_similarity(text, seen_text) > self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_pages.add(page)
                seen_texts.append(text)
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

class RAGQueryEngine:
    """Full RAG Query Engine with HyDE and Reranking."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        start_time = time.time()
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.embed_model = BGEEmbedder(config_path).get_embedding_model()
        self.llm = OllamaLLM(config_path).get_llm()
        
        # Monkey patch for performance using object.__setattr__ to bypass Pydantic validation
        original_get_query_embedding = self.embed_model.get_query_embedding
        @lru_cache(maxsize=100)
        def cached_query_embedding(query: str):
            return original_get_query_embedding(query)
        
        object.__setattr__(self.embed_model, 'get_query_embedding', cached_query_embedding)
        
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        
        self.qdrant_store = QdrantStore(config_path)
        self.vector_store = self.qdrant_store.get_vector_store()
        self.index = VectorStoreIndex.from_vector_store(self.vector_store)
        
        self.hyde = HyDEQueryTransform(llm=self.llm, include_original=True)
        self.deduplicator = DeduplicationPostprocessor(similarity_threshold=0.85)
        self.reranker = SentenceTransformerRerank(
            model=self.config['retrieval']['reranker_model'],
            top_n=self.config['retrieval']['reranker_top_n']
        )
        
        # Build base engine
        base_engine = self.index.as_query_engine(
            llm=self.llm,
            similarity_top_k=self.config['retrieval']['similarity_top_k'],
            node_postprocessors=[self.deduplicator, self.reranker]
        )
        
        # Wrap with HyDE
        self.engine = TransformQueryEngine(base_engine, query_transform=self.hyde)
        
        init_time = time.time() - start_time
        logger.info(f"Query engine initialized in {init_time:.2f}s")

    def query(self, message: str):
        """Executes a query and returns the response object."""
        return self.engine.query(message)

def get_query_engine():
    global _query_engine_instance
    if _query_engine_instance is None:
        _query_engine_instance = RAGQueryEngine()
    return _query_engine_instance
