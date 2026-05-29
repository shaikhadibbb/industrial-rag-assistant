# ADR 004: Choice of Embedding Engine (FastEmbed ONNX vs. Sentence-Transformers PyTorch)

## Context & Problem Statement

Our RAG system relies on dense vector embeddings generated from text chunks via the `BAAI/bge-small-en-v1.5` model. In our initial prototype, we loaded this model using the popular **Sentence-Transformers** library.

However, loading Sentence-Transformers in production triggered immediate Out-Of-Memory (OOM) failures:
1.  **PyTorch Overhead**: Sentence-Transformers depends directly on PyTorch. Simply importing `torch` and loading a model allocates over **600MB of RSS memory** instantly.
2.  **Staging Ceiling**: Render's free tier caps physical memory at **512MB RAM**. Any process exceeding this limit is abruptly terminated by the operating system kernel.
3.  **ONNX Compilation**: We needed a library that could load and run standard Hugging Face embedding models without requiring PyTorch, while maintaining embedding cosine parity.

We evaluated two libraries: **Sentence-Transformers (PyTorch)** and **FastEmbed (ONNX Runtime)**.

---

## Decision Drivers

*   **Memory Footprint**: The library must load and execute models inside a strict <150MB memory footprint.
*   **Import Latency**: Module import and model loading times must be under 3 seconds to prevent API server startup timeouts.
*   **Execution Speed**: Embedding generation on standard virtualized CPUs must be highly optimized.
*   **Embedding Parity**: Cosine similarities computed between generated embeddings must remain identical to original weights to preserve retrieval quality.

---

## Comparative Analysis

| Metric | Sentence-Transformers (PyTorch) | FastEmbed (ONNX Runtime) |
| :--- | :--- | :--- |
| **Primary Dependency** | PyTorch (Heavy, deep learning framework) | ONNX Runtime (C++ optimized inference) |
| **RAM Footprint (Model loaded)**| **~600MB to 850MB** (Instantly OOMs) | **~80MB to 120MB** (Staging safe) |
| **Model Import Time** | ~6.5 seconds | **~1.1 seconds** |
| **Embedding Speed (CPU)** | 1.0x (Standard) | **2.5x to 4.0x faster** (C++ optimized engine) |
| **Pydantic Validation Compatibility** | High (Direct integration) | Native (Engineered by Qdrant specifically) |

---

## Decision

We replaced Sentence-Transformers with **FastEmbed** running the ONNX compiled version of the `bge-small-en-v1.5` model in our production environments, while structuring the local pipeline to dynamically fallback if needed.

---

## Consequences

### Positive
*   **Deployment Stability**: Render staging memory consumption dropped from a crashing >750MB to a highly stable **115MB total RAM**, resolving memory leaks and system terminations completely.
*   **Ultra-Fast CPU Ingestion**: Ingesting complex, multi-page PDFs is 3x faster, as FastEmbed ONNX executes matrix operations using highly optimized C++ threads, bypassing Python's Global Interpreter Lock (GIL).
*   **ONNX Pre-baking**: Pre-baked the FastEmbed model download into our multi-stage Docker build step. This guarantees the model is present on disk at launch, preventing network-based startup latencies on the server.
*   **Skip Reranker Integration**: Structuring the pipeline to conditionally skip the heavy Cross-Encoder reranker when running in memory-constrained staging environments (via the `SKIP_RERANKER` environment variable) while retaining it for high-memory environments.

### Negative / Trade-Offs
*   **Model Options**: FastEmbed supports a curated subset of popular embedding models. However, our preferred model `BAAI/bge-small-en-v1.5` is fully supported natively, meaning there was zero compromise on our target RAGAS retrieval accuracy.
