# Render.com Slim Dockerfile (default)
# Uses fastembed (ONNX) instead of PyTorch — fits in 512MB free tier RAM
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install slim requirements (no PyTorch / sentence-transformers)
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

# Pre-download FastEmbed model files to bake them into the image
# This saves memory during startup (no unzipping/downloading in constrained RAM)
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='/app/.cache/fastembed')"

COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Memory-efficient settings for 512MB RAM
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV NUMEXPR_MAX_THREADS=1
ENV TOKENIZERS_PARALLELISM=false

# Render-specific: use fastembed (ONNX, no PyTorch) and skip reranker
ENV USE_FASTEMBED=true
ENV SKIP_RERANKER=true
ENV SKIP_MLFLOW=true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
