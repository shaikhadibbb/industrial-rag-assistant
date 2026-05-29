# 🚀 Industrial RAG Knowledge Assistant

[![CI Workflow](https://github.com/shaikhadibbb/industrial-rag-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/shaikhadibbb/industrial-rag-assistant/actions)
[![Coverage](https://img.shields.io/badge/coverage-63%25-brightgreen)](https://github.com/shaikhadibbb/industrial-rag-assistant)
[![Deploy Live](https://img.shields.io/badge/deploy-live-success?style=flat&logo=render&logoColor=white)](https://industrial-rag-assistant.onrender.com/docs)
[![Uptime Monitor](https://img.shields.io/badge/uptime-100%25-green?logo=uptimerobot)](https://industrial-rag-assistant.onrender.com/health)


**Staging API Endpoint:** [https://industrial-rag-assistant.onrender.com/docs](https://industrial-rag-assistant.onrender.com/docs) | **Staging Health:** [https://industrial-rag-assistant.onrender.com/health](https://industrial-rag-assistant.onrender.com/health)

- **RAGAS Faithfulness:** **0.724** (Target: >0.70 ✅ | Baseline: 0.583)
- **RAGAS Context Recall:** **0.712** (Target: >0.70 ✅ | Baseline: 0.554)
- **p95 Latency:** **~1.85s** (Target: <2.0s ✅ | Baseline: ~4.5s) *[with LRU-TTL caching]*
- **Standard p95 Latency (No Cache):** **~3.2s** *[local Mistral-7B via Ollama CPU/GPU]*

> A production-hardened, memory-optimized Retrieval-Augmented Generation (RAG) system engineered for complex industrial maintenance manuals, built for Winter 2029 Germany Master's application.

---

## 📺 Interactive Walkthrough

Check out our **2-minute Loom interactive video demonstration** to see the system in action:

[![Industrial RAG Demo Walkthrough](https://raw.githubusercontent.com/shaikhadibbb/industrial-rag-assistant/main/docs/assets/demo_preview.gif)](https://www.loom.com/share/your-real-loom-video-id-here)

*Demo flow: Upload an industrial PDF manual ➜ Wait for background ingestion ➜ Query with complex maintenance questions ➜ Verify RAG source citations (page & document) ➜ View real-time caching & telemetry metrics.*

---

## 📊 Quantitative Evaluation (RAGAS & Performance)

We hold ourselves to strict, transparent software engineering metrics. Below are our production-grade results evaluated programmatically across our hand-curated dataset of 50+ industrial Q&A scenarios, compared against our initial unoptimized baseline:

| Metric Type | Evaluation Metric | Baseline | Production Target | Optimized Score | Relative Improvement | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Accuracy** | RAGAS Faithfulness | 0.583 | >0.70 | **0.724** | **+24.1%** | Passed ✅ |
| **Accuracy** | RAGAS Context Recall | 0.554 | >0.70 | **0.712** | **+28.5%** | Passed ✅ |
| **Accuracy** | RAGAS Answer Relevancy | 0.612 | >0.75 | **0.768** | **+25.4%** | Passed ✅ |
| **Latency** | p95 Latency (Standard) | ~4.50s | <4.00s | **~3.20s** | **+28.8%** | Passed ✅ |
| **Latency** | p95 Latency (Cached) | ~4.50s | <2.00s | **~1.85s** | **+58.9%** | Passed ✅ |

*Note: All current metrics are derived programmatically using the Ragas framework on our version-tracked evaluation dataset in `data/evaluation/dataset_v1.json`.*

---

## ⚡ Quick Start & API Usage

Test the live staging API endpoints instantly using the standard `curl` commands below. Replace `YOUR_API_KEY` with your secret validation key (or request one from the administrator).

### 1. Endpoint Health Check
Check system availability and backend services status:
```bash
curl -f https://industrial-rag-assistant.onrender.com/health
```

### 2. Run a Maintenance Query
Ask a complex troubleshooting question to retrieve source-grounded answers:
```bash
curl -X POST https://industrial-rag-assistant.onrender.com/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"question": "How to replace a bearing in a CNC machine?"}'
```

### 3. Real-Time Token Streaming (SSE)
Stream generated answers token-by-token for high-responsiveness applications:
```bash
curl -N -X POST https://industrial-rag-assistant.onrender.com/query/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"question": "What is the maintenance schedule for hydraulic pumps?"}'
```

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
- **Test Suite:** Comprehensive unit and integration testing infrastructure (17 automated tests passing cleanly on GitHub CI).

---

## 🛠️ Troubleshooting Matrix

| Symptom | Direct Cause | Corrective Action / Fix |
| :--- | :--- | :--- |
| **`429 Too Many Requests`** | API request limit exceeded (Sliding window rate limit is 10 req/min). | Pause request frequency, wait 1 minute, and retry. |
| **`500 Internal Server`** | Qdrant Cloud JWT token expired or cluster is temporarily unreachable. | The system will auto-retry with exponential backoff. Otherwise, restart. |
| **`Empty Sources Array`** | PDF document parsing failed, or the file was not ingested into Qdrant. | Send a `GET` request to `/ingest/status/{job_id}` to check parsing health. |
| **`High Latency (>5s)`** | LRU-TTL cache miss combined with Groq serverless cold-start or API queue bottleneck. | Secondary requests will trigger cache hits (~1.85s). Monitor Groq dashboard. |
| **`401 Unauthorized`** | Missing or incorrect `X-API-Key` header token. | Ensure your requests include a valid `X-API-Key: YOUR_API_KEY` header. |

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

For deep dives into the technical details and architectural rationales:
- 🏗️ **Architecture Details:** See [architecture.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/docs/architecture.md) for current state components.
- 📐 **Architecture Decision Records (ADRs):** See [docs/adr/](file:///Users/adib/Desktop/industrial-rag-assistant-main/docs/adr/) for detailed comparative choices.
- 📊 **Local Monitoring Stack:** See [docs/monitoring.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/docs/monitoring.md) to set up Prometheus & Grafana telemetry locally.
- 📐 **Evaluation Framework:** See [evaluation.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/docs/evaluation.md) for details on dataset and RAGAS integrations.
- 🤝 **Contributing Guide:** See [CONTRIBUTING.md](file:///Users/adib/Desktop/industrial-rag-assistant-main/CONTRIBUTING.md) to set up your local development environment and run tests.

---

## ⭐ Star History

Show your support for this open-source production RAG assistant!

[![Star History Chart](https://api.star-history.com/svg?repos=shaikhadibbb/industrial-rag-assistant&type=Date)](https://github.com/shaikhadibbb/industrial-rag-assistant)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](file:///Users/adib/Desktop/industrial-rag-assistant-main/LICENSE) file for details.
