from unittest.mock import MagicMock, patch
from src.ingestion.pdf_parser import PDFParser, main


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


def test_parse_pdf_ocr_fallback():
    mock_page = MagicMock()
    mock_page.get_text.return_value = ""  # Empty text triggers OCR

    mock_pixmap = MagicMock()
    mock_pixmap.tobytes.return_value = b"fake_png_bytes"
    mock_page.get_pixmap.return_value = mock_pixmap

    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_doc.load_page.return_value = mock_page

    mock_pytesseract = MagicMock()
    mock_pytesseract.image_to_string.return_value = "OCR extracted text"
    mock_pil = MagicMock()

    with patch("fitz.open", return_value=mock_doc), patch.dict(
        "sys.modules", {"pytesseract": mock_pytesseract, "PIL": mock_pil}
    ):
        parser = PDFParser(data_dir="dummy_dir")
        docs = parser.parse_pdf("dummy_dir/scanned.pdf")

        assert len(docs) == 1
        assert docs[0].text == "OCR extracted text"
        mock_pytesseract.image_to_string.assert_called_once()


def test_parse_pdf_exception():
    with patch("fitz.open", side_effect=Exception("Failed to open")):
        parser = PDFParser(data_dir="dummy_dir")
        docs = parser.parse_pdf("dummy_dir/bad.pdf")
        assert len(docs) == 0


def test_parse_all():
    parser = PDFParser(data_dir="dummy_dir")
    with patch("os.listdir", return_value=["a.pdf", "b.txt", "c.pdf"]), patch.object(
        parser, "parse_pdf", return_value=[MagicMock()]
    ) as mock_parse_pdf:
        docs = parser.parse_all()
        assert len(docs) == 2
        assert mock_parse_pdf.call_count == 2


def test_main():
    with patch(
        "src.ingestion.pdf_parser.PDFParser.parse_all", return_value=[MagicMock()]
    ):
        main()  # Should run without error
