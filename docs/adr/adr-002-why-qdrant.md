# ADR 002: Choice of Vector Database (Qdrant vs. Pinecone & Weaviate)

## Context & Problem Statement

We require a vector database to store and query highly dimensional vector embeddings generated from chunked industrial maintenance manuals (using the `BAAI/bge-small-en-v1.5` dense model). 

To support industrial maintenance queries, retrieval must be:
1.  **Parity Between Environments**: Work seamlessly both in local development (offline local fallback) and in cloud staging (remote managed service).
2.  **Rich Metadata Filtering**: Support strict filtering of queries by `document_name` or `page_number` using payload keys without degrading search performance.
3.  **Low Latency**: Keep vector query times down to millisecond ranges under high concurrency.
4.  **Resource Constraints**: Ensure the production staging client requires minimal RAM and does not crash the 512MB RAM server limit.

We evaluated three candidate vector stores: **Qdrant**, **Pinecone**, and **Weaviate**.

---

## Decision Drivers

*   **Offline Development Capabilities**: Crucial for developers working without constant internet or when executing automated unit/integration tests offline.
*   **Rust-backed Speed & Memory Safety**: Maximum performance with low compute footprints.
*   **Payload Filtering Engine**: Native ability to filter vectors using complex boolean expressions on JSON-like payloads.
*   **API Quality and Client Support**: Clean Python SDK with full async support and robust retry mechanics.

---

## Comparative Analysis

| Criteria | Qdrant | Pinecone | Weaviate |
| :--- | :--- | :--- | :--- |
| **Deployment Model** | Open-source, Docker, Local Folder, Cloud | SaaS Only (No Local Docker/Folder) | Open-source, Docker, Cloud |
| **Language & Engine** | Rust (High-performance, low RAM) | Proprietary C++ | Go (Higher RAM footprint) |
| **Local Offline Mode** | Yes (via local disk storage `./qdrant_data`) | No (Requires cloud account & API keys) | Yes (via Docker) |
| **Async Python Client** | Yes (`AsyncQdrantClient` with pooled connection) | Yes (but less mature async wrappers) | Yes (version 4.x+) |
| **Payload Filtering** | Exceptional (JSON match/range indexing) | Metadata key-value (limited types) | Rich (GraphQL-style, complex) |

---

## Decision

We chose **Qdrant** as our core Vector Database.

---

## Consequences

### Positive
*   **Zero-Cost Local Fallback**: Developers can launch the system using a local storage directory (`./qdrant_data`) with zero configuration, while production staging uses Qdrant Cloud. This is highly beneficial for CI/CD unit testing where cloud connections are blocked.
*   **Production Robustness**: Implemented a **5-step Exponential Backoff Retry** mechanism inside our db connection initialization to handle occasional cloud networking drops gracefully.
*   **Complex Filtering**: Enabled our BM25 and dense bi-encoder to extract vectors belonging only to specific document classes by combining `Filter` clauses on ingestion jobs.
*   **Ultra-low Overhead**: The Qdrant remote python client has negligible memory overhead, keeping our FastAPI instance running far below the 512MB RAM ceiling.

### Negative / Trade-Offs
*   **Index Management**: We must manually manage vector dimension configurations (384 dimensions for `bge-small-en-v1.5`) and distance metrics (Cosine similarity) upon collection creation. This requires robust setup checks inside `src/retrieval/vector_store.py`.
