from unittest.mock import MagicMock, patch

with patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as mock_hf:
    # Import after patch to prevent early load
    from src.retrieval.embedder import BGEEmbedder


def test_embedder_initialization():
    mock_model = MagicMock()
    with patch(
        "src.retrieval.embedder.HuggingFaceEmbedding", return_value=mock_model
    ) as mock_hf_class:
        embedder = BGEEmbedder()
        model = embedder.get_embedding_model()

        mock_hf_class.assert_called_once()
        assert model == mock_model
        assert embedder.model_name == "BAAI/bge-small-en-v1.5"
