import socket
import pytest
from src.retrieval.query_engine import get_query_engine

def check_service(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False

QDRANT_UP = check_service("localhost", 6333)
OLLAMA_UP = check_service("localhost", 11434)

@pytest.mark.skipif(not (QDRANT_UP and OLLAMA_UP), reason="Requires local Qdrant and Ollama services to be running.")
def test_query_engine_integration():
    engine = get_query_engine()
    assert engine is not None
    
    # Try a simple query
    response = engine.query("What is the main safety procedure?")
    assert response is not None
    # Response can be empty or have text, but it must return a valid response object
    assert hasattr(response, "response") or hasattr(response, "source_nodes")
