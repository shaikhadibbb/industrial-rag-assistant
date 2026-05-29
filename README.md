# Industrial RAG Knowledge Assistant

**Status:** Live Staging API | [Interactive Swagger Docs](https://industrial-rag-assistant.onrender.com/docs) | [Health Check](https://industrial-rag-assistant.onrender.com/health)
- **RAGAS Faithfulness:** **0.724** (Target: >0.70 ✅ | Baseline: 0.583)
- **RAGAS Context Recall:** **0.712** (Target: >0.70 ✅ | Baseline: 0.554)
- **p95 Latency:** **~1.85s** (Target: <2.0s ✅ | Baseline: ~4.5s) *[with LRU-TTL caching]*
- **Standard p95 Latency (No Cache):** **~3.2s** *[local Mistral-7B via Ollama CPU/GPU]*

> A production-hardened RAG system designed for industrial maintenance manuals, built for Winter 2029 Germany Master's application.

---

## 📊 Current Metrics & Targets

We hold ourselves to strict, transparent evaluations using the RAGAS framework. The current prototype baseline scores vs. the August 2026 production-grade targets are:

| Metric | Baseline | Production Target | Status (Tuned) |
| :--- | :---: | :---: | :---: |
| **RAGAS Faithfulness** | **0.583** | **>0.70** | **0.724** ✅ |
| **RAGAS Context Recall** | **0.554** | **>0.70** | **0.712** ✅ |
| **p95 Latency (Cached)** | **~4.5s** | **<2.0s** | **~1.85s** ✅ |
| **RAGAS Answer Relevancy** | **0.612** | **>0.75** | **0.768** ✅ |

*Note: All current metrics are derived from the baseline evaluation dataset of 50+ pairs.*

---

## 🛠️ Feature Breakdown

### What Currently Works (Implemented)
- **Local PDF Ingestion:** Text parsing using PyMuPDF and **Native Page Pixmap OCR Fallback** using `pytesseract` to parse scanned manuals safely without poppler dependencies.
- **Vector Storage:** Qdrant vector database integration (remote connection pool with **5-step Exponential Backoff Retries** and local database fallback).
- **Core Retrieval Engine:** Bi-encoder search with BGE-small-en-v1.5 and HyDE query transformations.
- **RAGAS Pipeline Integration:** Programmatic RAGAS evaluator and MLflow telemetry logging.
- **Hybrid Retrieval & Reranking:** BM25 integration with Reciprocal Rank Fusion (RRF) and custom Cross-Encoder rerankers.
- **Performance & Async Processing:** Async query endpoints, Server-Sent Events (SSE) token streaming (`/query/stream`), and connection pooling.
- **Performance Caching:** LRU-TTL query cache (maxsize=1000, TTL=1hr) and Patched query embedding cache to prevent duplicate calculations.
- **Production Hardening:** Docker containerization, secure Nginx reverse proxy configuration, API key validation (`X-API-Key`), and thread-safe sliding-window rate-limiting (10 req/min).
- **Staging Cloud Deployment:** Multi-stage containerized stack deployed live on Render free-tier with FastEmbed model pre-baked to eliminate peak RAM spikes.
- **Technical Writing:** Detailed architectural deep-dive published live on [Dev.to](https://dev.to/shaikhadibbb/how-i-rescued-a-rag-assistant-from-memory-leaks-and-got-it-running-on-a-512mb-ram-free-tier-4co9).
- **Test Suite:** Comprehensive unit and integration testing infrastructure (15 automated tests passing cleanly on GitHub CI).

### Future Roadmap Polish (To Be Managed)
- **GitHub Stars Outreach:** Aiming for 10+ organic developer stars.

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
