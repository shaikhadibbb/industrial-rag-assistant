import argparse
import logging
import time
import mlflow
import os
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.chunker import DocumentChunker
from src.retrieval.vector_store import QdrantStore
from src.retrieval.embedder import BGEEmbedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_ingestion(data_dir: str):
    """Main ingestion pipeline."""
    start_time = time.time()
    
    # 1. Initialize mlflow
    mlflow.set_experiment("rag-ingestion")
    
    with mlflow.start_run():
        logger.info(f"Starting ingestion from {data_dir}")
        
        # 2. Parse PDFs
        parser = PDFParser(data_dir)
        documents = parser.parse_all()
        
        if not documents:
            logger.error("No documents found to ingest.")
            return
            
        # 3. Chunk
        chunker = DocumentChunker()
        nodes = chunker.chunk_documents(documents)
        
        # 4. Embed and Store
        store = QdrantStore()
        # Initialize embedder to ensure it's loaded in the process
        embedder = BGEEmbedder()
        
        # Upsert (LlamaIndex handles embedding during upsert if configured)
        # However, for control, we use the store.upsert_nodes which takes the nodes
        # and uses the global settings or passed embed_model.
        from llama_index.core import Settings
        Settings.embed_model = embedder.get_embedding_model()
        
        store.upsert_nodes(nodes)
        
        duration = time.time() - start_time
        
        # 5. Log stats to MLflow
        mlflow.log_param("data_dir", data_dir)
        mlflow.log_metric("total_documents", len(os.listdir(data_dir)))
        mlflow.log_metric("total_pages", len(documents))
        mlflow.log_metric("total_chunks", len(nodes))
        mlflow.log_metric("ingestion_time_sec", duration)
        
        logger.info("--- Ingestion Summary ---")
        logger.info(f"Total Docs: {len(os.listdir(data_dir))}")
        logger.info(f"Total Chunks: {len(nodes)}")
        logger.info(f"Time Taken: {duration:.2f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDF documents into Qdrant.")
    parser.add_argument("--data-dir", type=str, default="data/raw", help="Directory containing PDFs")
    args = parser.parse_args()
    
    run_ingestion(args.data_dir)
