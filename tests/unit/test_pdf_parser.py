from unittest.mock import MagicMock, patch
from src.ingestion.pdf_parser import PDFParser


def test_parse_pdf():
    # Setup mock fitz Document and Page
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is a test page."

    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 2
    mock_doc.load_page.return_value = mock_page

    with patch("fitz.open", return_value=mock_doc) as mock_open:
        parser = PDFParser(data_dir="dummy_dir")
        docs = parser.parse_pdf("dummy_dir/test.pdf")

        mock_open.assert_called_once_with("dummy_dir/test.pdf")
        assert len(docs) == 2
        assert docs[0].text == "This is a test page."
        assert docs[0].metadata["filename"] == "test.pdf"
        assert docs[0].metadata["page_number"] == 1
        assert docs[1].metadata["page_number"] == 2
        mock_doc.close.assert_called_once()
