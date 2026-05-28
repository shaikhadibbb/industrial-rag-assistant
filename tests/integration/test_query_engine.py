import pytest
from src.retrieval.query_engine import get_query_engine
from tests.conftest import QDRANT_UP, OLLAMA_UP


@pytest.mark.skipif(
    not (QDRANT_UP and OLLAMA_UP),
    reason="Requires running local Qdrant (port 6333) and Ollama (port 11434) services.",
)
def test_query_engine_integration():
    engine = get_query_engine()
    assert engine is not None

    # Try a simple query
    response = engine.query("What is the main safety procedure?")
    assert response is not None
    # Response can be empty or have text, but it must return a valid response object
    assert hasattr(response, "response") or hasattr(response, "source_nodes")
