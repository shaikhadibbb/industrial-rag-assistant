import time
import uuid
import logging
import os
import traceback
import yaml
import httpx
import subprocess
import threading
import json
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from typing import Optional
from llama_index.core import Settings, QueryBundle
from src.retrieval.query_engine import get_query_engine
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.chunker import DocumentChunker
from src.retrieval.embedder import BGEEmbedder
from src.generation.llm_client import OllamaLLM

logger = logging.getLogger(__name__)

app = FastAPI(title="Industrial RAG Assistant API")

# Fix CORS: Environment-variable-based origins or default to http://localhost:7860
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:7860")
allowed_origins = [
    origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 🔒 API Security & Rate Limiting ---
class SlidingWindowRateLimiter:
    def __init__(self, limit_per_minute: int = 10):
        self.limit = limit_per_minute
        self.requests = {}  # maps IP to list of timestamps
        self.lock = threading.Lock()

    def is_rate_limited(self, identifier: str) -> tuple[bool, int]:
        """Returns (is_limited, retry_after_seconds)"""
        now = time.time()
        one_minute_ago = now - 60.0
        with self.lock:
            if identifier not in self.requests:
                self.requests[identifier] = [now]
                return False, 0

            # Filter out requests older than 60 seconds
            self.requests[identifier] = [
                t for t in self.requests[identifier] if t > one_minute_ago
            ]

            if len(self.requests[identifier]) >= self.limit:
                oldest_in_window = self.requests[identifier][0]
                retry_after = int(max(1.0, 60.0 - (now - oldest_in_window)))
                return True, retry_after

            self.requests[identifier].append(now)
            return False, 0


rate_limiter = SlidingWindowRateLimiter(limit_per_minute=10)

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    API_KEY = "rag_default_secret_key_2026"
    logger.warning(f"⚠️ API_KEY environment variable not set. Using default: {API_KEY}")
else:
    logger.info("🔑 API_KEY loaded successfully from environment.")


async def verify_security(request: Request):
    # 1. API Key Check
    client_key = request.headers.get("X-API-Key")
    if client_key != API_KEY:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Invalid or missing X-API-Key header."
        )

    # 2. Rate Limiting Check
    client_ip = request.client.host if request.client else "unknown"
    is_limited, retry_after = rate_limiter.is_rate_limited(client_ip)
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail=f"Too Many Requests: Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


# --- 📊 Prometheus In-Memory Metrics Store ---
metrics = {
    "rag_queries_total": {"query": 0, "query_stream": 0},
    "rag_errors_total": {"internal_error": 0, "validation_error": 0},
    "rag_tokens_generated_total": 0,
    "rag_query_latency_seconds_count": 0,
    "rag_query_latency_seconds_sum": 0.0,
    "rag_query_latency_seconds_bucket": {
        0.1: 0,
        0.5: 0,
        1.0: 0,
        2.0: 0,
        5.0: 0,
        float("inf"): 0,
    },
}

# Ingestion Background Job Statuses
ingestion_jobs = {}


# --- 📝 Structured JSON Logging Middleware ---
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())

    response = await call_next(request)

    duration = time.time() - start_time

    log_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2),
        "client_host": request.client.host if request.client else "unknown",
    }

    # Print structured logs directly to console (stdout)
    print(json.dumps(log_data))
    return response


def start_mlflow():
    try:
        import shutil

        mlflow_path = shutil.which("mlflow") or "mlflow"
        subprocess.Popen([mlflow_path, "ui", "--port", "5001", "--host", "0.0.0.0"])
    except Exception as e:
        logger.error(f"Failed to start MLflow UI: {e}")


@app.on_event("startup")
async def startup_event():
    try:
        # Start MLflow UI in background (non-critical)
        threading.Thread(target=start_mlflow, daemon=True).start()
    except Exception as e:
        logger.warning(f"MLflow startup skipped: {e}")

    try:
        # Initialize global settings
        Settings.embed_model = BGEEmbedder().get_embedding_model()
        Settings.llm = OllamaLLM().get_llm()

        # Warm up query engine singleton
        get_query_engine()
        logger.info("Startup: RAG Engine initialized.")
    except Exception as e:
        logger.warning(
            f"Startup: RAG engine could not initialize (services may not be ready): {e}. "
            "Engine will initialize on first request."
        )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    metrics["rag_errors_total"]["validation_error"] += 1
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=headers
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    metrics["rag_errors_total"]["internal_error"] += 1
    request_id = str(uuid.uuid4())
    logger.error(f"Unhandled Exception [Request ID: {request_id}]: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


@app.post("/query")
async def query_rag(request: QueryRequest, raw_request: Request):
    await verify_security(raw_request)
    metrics["rag_queries_total"]["query"] += 1
    t0 = time.time()

    engine = get_query_engine()
    response = await engine.aquery(request.question)

    latency = time.time() - t0

    # Update Prometheus Metrics
    metrics["rag_query_latency_seconds_count"] += 1
    metrics["rag_query_latency_seconds_sum"] += latency
    for bucket in sorted(metrics["rag_query_latency_seconds_bucket"].keys()):
        if latency <= bucket:
            metrics["rag_query_latency_seconds_bucket"][bucket] += 1
            break

    # Track generated tokens (rough word multiplier heuristic)
    token_count = int(len(str(response).split()) * 1.33)
    metrics["rag_tokens_generated_total"] += token_count

    # Extract and process sources as requested
    sources = []
    seen_pages = set()

    if hasattr(response, "source_nodes"):
        for node in response.source_nodes:
            text = node.node.text[:150]
            page = (
                node.node.metadata.get("page_label")
                or node.node.metadata.get("page_number")
                or "?"
            )
            filename = (
                node.node.metadata.get("file_name")
                or node.node.metadata.get("filename")
                or "Manual"
            )

            score = node.score if hasattr(node, "score") and node.score else 0.5
            norm_score = round(float(score), 4)

            # Deduplicate by page number (keep first occurrence)
            if page not in seen_pages:
                sources.append(
                    {
                        "filename": filename,
                        "page": page,
                        "score": norm_score,
                        "text_preview": text,
                    }
                )
                seen_pages.add(page)

    return {
        "answer": str(response),
        "sources": sources[:3],  # Return maximum 3 sources
        "latency_ms": round(latency * 1000, 2),
    }


@app.post("/query/stream")
async def query_rag_stream(request: QueryRequest, raw_request: Request):
    await verify_security(raw_request)
    metrics["rag_queries_total"]["query_stream"] += 1
    engine = get_query_engine()

    async def token_generator():
        t0 = time.time()
        try:
            # 1. Retrieve & Rerank nodes asynchronously
            nodes = await engine.hybrid_retriever.aretrieve(
                QueryBundle(query_str=request.question)
            )
            nodes = engine.reranker.postprocess_nodes(
                nodes, QueryBundle(query_str=request.question)
            )
            nodes = engine.deduplicator.postprocess_nodes(nodes)

            sources = []
            for node in nodes:
                sources.append(
                    {
                        "filename": node.node.metadata.get("filename") or "Manual",
                        "page": node.node.metadata.get("page_label") or "?",
                        "score": round(float(node.score), 4),
                        "text_preview": node.node.text[:150],
                    }
                )

            # Send initial sources
            yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

            # 2. Format the prompt
            context_str = "\n\n".join([n.node.text for n in nodes])
            from src.generation.prompt_templates import MISTRAL_PROMPT_TEMPLATE

            prompt = MISTRAL_PROMPT_TEMPLATE.format(
                context_str=context_str, query_str=request.question
            )

            # 3. Stream tokens asynchronously
            token_count = 0
            response_stream = await Settings.llm.astream_complete(prompt)
            async for chunk in response_stream:
                token_count += 1
                yield f"event: token\ndata: {json.dumps({'token': chunk.delta})}\n\n"

            metrics["rag_tokens_generated_total"] += token_count
            latency = time.time() - t0

            # Record latency
            metrics["rag_query_latency_seconds_count"] += 1
            metrics["rag_query_latency_seconds_sum"] += latency
            for bucket in sorted(metrics["rag_query_latency_seconds_bucket"].keys()):
                if latency <= bucket:
                    metrics["rag_query_latency_seconds_bucket"][bucket] += 1
                    break

            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            metrics["rag_errors_total"]["internal_error"] += 1
            logger.error(f"SSE stream failed: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': 'Internal server error during streaming'})}\n\n"

    return StreamingResponse(token_generator(), media_type="text/event-stream")


@app.get("/health")
async def health():
    config_path = "configs/config.yaml"
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        # OLLAMA_BASE_URL env var overrides config (for Render deployments)
        ollama_url = os.getenv("OLLAMA_BASE_URL", config["llm"]["base_url"])
    except Exception:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

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

    overall = (
        "healthy"
        if qdrant_status == "connected" and ollama_status == "connected"
        else "degraded"
    )

    return {"status": overall, "qdrant": qdrant_status, "ollama": ollama_status}


@app.get("/metrics")
async def get_metrics():
    """Standard Prometheus Exporter text response."""
    lines = [
        "# HELP rag_queries_total Number of queries received",
        "# TYPE rag_queries_total counter",
        f'rag_queries_total{{endpoint="/query"}} {metrics["rag_queries_total"]["query"]}',
        f'rag_queries_total{{endpoint="/query/stream"}} {metrics["rag_queries_total"]["query_stream"]}',
        "",
        "# HELP rag_errors_total Number of queries resulting in errors",
        "# TYPE rag_errors_total counter",
        f'rag_errors_total{{error_type="internal_error"}} {metrics["rag_errors_total"]["internal_error"]}',
        f'rag_errors_total{{error_type="validation_error"}} {metrics["rag_errors_total"]["validation_error"]}',
        "",
        "# HELP rag_tokens_generated_total Total generated tokens",
        "# TYPE rag_tokens_generated_total counter",
        f'rag_tokens_generated_total {metrics["rag_tokens_generated_total"]}',
        "",
        "# HELP rag_query_latency_seconds Query latency histogram",
        "# TYPE rag_query_latency_seconds histogram",
    ]

    cumulative = 0
    for le, count in sorted(metrics["rag_query_latency_seconds_bucket"].items()):
        cumulative += count
        le_str = "+Inf" if le == float("inf") else f"{le:.1f}"
        lines.append(f'rag_query_latency_seconds_bucket{{le="{le_str}"}} {cumulative}')

    lines.extend(
        [
            f'rag_query_latency_seconds_sum {metrics["rag_query_latency_seconds_sum"]}',
            f'rag_query_latency_seconds_count {metrics["rag_query_latency_seconds_count"]}',
            "",
        ]
    )

    return Response(content="\n".join(lines), media_type="text/plain")


# --- 📁 Async PDF Ingestion Task Handler ---
def process_ingestion_task(temp_path: Path, filename: str, job_id: str):
    try:
        ingestion_jobs[job_id] = "processing"

        parser = PDFParser(str(temp_path.parent))
        docs = parser.parse_pdf(str(temp_path))
        chunker = DocumentChunker()
        nodes = chunker.chunk_documents(docs)

        engine = get_query_engine()
        engine.qdrant_store.upsert_nodes(nodes)

        ingestion_jobs[job_id] = "success"
    except Exception as e:
        logger.error(
            f"Async background ingestion failed for {filename} [Job: {job_id}]: {e}"
        )
        ingestion_jobs[job_id] = f"failed: {str(e)}"
        if temp_path.exists():
            temp_path.unlink()


MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@app.post("/ingest")
async def ingest_file(
    background_tasks: BackgroundTasks,
    raw_request: Request,
    file: UploadFile = File(...),
):
    await verify_security(raw_request)
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
                    raise HTTPException(
                        status_code=413,
                        detail="File size exceeds maximum limit of 50MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to write file to temp path: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    # Queue the ingestion inside FastAPI BackgroundTasks
    job_id = str(uuid.uuid4())
    ingestion_jobs[job_id] = "pending"
    background_tasks.add_task(process_ingestion_task, temp_path, filename, job_id)

    return {
        "status": "accepted",
        "job_id": job_id,
        "message": "Ingestion job successfully queued.",
    }


@app.get("/ingest/status/{job_id}")
async def get_ingestion_status(job_id: str, raw_request: Request):
    await verify_security(raw_request)
    if job_id not in ingestion_jobs:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return {"job_id": job_id, "status": ingestion_jobs[job_id]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
