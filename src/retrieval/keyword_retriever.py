import logging
import yaml
import json
from typing import List
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.retrievers.bm25 import BM25Retriever
from src.retrieval.vector_store import QdrantStore

logger = logging.getLogger(__name__)


class KeywordRetriever:
    """Keyword-based retriever using BM25, pulling document chunks dynamically from Qdrant."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.qdrant_store = QdrantStore(config_path)
        self.client = self.qdrant_store.client
        self.collection_name = self.qdrant_store.collection_name
        self.top_k = self.config["retrieval"].get("similarity_top_k", 6)

        self.retriever = None
        self._initialize_bm25()

    def _initialize_bm25(self):
        """Scrolls through Qdrant collections to reconstruct TextNodes and fit rank-bm25."""
        try:
            logger.info("Initializing BM25 index from Qdrant vector database...")
            # Retrieve all indexed nodes in the Qdrant collection
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False,
            )
            points = results[0]

            nodes = []
            for p in points:
                payload = p.payload
                if payload:
                    node_content_str = payload.get("_node_content")
                    text = ""
                    metadata = {}

                    if node_content_str:
                        try:
                            node_content = json.loads(node_content_str)
                            text = node_content.get("text", "")
                            metadata = node_content.get("metadata", {})
                        except Exception:
                            text = payload.get("text", "")
                            metadata = payload.get("metadata", {})
                    else:
                        text = payload.get("text", "")
                        metadata = payload.get("metadata", {})

                    if text:
                        node = TextNode(text=text, id_=p.id, metadata=metadata)
                        nodes.append(node)

            if nodes:
                logger.info(f"Found {len(nodes)} nodes. Constructing BM25 index...")
                self.retriever = BM25Retriever.from_defaults(
                    nodes=nodes, similarity_top_k=self.top_k
                )
                logger.info("BM25 Keyword Retriever successfully built.")
            else:
                logger.warning(
                    "Qdrant collection is currently empty. BM25 is uninitialized."
                )
        except Exception as e:
            logger.error(f"Failed to initialize BM25 index: {e}")

    def retrieve(self, query: str) -> List[NodeWithScore]:
        """Performs BM25 keyword query lookup."""
        if self.retriever is None:
            logger.warning(
                "BM25 retriever is uninitialized (no documents found). Returning empty."
            )
            return []
        try:
            return self.retriever.retrieve(query)
        except Exception as e:
            logger.error(f"BM25 keyword search retrieval failed: {e}")
            return []
