import fitz
import os
import logging
from typing import List
from llama_index.core import Document

logger = logging.getLogger(__name__)


class PDFParser:
    """Parser to extract text from PDF files using PyMuPDF."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def parse_pdf(self, file_path: str) -> List[Document]:
        """Parses a single PDF file and returns a list of Document objects."""
        documents = []
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            filename = os.path.basename(file_path)

            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                text = page.get_text()

                # OCR Fallback for image-only or scanned PDFs
                if not text.strip():
                    logger.info(
                        f"Page {page_num + 1} of {filename} yielded empty text. Attempting OCR fallback..."
                    )
                    try:
                        import io
                        from PIL import Image
                        import pytesseract

                        # Render page to PNG pixmap using fitz
                        pix = page.get_pixmap(dpi=150)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))

                        # Run OCR
                        ocr_text = pytesseract.image_to_string(img)
                        if ocr_text.strip():
                            text = ocr_text
                            logger.info(
                                f"OCR successfully extracted {len(text)} characters from page {page_num + 1}."
                            )
                        else:
                            logger.warning(
                                f"OCR returned empty text for page {page_num + 1}."
                            )
                    except ImportError:
                        logger.warning(
                            "pytesseract or PIL is not installed. Skipping OCR fallback."
                        )
                    except Exception as ocr_err:
                        logger.error(
                            f"OCR fallback failed on page {page_num + 1}: {ocr_err}"
                        )

                metadata = {
                    "filename": filename,
                    "page_number": page_num + 1,
                    "total_pages": total_pages,
                }

                documents.append(Document(text=text, metadata=metadata))

            doc.close()
            logger.info(f"Successfully parsed {filename} with {total_pages} pages.")
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")

        return documents

    def parse_all(self) -> List[Document]:
        """Parses all PDF files in the data directory."""
        all_docs = []
        for file in os.listdir(self.data_dir):
            if file.endswith(".pdf"):
                path = os.path.join(self.data_dir, file)
                all_docs.extend(self.parse_pdf(path))
        return all_docs


def main() -> None:
    """Standalone test for PDFParser."""
    # Create a dummy pdf if none exists for testing or just log
    parser = PDFParser("data/raw")
    docs = parser.parse_all()
    print(f"Parsed {len(docs)} pages.")


if __name__ == "__main__":
    main()
