from unittest.mock import MagicMock, patch


def test_embedder_initialization():
    mock_model = MagicMock()

    mock_hf_module = MagicMock()
    mock_hf_class = MagicMock()
    mock_hf_class.return_value = mock_model
    mock_hf_module.HuggingFaceEmbedding = mock_hf_class

    # Dynamic patching of sys.modules to handle missing packages in CI runner
    with patch.dict(
        "sys.modules", {"llama_index.embeddings.huggingface": mock_hf_module}
    ):
        import llama_index.embeddings

        with patch.object(
            llama_index.embeddings, "huggingface", mock_hf_module, create=True
        ):
            from src.retrieval.embedder import BGEEmbedder

            embedder = BGEEmbedder()
            model = embedder.get_embedding_model()

            mock_hf_class.assert_called_once()
            assert model == mock_model
            assert embedder.model_name == "BAAI/bge-small-en-v1.5"
