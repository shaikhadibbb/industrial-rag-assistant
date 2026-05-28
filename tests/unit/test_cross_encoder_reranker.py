import pytest
from unittest.mock import MagicMock, patch
from src.retrieval.cross_encoder_reranker import CrossEncoderReranker


def test_cross_encoder_reranker_predict():
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.1, 0.9]

    # Patch the local reference inside the module directly
    with patch(
        "src.retrieval.cross_encoder_reranker.CrossEncoder",
        return_value=mock_model,
    ):
        reranker = CrossEncoderReranker(model_name="dummy_model", top_n=1)

        from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle

        node1 = NodeWithScore(
            node=TextNode(text="Node A", id_="node_a"), score=0.5
        )
        node2 = NodeWithScore(
            node=TextNode(text="Node B", id_="node_b"), score=0.5
        )

        results = reranker.postprocess_nodes(
            [node1, node2], QueryBundle(query_str="test")
        )

        mock_model.predict.assert_called_once_with(
            [["test", "Node A"], ["test", "Node B"]]
        )

        assert len(results) == 1
        assert results[0].node.node_id == "node_b"
        assert results[0].score == 0.9
