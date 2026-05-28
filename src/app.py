import time
import uuid
import logging
import os
import traceback
import yaml
import httpx
import subprocess
import threading
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import List, Optional
from llama_index.core import Settings
from src.retrieval.query_engine import get_query_engine
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.chunker import DocumentChunker
from src.retrieval.vector_store import QdrantStore
from src.retrieval.embedder import BGEEmbedder
from src.generation.llm_client import OllamaLLM

logger = logging.getLogger(__name__)

app = FastAPI(title="Industrial RAG Assistant API")

# Fix CORS: Environment-variable-based origins or default to http://localhost:7860
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:7860")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def start_mlflow():
    try:
        mlflow_path = os.path.join(os.getcwd(), "venv", "bin", "mlflow")
        subprocess.Popen([mlflow_path, "ui", "--port", "5001", "--host", "0.0.0.0"])
    except Exception as e:
        logger.error(f"Failed to start MLflow UI: {e}")

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

# Fix Error Handling: Global exception handler to prevent leaking raw tracebacks
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    logger.error(f"Unhandled Exception [Request ID: {request_id}]: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id}
    )

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

@app.post("/query")
async def query_rag(request: QueryRequest):
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
            # Fix score normalization: remove the nonsensical 1 / (1 + abs(score)) and return raw rounded score
            norm_score = round(float(score), 4)
            
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

@app.get("/health")
async def health():
    config_path = "configs/config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    ollama_url = config['llm']['base_url']
    
    qdrant_status = "unreachable"
    ollama_status = "unreachable"
    
    # 1. Ping Qdrant
    try:
        engine = get_query_engine()
        client = engine.qdrant_store.client
        if hasattr(client, "health_check"):
            client.health_check()
        else:
            client.get_collections()
        qdrant_status = "connected"
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        qdrant_status = f"disconnected: {str(e)}"
        
    # 2. Ping Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as httpx_client:
            response = await httpx_client.get(f"{ollama_url}/api/tags")
            if response.status_code == 200:
                ollama_status = "connected"
            else:
                ollama_status = f"disconnected (status code: {response.status_code})"
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        ollama_status = f"disconnected: {str(e)}"
        
    overall = "healthy" if qdrant_status == "connected" and ollama_status == "connected" else "degraded"
    
    return {
        "status": overall,
        "qdrant": qdrant_status,
        "ollama": ollama_status
    }

MAX_FILE_SIZE = 50 * 1024 * 1024 # 50MB

@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    # Sanitize filename
    filename = Path(file.filename).name
    
    # Validate file type (PDF only)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    temp_dir = Path("data/raw")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / filename
    
    # Enforce max size (50MB) and save to temp directory first
    size = 0
    try:
        with open(temp_path, "wb") as buffer:
            while chunk := await file.read(8192):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    buffer.close()
                    if temp_path.exists():
                        temp_path.unlink()
                    raise HTTPException(status_code=413, detail="File size exceeds maximum limit of 50MB.")
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to write file to temp path: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")
        
    # Process the file
    parser = PDFParser(str(temp_dir))
    docs = parser.parse_pdf(str(temp_path))
    chunker = DocumentChunker()
    nodes = chunker.chunk_documents(docs)
    
    engine = get_query_engine()
    engine.qdrant_store.upsert_nodes(nodes)
    
    return {"status": "success", "message": f"Ingested {filename}"}
