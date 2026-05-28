import logging
import yaml
from typing import List
from llama_index.core.node_parser import SentenceWindowNodeParser, TokenTextSplitter
from llama_index.core.schema import TextNode, Document

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Chunker for breaking documents into smaller nodes for embedding."""

    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.chunk_size = config["data"]["chunk_size"]
        self.chunk_overlap = config["data"]["chunk_overlap"]

        # Advanced parser
        self.sentence_parser = SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )

        # Fallback parser
        self.fallback_parser = TokenTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

    def chunk_documents(self, documents: List[Document]) -> List[TextNode]:
        """Splits documents into nodes using SentenceWindowNodeParser with fallback."""
        try:
            nodes = self.sentence_parser.get_nodes_from_documents(documents)
            logger.info(
                f"Chunked {len(documents)} docs into {len(nodes)} nodes using SentenceWindow."
            )
        except Exception as e:
            logger.warning(
                f"SentenceWindowNodeParser failed, falling back to TokenTextSplitter: {e}"
            )
            nodes = self.fallback_parser.get_nodes_from_documents(documents)
            logger.info(
                f"Chunked {len(documents)} docs into {len(nodes)} nodes using fallback."
            )

        if nodes:
            avg_size = sum(len(n.get_content()) for n in nodes) / len(nodes)
            logger.info(f"Average chunk size: {avg_size:.2f} characters.")

        return nodes
