import logging
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

logger = logging.getLogger(__name__)


class QdrantStore:
    """Manager for Qdrant Vector Store."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.host = config["vector_store"].get("host", "localhost")
        self.port = config["vector_store"].get("port", 6333)
        self.collection_name = config["vector_store"]["collection_name"]

        try:
            # Try connecting to remote Qdrant first
            logger.info(f"Connecting to Qdrant at {self.host}:{self.port}")
            self.client = qdrant_client.QdrantClient(
                host=self.host, port=self.port, timeout=5
            )
            # Check if reachable
            self.client.get_collections()
            logger.info("Successfully connected to remote Qdrant.")
        except Exception as e:
            logger.warning(
                f"Could not connect to Qdrant at {self.host}:{self.port}: {e}"
            )
            logger.info("Falling back to local Qdrant storage at ./qdrant_data")
            self.client = qdrant_client.QdrantClient(path="./qdrant_data")

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
