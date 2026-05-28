from unittest.mock import MagicMock
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle
from src.retrieval.hybrid_retriever import HybridRetriever


def test_hybrid_retriever_rrf():
    mock_vector = MagicMock()
    mock_keyword = MagicMock()

    node1 = TextNode(text="Node A", id_="node_a")
    node2 = TextNode(text="Node B", id_="node_b")

    mock_vector.retrieve.return_value = [
        NodeWithScore(node=node1, score=0.9),
        NodeWithScore(node=node2, score=0.8),
    ]
    mock_keyword.retrieve.return_value = [
        NodeWithScore(node=node2, score=0.9),
        NodeWithScore(node=node1, score=0.8),
    ]

    hybrid = HybridRetriever(
        vector_retriever=mock_vector,
        keyword_retriever=mock_keyword,
        similarity_top_k=2,
        rrf_k=60,
    )

    results = hybrid.retrieve(QueryBundle(query_str="test"))

    assert len(results) == 2
    assert {r.node.node_id for r in results} == {"node_a", "node_b"}
