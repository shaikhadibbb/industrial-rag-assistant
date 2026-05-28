import socket
import pytest
from fastapi.testclient import TestClient
from src.app import app

def check_service(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False

QDRANT_UP = check_service("localhost", 6333)
OLLAMA_UP = check_service("localhost", 11434)

client = TestClient(app)

def test_api_health_endpoint():
    # The health check is robust and should return 200 OK even if degraded
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert "qdrant" in json_data
    assert "ollama" in json_data

@pytest.mark.skipif(not (QDRANT_UP and OLLAMA_UP), reason="Requires local Qdrant and Ollama services to be running.")
def test_api_query_endpoint():
    response = client.post("/query", json={"question": "Test query"})
    assert response.status_code == 200
    json_data = response.json()
    assert "answer" in json_data
    assert "sources" in json_data
    assert "latency_ms" in json_data

def test_api_ingest_invalid_file_type():
    # Attempt uploading non-PDF
    response = client.post("/ingest", files={"file": ("test.txt", b"dummy content", "text/plain")})
    assert response.status_code == 400
    assert "Only PDF files are allowed" in response.json()["detail"]
