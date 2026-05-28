import pytest
from unittest.mock import MagicMock, patch
from src.generation.llm_client import OllamaLLM

def test_llm_client_initialization():
    mock_ollama_instance = MagicMock()
    with patch("src.generation.llm_client.Ollama", return_value=mock_ollama_instance) as mock_ollama_class:
        llm_client = OllamaLLM()
        llm = llm_client.get_llm()
        
        mock_ollama_class.assert_called_once()
        assert llm == mock_ollama_instance
        assert llm_client.model == "mistral:7b-instruct"
