from unittest.mock import MagicMock, patch
from src.retrieval.keyword_retriever import KeywordRetriever


def test_keyword_retriever_initialization():
    mock_client = MagicMock()
    # Mocking scroll to return empty list of points
    mock_client.scroll.return_value = ([], None)

    with patch("src.retrieval.keyword_retriever.QdrantStore") as mock_store_class:
        mock_store_inst = MagicMock()
        mock_store_inst.client = mock_client
        mock_store_inst.collection_name = "test_collection"
        mock_store_class.return_value = mock_store_inst

        retriever = KeywordRetriever()
        assert retriever.retriever is None


def test_keyword_retriever_successful_initialization():
    mock_client = MagicMock()
    mock_point = MagicMock()
    mock_point.id = "point-123"
    mock_point.payload = {
        "_node_content": '{"text": "Sample text", "metadata": {"filename": "manual.pdf"}}'
    }
    mock_client.scroll.return_value = ([mock_point], None)

    mock_bm25_instance = MagicMock()

    with patch(
        "src.retrieval.keyword_retriever.QdrantStore"
    ) as mock_store_class, patch(
        "llama_index.retrievers.bm25.BM25Retriever.from_defaults",
        return_value=mock_bm25_instance,
    ) as mock_from_defaults:
        mock_store_inst = MagicMock()
        mock_store_inst.client = mock_client
        mock_store_inst.collection_name = "test_collection"
        mock_store_class.return_value = mock_store_inst

        retriever = KeywordRetriever()
        assert retriever.retriever == mock_bm25_instance
        mock_from_defaults.assert_called_once()


def test_keyword_retriever_retrieve():
    mock_client = MagicMock()
    mock_client.scroll.return_value = ([], None)

    with patch("src.retrieval.keyword_retriever.QdrantStore") as mock_store_class:
        mock_store_inst = MagicMock()
        mock_store_inst.client = mock_client
        mock_store_inst.collection_name = "test_collection"
        mock_store_class.return_value = mock_store_inst

        retriever = KeywordRetriever()
        # When uninitialized
        assert retriever.retrieve("query") == []

        # When mock retriever is set
        mock_bm25 = MagicMock()
        mock_bm25.retrieve.return_value = ["mocked_node"]
        retriever.retriever = mock_bm25
        assert retriever.retrieve("query") == ["mocked_node"]
