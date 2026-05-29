from unittest.mock import MagicMock, patch
from src.generation.llm_client import OllamaLLM


def test_llm_client_initialization():
    mock_ollama_instance = MagicMock()
    with patch(
        "src.generation.llm_client.Ollama", return_value=mock_ollama_instance
    ) as mock_ollama_class:
        llm_client = OllamaLLM()
        llm = llm_client.get_llm()

        mock_ollama_class.assert_called_once()
        assert llm == mock_ollama_instance
        assert llm_client.model == "mistral:7b-instruct"


def test_llm_client_complete():
    mock_ollama_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.__str__.return_value = "Mocked answer"
    mock_ollama_instance.complete.return_value = mock_response

    with patch("src.generation.llm_client.Ollama", return_value=mock_ollama_instance):
        llm_client = OllamaLLM()
        llm_client.llm = mock_ollama_instance

        res = llm_client.complete("Test prompt")
        assert str(res) == "Mocked answer"
        mock_ollama_instance.complete.assert_called_once_with("Test prompt")


def test_llm_client_complete_consistency():
    mock_ollama_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.__str__.return_value = "Mocked answer text content here"
    mock_ollama_instance.complete.return_value = mock_response

    mock_embed_instance = MagicMock()
    mock_embed_instance.get_embedding_model.return_value.get_text_embedding.return_value = [
        0.1,
        0.2,
        0.3,
    ]

    with patch("src.generation.llm_client.Ollama", return_value=mock_ollama_instance), patch(
        "src.retrieval.embedder.BGEEmbedder", return_value=mock_embed_instance
    ):
        llm_client = OllamaLLM()
        llm_client.llm = mock_ollama_instance

        res = llm_client.complete("Test prompt", check_consistency=True)
        assert str(res) == "Mocked answer text content here"
        assert mock_ollama_instance.complete.call_count == 3
