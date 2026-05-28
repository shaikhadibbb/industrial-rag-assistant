# Industrial RAG Assistant

> [!WARNING]
> **Status: Prototype / In Development** (Target Production Release: August 2026)
> This repository is in active development to transition a functional local prototype into a production-grade, highly secure, and optimized system.

A Retrieval-Augmented Generation (RAG) assistant designed for querying and navigating complex industrial maintenance manuals and troubleshooting guides.

---

## 📊 Current Metrics & Targets

We hold ourselves to strict, transparent evaluations using the RAGAS framework. The current prototype baseline scores vs. the August 2026 production-grade targets are:

| Metric | Baseline (Current) | Target (Production) | Status |
| :--- | :---: | :---: | :---: |
| **RAGAS Faithfulness** | **0.583** | **>0.70** | ⚠️ Below Target |
| **p95 Latency** | **~4.5s** | **<2.0s** | ⚠️ Below Target |
| **RAGAS Answer Relevancy** | **0.612** | **>0.75** | ⚠️ Below Target |
| **RAGAS Context Recall** | **0.554** | **>0.70** | ⚠️ Below Target |

*Note: All current metrics are derived from the baseline evaluation dataset of 25 pairs.*

---

## 🛠️ Feature Breakdown

### What Currently Works (Implemented)
- **Local PDF Ingestion:** Text parsing using PyMuPDF and Sentence-Window chunking fallback.
- **Vector Storage:** Qdrant vector database integration (local database folder fallback).
- **Core Retrieval Engine:** Basic bi-encoder search with Cached Embeddings and HyDE query transformations.
- **LLM Generation:** Local Mistral-7B-Instruct execution via Ollama.
- **FastAPI Endpoints:** Complete set of secure endpoints with exception shields, robust CORS configurations, and active service health checks.
- **Test Suite:** Comprehensive unit and integration testing infrastructure with mocked external calls.

### What is Missing / WIP (To Be Implemented)
- **RAGAS Pipeline Integration:** Programmatic RAGAS evaluator and MLflow telemetry logging.
- **Hybrid Retrieval & Reranking:** BM25 integration with Reciprocal Rank Fusion (RRF) and Cross-Encoder rerankers.
- **Performance & Async Processing:** Async query endpoints, Server-Sent Events (SSE) token streaming, and connection pooling.
- **Production Hardening:** Docker containerization, cloud deployment (Fly.io/AWS), API key validation, and rate-limiting.

---

## 🗺️ Project Roadmap

Our phased 90-day execution plan covers:
- **Phase 1 (Week 1-2):** Foundation & Honesty *(Completed / Current)*
- **Phase 2 (Week 3-4):** RAG Quality (Evaluation & Hybrid Retrieval)
- **Phase 3 (Week 5-6):** Performance & Async Refactoring
- **Phase 4 (Week 7-8):** Containerization & Production Deployment
- **Phase 5 (Week 9-10):** Community, Blog Post & Profile Polish
- **Phase 6 (Week 11-12):** Edge Cases, Robustness & Final Polish

See [ROADMAP.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/ROADMAP.md) for detailed task items.

---

## 📖 Additional Documentation

For deep dives into the technical details and contribution guidelines:
- 🏗️ **Architecture Details:** See [architecture.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/docs/architecture.md) for current state components.
- 📐 **Evaluation Framework:** See [evaluation.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/docs/evaluation.md) for details on dataset and RAGAS integrations.
- 🤝 **Contributing Guide:** See [CONTRIBUTING.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/CONTRIBUTING.md) to set up your local development environment and run tests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](file:///Users/adib/Desktop/industrial-rag-assistant-main/LICENSE) file for details.
