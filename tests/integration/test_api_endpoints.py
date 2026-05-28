import pytest
from fastapi.testclient import TestClient
from src.app import app, API_KEY
from tests.conftest import QDRANT_UP, OLLAMA_UP

client = TestClient(app)


def test_api_health_endpoint():
    # The health check is robust and should return 200 OK even if degraded
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert "qdrant" in json_data
    assert "ollama" in json_data


@pytest.mark.skipif(
    not (QDRANT_UP and OLLAMA_UP),
    reason="Requires running local Qdrant (port 6333) and Ollama (port 11434) services.",
)
def test_api_query_endpoint():
    headers = {"X-API-Key": API_KEY}
    response = client.post("/query", json={"question": "Test query"}, headers=headers)
    assert response.status_code == 200
    json_data = response.json()
    assert "answer" in json_data
    assert "sources" in json_data
    assert "latency_ms" in json_data


def test_api_ingest_invalid_file_type():
    # Attempt uploading non-PDF
    headers = {"X-API-Key": API_KEY}
    response = client.post(
        "/ingest",
        files={"file": ("test.txt", b"dummy content", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json()["detail"]
