from unittest.mock import patch
from llama_index.core import Document
from src.ingestion.chunker import DocumentChunker


def test_chunk_documents_success():
    chunker = DocumentChunker()
    doc = Document(
        text="This is sentence one. This is sentence two.",
        metadata={"filename": "test.pdf"},
    )

    # Check that normal chunking parses nodes
    nodes = chunker.chunk_documents([doc])
    assert len(nodes) > 0
    assert all(n.metadata["filename"] == "test.pdf" for n in nodes)


def test_chunk_documents_fallback():
    chunker = DocumentChunker()
    doc = Document(
        text="This is fallback text to chunk.", metadata={"filename": "test.pdf"}
    )

    # Force SentenceWindowNodeParser class method to fail to test fallback
    with patch(
        "llama_index.core.node_parser.SentenceWindowNodeParser.get_nodes_from_documents",
        side_effect=Exception("Parsing error"),
    ):
        nodes = chunker.chunk_documents([doc])
        assert len(nodes) > 0
        assert all(n.metadata["filename"] == "test.pdf" for n in nodes)
