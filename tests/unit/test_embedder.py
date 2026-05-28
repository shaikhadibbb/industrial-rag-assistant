from unittest.mock import MagicMock, patch


def test_embedder_initialization():
    mock_model = MagicMock()
    # Patch at the source — embedder.py imports HuggingFaceEmbedding lazily
    # inside _load_huggingface(), so we patch the library's module directly.
    with patch(
        "llama_index.embeddings.huggingface.HuggingFaceEmbedding",
        return_value=mock_model,
    ) as mock_hf_class:
        from src.retrieval.embedder import BGEEmbedder

        embedder = BGEEmbedder()
        model = embedder.get_embedding_model()

        mock_hf_class.assert_called_once()
        assert model == mock_model
        assert embedder.model_name == "BAAI/bge-small-en-v1.5"
