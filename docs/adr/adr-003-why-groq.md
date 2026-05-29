# ADR 003: Choice of LLM Generation Layer (Groq Serverless vs. Local Ollama)

## Context & Problem Statement

In the initial prototype, we used **Ollama** running a local `mistral:7b-instruct` model. While this worked excellently on high-end local development machines (with dedicated GPUs), transitioning this setup to cloud staging introduced severe blockers:
1.  **Staging RAM Constraints**: Render's free tier imposes a strict **512MB RAM** ceiling. Loading a 7B parameter model (which requires ~4.5GB of RAM) is physically impossible and results in immediate Out-Of-Memory (OOM) kernel terminations.
2.  **Staging GPU Limitations**: Affordable staging servers do not provide CUDA GPUs. Running 7B models on standard virtualized CPUs results in disastrous generation speeds, with token generation latencies exceeding **20 to 45 seconds** per query.
3.  **Required Metrics**: Our target p95 latency must be **< 2.0s** with cached configurations, and standard generation must remain highly responsive.

We evaluated two approaches for production staging: **Local CPU-based Ollama** and **Groq Serverless API**.

---

## Decision Drivers

*   **Memory Footprint**: The LLM client must not consume server RAM.
*   **Token Generation Latency**: p95 target must be below 2 seconds.
*   **Cost**: Staging must remain free or extremely low-cost.
*   **Model Performance**: The LLM must support structured system prompts, follow guidelines, and perform high-quality generation.

---

## Comparative Analysis

| Feature | Local Ollama (CPU Staging) | Groq Serverless API |
| :--- | :--- | :--- |
| **RAM Footprint** | ~4.5GB (Crashes 512MB environment) | **~0MB** (Offloaded to cloud API) |
| **p95 Generation Latency** | >25 seconds (Unusable CPU inference) | **~0.3s to 0.8s** (LPU ultra-fast inference) |
| **Hosting Cost** | Requires high-end VM ($40+/month) | Free tier (Generous rate limits) |
| **Model Availability** | Limited to small/quantized models (e.g. 1B) | Top-tier models (e.g. `llama3-8b-8192`) |
| **API Compliance** | OpenAI compatible | OpenAI compatible |

---

## Decision

We migrated our production LLM generation layer from local Ollama CPU models to the **Groq Serverless API** utilizing the `llama3-8b-8192` model, while keeping Ollama as a local-only developer toggle.

---

## Consequences

### Positive
*   **Render Deployment Success**: Our memory footprint in production stayed under **120MB**, representing a 75% margin below the 512MB limit, ensuring absolute stability.
*   **Stunning Latency (p95: 1.85s)**: By leveraging Groq LPUs, token streaming starts within 150ms of a query, and standard responses finish in under a second (even when cache misses occur).
*   **No Downgrade in Intelligence**: Instead of being forced to run an inaccurate 1B parameter model locally on CPU, we can query high-performing models (`llama-3.1-8b-instant` or similar) to ensure high RAGAS Faithfulness (0.724).
*   **SSE Token Streaming**: Integrated FastAPI's async SSE handlers natively with Groq's async stream client.

### Negative / Trade-Offs
*   **API Dependency**: We rely on an external API, which introduces networking failures as a risk. We mitigated this by building custom API exception handlers and failover response structures in `src/generation/llm_client.py`.
*   **Rate Limits**: Free-tier Groq API has request-per-minute limits. We implemented a thread-safe sliding-window rate-limiter (10 req/min) on our FastAPI routes to safeguard API token budgets and avoid `429 Too Many Requests` errors.
