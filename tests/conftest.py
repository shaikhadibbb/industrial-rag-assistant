"""Test configuration for CI and local environments."""

import socket
import pytest


def check_service(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


QDRANT_UP = check_service("localhost", 6333)
OLLAMA_UP = check_service("localhost", 11434)


@pytest.fixture(scope="session", autouse=True)
def print_service_status():
    """Prints local service dependencies state during test runs."""
    print("\n" + "=" * 50)
    print("📡 Local RAG Integration Services Health:")
    print(
        f"  - Qdrant Vector DB (Port 6333): {'🟢 ONLINE' if QDRANT_UP else '🔴 OFFLINE'}"
    )
    print(
        f"  - Ollama LLM Service (Port 11434): {'🟢 ONLINE' if OLLAMA_UP else '🔴 OFFLINE'}"
    )
    if not (QDRANT_UP and OLLAMA_UP):
        print("📢 NOTE: Integration tests calling local Qdrant/Ollama will be skipped.")
    print("=" * 50 + "\n")
