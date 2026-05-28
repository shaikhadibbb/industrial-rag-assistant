from unittest.mock import MagicMock, patch

with patch("src.retrieval.keyword_retriever.QdrantStore") as mock_store:
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
