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
                
                metadata = {
                    "filename": filename,
                    "page_number": page_num + 1,
                    "total_pages": total_pages
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

def main():
    """Standalone test for PDFParser."""
    # Create a dummy pdf if none exists for testing or just log
    parser = PDFParser("data/raw")
    docs = parser.parse_all()
    print(f"Parsed {len(docs)} pages.")

if __name__ == "__main__":
    main()
