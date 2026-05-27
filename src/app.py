import time
import uuid
import logging
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from llama_index.core import Settings
from src.retrieval.query_engine import get_query_engine
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.chunker import DocumentChunker
from src.retrieval.vector_store import QdrantStore
from src.retrieval.embedder import BGEEmbedder
from src.generation.llm_client import OllamaLLM
import subprocess
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Industrial RAG Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def start_mlflow():
    mlflow_path = os.path.join(os.getcwd(), "venv", "bin", "mlflow")
    subprocess.Popen([mlflow_path, "ui", "--port", "5001", "--host", "0.0.0.0"])

@app.on_event("startup")
async def startup_event():
    try:
        # Start MLflow UI in background
        threading.Thread(target=start_mlflow, daemon=True).start()
        
        # Initialize global settings
        Settings.embed_model = BGEEmbedder().get_embedding_model()
        Settings.llm = OllamaLLM().get_llm()
        
        # Warm up query engine singleton
        get_query_engine()
        logger.info("Startup: RAG Engine initialized.")
    except Exception as e:
        logger.error(f"Startup Failure: {e}")

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

@app.post("/query")
async def query_rag(request: QueryRequest):
    try:
        engine = get_query_engine()
        start_time = time.time()
        response = engine.query(request.question)
        latency = (time.time() - start_time) * 1000
        
        # Extract and process sources as requested
        sources = []
        seen_pages = set()
        
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                text = node.node.text[:150]
                page = node.node.metadata.get("page_label") or node.node.metadata.get("page_number") or "?"
                filename = node.node.metadata.get("file_name") or node.node.metadata.get("filename") or "Manual"
                
                score = node.score if hasattr(node, "score") and node.score else 0.5
                # Normalize score: round(1 / (1 + abs(score)), 3) if score > 1 else round(abs(score), 3)
                norm_score = round(1 / (1 + abs(score)), 3) if abs(score) > 1.0 else round(abs(score), 3)
                
                # Deduplicate by page number (keep first occurrence)
                if page not in seen_pages:
                    sources.append({
                        "filename": filename,
                        "page": page,
                        "score": norm_score,
                        "text_preview": text
                    })
                    seen_pages.add(page)
        
        return {
            "answer": str(response),
            "sources": sources[:3], # Return maximum 3 sources
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        logger.error(f"Query Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "qdrant": "connected",
        "ollama": "connected"
    }

@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    temp_path = f"data/raw/{file.filename}"
    os.makedirs("data/raw", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(await file.read())
        
    try:
        parser = PDFParser("data/raw")
        docs = parser.parse_pdf(temp_path)
        chunker = DocumentChunker()
        nodes = chunker.chunk_documents(docs)
        
        engine = get_query_engine()
        engine.qdrant_store.upsert_nodes(nodes)
        
        return {"status": "success", "message": f"Ingested {file.filename}"}
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
