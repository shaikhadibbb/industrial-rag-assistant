import logging
import os
import yaml
import qdrant_client

# Monkeypatch QdrantClient to support old search API in newer qdrant-client versions
if not hasattr(qdrant_client.QdrantClient, "search"):
    qdrant_client.QdrantClient.search = (
        lambda self, *args, **kwargs: self._client.search(*args, **kwargs)
    )

from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from typing import List
import threading

logger = logging.getLogger(__name__)

_qdrant_client_instance = None
_qdrant_client_lock = threading.Lock()


class QdrantStore:
    """Manager for Qdrant Vector Store."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        global _qdrant_client_instance
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Environment variables override config.yaml (for Render / Docker / Cloud deployments)
        self.host = os.getenv(
            "QDRANT_HOST", config["vector_store"].get("host", "localhost")
        )
        self.port = int(
            os.getenv("QDRANT_PORT", config["vector_store"].get("port", 6333))
        )
        self.collection_name = config["vector_store"]["collection_name"]

        # Qdrant Cloud API key — if set, use URL-based cloud connection
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if _qdrant_client_instance is None:
            with _qdrant_client_lock:
                if _qdrant_client_instance is None:
                    import time

                    max_retries = 5
                    retry_delay = 1.0
                    connected = False
                    for attempt in range(1, max_retries + 1):
                        try:
                            if qdrant_api_key:
                                # ☁️  Qdrant Cloud mode: URL + API key (JWT or secret)
                                cloud_url = f"https://{self.host}"
                                logger.info(
                                    f"Connecting to Qdrant Cloud at {cloud_url} (Attempt {attempt}/{max_retries})..."
                                )
                                client = qdrant_client.QdrantClient(
                                    url=cloud_url,
                                    api_key=qdrant_api_key,
                                    timeout=10,
                                )
                            else:
                                # 🖥️  Local / Docker mode: host + port
                                logger.info(
                                    f"Connecting to Qdrant at {self.host}:{self.port} (Attempt {attempt}/{max_retries})..."
                                )
                                client = qdrant_client.QdrantClient(
                                    host=self.host, port=self.port, timeout=5
                                )

                            client.get_collections()
                            _qdrant_client_instance = client
                            logger.info("Successfully connected to Qdrant.")
                            connected = True
                            break
                        except Exception as e:
                            logger.warning(f"Connection attempt {attempt} failed: {e}")
                            if attempt < max_retries:
                                sleep_time = retry_delay * (2 ** (attempt - 1))
                                logger.info(f"Retrying in {sleep_time:.1f} seconds...")
                                time.sleep(sleep_time)

                    if not connected:
                        logger.warning(
                            "Could not connect to Qdrant after all retries. "
                            "Falling back to local storage at ./qdrant_data"
                        )
                        _qdrant_client_instance = qdrant_client.QdrantClient(
                            path="./qdrant_data"
                        )

        self.client = _qdrant_client_instance
        self.vector_store = QdrantVectorStore(
            client=self.client, collection_name=self.collection_name, path=None
        )

    def upsert_nodes(self, nodes: List[TextNode]):
        """Upserts nodes into Qdrant."""
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        index = VectorStoreIndex(
            nodes, storage_context=storage_context, show_progress=True
        )
        logger.info(f"Successfully upserted {len(nodes)} nodes to Qdrant.")
        return index

    def delete_collection(self):
        """Deletes the collection for cleanup."""
        self.client.delete_collection(self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")

    def get_collection_info(self):
        """Returns collection statistics."""
        info = self.client.get_collection(self.collection_name)
        logger.info(f"Collection Info: {info}")
        return info

    def get_vector_store(self):
        """Returns the QdrantVectorStore object."""
        return self.vector_store
