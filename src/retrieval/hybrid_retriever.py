import logging
from typing import List
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from src.retrieval.keyword_retriever import KeywordRetriever

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Custom Hybrid Retriever implementing Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        vector_retriever: BaseRetriever,
        keyword_retriever: KeywordRetriever,
        similarity_top_k: int = 6,
        rrf_k: int = 60,
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.similarity_top_k = similarity_top_k
        self.rrf_k = rrf_k
        super().__init__()

    def _retrieve(
        self, query_bundle: QueryBundle, event_manager=None
    ) -> List[NodeWithScore]:
        """Performs RRF on top of dense vector and BM25 search scores."""
        query_str = query_bundle.query_str

        # 1. Retrieve candidates
        try:
            vector_nodes = self.vector_retriever.retrieve(query_bundle)
        except Exception as e:
            logger.error(f"Vector retrieval failed in hybrid retrieval: {e}")
            vector_nodes = []

        try:
            keyword_nodes = self.keyword_retriever.retrieve(query_str)
        except Exception as e:
            logger.error(f"BM25 retrieval failed in hybrid retrieval: {e}")
            keyword_nodes = []

        # 2. Apply Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        node_map = {}

        def add_ranks(nodes):
            for rank, node_with_score in enumerate(nodes):
                node = node_with_score.node
                node_id = node.node_id
                node_map[node_id] = node

                if node_id not in rrf_scores:
                    rrf_scores[node_id] = 0.0

                # RRF Formula: 1 / (rrf_k + rank) where rank is 1-indexed
                rrf_scores[node_id] += 1.0 / (self.rrf_k + (rank + 1))

        add_ranks(vector_nodes)
        add_ranks(keyword_nodes)

        # 3. Sort by fused score descending
        sorted_nodes = sorted(
            rrf_scores.items(), key=lambda item: item[1], reverse=True
        )

        # 4. Filter and return top K
        top_k_nodes = sorted_nodes[: self.similarity_top_k]

        fused_nodes = []
        for node_id, fused_score in top_k_nodes:
            fused_nodes.append(NodeWithScore(node=node_map[node_id], score=fused_score))

        logger.info(
            f"Hybrid retrieval finished: dense vector candidates={len(vector_nodes)}, "
            f"keyword candidates={len(keyword_nodes)} -> fused nodes={len(fused_nodes)}"
        )
        return fused_nodes
