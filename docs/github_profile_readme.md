# 👋 Hi, I'm Adib Azam Shaikh

### 🚀 BSc Computer Science | AI/ML Engineer | Building Production RAG Systems
*Targeting Winter 2029 Germany Master's in Computer Science & Autonomous Systems*

---

## 🛠️ Featured Project

### [🏗️ Industrial RAG Knowledge Assistant](https://github.com/shaikhadibbb/industrial-rag-assistant)
> A production-hardened, memory-optimized Retrieval-Augmented Generation (RAG) system engineered for complex industrial maintenance manuals.

```
⚡ 0.724 RAGAS Faithfulness | 📊 p95 1.85s Latency | 🐳 Deployed Staging API (Live)
```

* **The Rescue Story:** I faced a classic *"works on my machine"* problem: my RAG prototype ran locally with Ollama but crashed instantly on Render's 512MB RAM free tier. Over 90 days, I re-engineered the pipeline—swapping PyTorch for **FastEmbed ONNX Runtime** (shrinking RAM from 600MB to <80MB), implementing **BM25 + Dense Hybrid Retrieval** via Reciprocal Rank Fusion (RRF), writing custom asynchronous FastAPI handlers with SSE Token Streaming, and building a comprehensive Prometheus + Grafana telemetry stack.
* **Key Achievements:**
  * Boosted RAGAS Faithfulness from **0.583 to 0.724** and Context Recall from **0.554 to 0.712**.
  * Optimized latency down to **p95 ~1.85 seconds** (using custom LRU-TTL embedding and query caches).
  * 100% strict type safety (`mypy --strict`), automated security scanning (`bandit` + `pip-audit`), and green GitHub CI gates.

👉 **Explore the code:** [shaikhadibbb/industrial-rag-assistant](https://github.com/shaikhadibbb/industrial-rag-assistant)
👉 **Read the deep-dive:** [How I Rescued a RAG Assistant from Memory Leaks (Dev.to)](https://dev.to/shaikhadibbb/how-i-rescued-a-rag-assistant-from-memory-leaks-and-got-it-running-on-a-512mb-ram-free-tier-4co9)

---

## 💻 Tech Stack & Tooling

* **Languages:** Python (Strict Typing), SQL, Shell Scripting, C++
* **AI & Retrieval:** LlamaIndex, Qdrant Vector DB, FastEmbed (ONNX), Cross-Encoders, BM25 Lexical Search, RAGAS Evaluations
* **Backend & API:** FastAPI (Async/SSE), Uvicorn, Nginx, Gunicorn
* **DevOps & Infrastructure:** Docker, Docker Compose, Prometheus, Grafana, GitHub Actions (CI/CD), Render, Git/DVC (Data Version Control)
* **Testing & Quality:** Pytest, pytest-cov, Hypothesis (Property-Based Testing), MyPy, Ruff, Bandit, Pip-Audit

---

## 📝 Recent Technical Writing

* 📝 [How I Rescued a RAG Assistant from Memory Leaks and Got it Running on a 512MB RAM Free Tier](https://dev.to/shaikhadibbb/how-i-rescued-a-rag-assistant-from-memory-leaks-and-got-it-running-on-a-512mb-ram-free-tier-4co9)
* 📐 [Programmatic Evaluation of RAG pipelines using RAGAS and MLflow Telemetry](https://dev.to/shaikhadibbb/) *(Forthcoming)*

---

## 📊 GitHub Metrics & Statistics

<div align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=shaikhadibbb&show_icons=true&theme=nord&count_private=true" alt="Adib's GitHub Stats" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=shaikhadibbb&layout=compact&theme=nord" alt="Top Languages" />
</div>

---

## 📫 How to Reach Me

* **LinkedIn:** [linkedin.com/in/shaikhadibbb](https://linkedin.com)
* **Email:** [adib.azam.shaikh@example.com](mailto:adib.azam.shaikh@example.com)
* **Portfolio Site:** [shaikhadib.dev](https://shaikhadib.dev)
