import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # Clear rate limiter states before each test
    from src.app import rate_limiter

    with rate_limiter.lock:
        rate_limiter.requests.clear()


def test_api_unauthorized_without_key():
    # Sending query without X-API-Key header should be unauthorized
    response = client.post("/query", json={"question": "What is the pressure limit?"})
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_api_unauthorized_with_invalid_key():
    # Sending query with incorrect key should be unauthorized
    headers = {"X-API-Key": "wrong_key_123"}
    response = client.post(
        "/query", json={"question": "What is the pressure limit?"}, headers=headers
    )
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


@patch("src.app.get_query_engine")
def test_api_authorized_with_correct_key(mock_get_query_engine):
    # Mocking the engine query response to avoid remote service dependencies
    mock_engine = MagicMock()
    mock_engine.aquery = AsyncMock(return_value="Mocked answer")
    mock_get_query_engine.return_value = mock_engine

    from src.app import API_KEY

    headers = {"X-API-Key": API_KEY}
    response = client.post(
        "/query", json={"question": "What is the pressure limit?"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "Mocked answer"


@patch("src.app.get_query_engine")
def test_api_rate_limiting(mock_get_query_engine):
    mock_engine = MagicMock()
    mock_engine.aquery = AsyncMock(return_value="Mocked answer")
    mock_get_query_engine.return_value = mock_engine

    from src.app import API_KEY

    headers = {"X-API-Key": API_KEY}

    # Make 10 requests (should succeed)
    for _ in range(10):
        response = client.post(
            "/query", json={"question": "Fast question"}, headers=headers
        )
        assert response.status_code == 200

    # 11th request in the same minute should be rate limited (429)
    response = client.post(
        "/query", json={"question": "Limited question"}, headers=headers
    )
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
    assert "Retry-After" in response.headers
