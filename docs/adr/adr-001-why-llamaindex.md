# ADR 001: Choice of RAG Framework (LlamaIndex vs. LangChain)

## Context & Problem Statement

We need a framework to construct a robust, high-accuracy Retrieval-Augmented Generation (RAG) assistant for complex, long-form industrial maintenance manuals (e.g., CNC machine bearing replacement guides, pump maintenance schedules). 

Industrial manuals contain dense structural features (step-by-step instructions, caution boxes, page references, diagrams). The system must meet strict evaluation requirements:
*   RAGAS Faithfulness: **>0.70**
*   RAGAS Context Recall: **>0.70**
*   Staging RAM budget: **512MB RAM**
*   Execution latency: **p95 < 2.0s**

We evaluated two leading Python LLM frameworks: **LlamaIndex** and **LangChain**.

---

## Decision Drivers

1.  **Data-Centric Abstraction**: The core of a successful industrial RAG pipeline is indexing and parsing, not just chaining LLM calls. The framework must treat documents, chunks, and metadata as first-class objects.
2.  **Sentence-Window Context Enrichment**: The ability to decouple the retrieval chunk (small sentence) from the synthesis chunk (sentence + context window) is crucial for precision and factual accuracy.
3.  **Extensible Post-Retrieval Pipeline**: Easy composition of custom retrievers (BM25 + Dense RRF fusion) and node-postprocessors (deduplication, reranking) without writing verbose custom graph chains.
4.  **Memory footprint**: Minimal overhead and efficient lazy-loading of models.

---

## Comparative Analysis

| Feature | LlamaIndex | LangChain |
| :--- | :--- | :--- |
| **Data Abstraction** | Documents, TextNodes with native parent/child relations. | Generic Document dict schemas. |
| **RAG Specialization** | Built specifically for search, query, and indexing. | General-purpose LLM application orchestration. |
| **Parsing & Chunking** | Native hierarchical chunkers (Sentence-Window, Node parsers). | Basic text splitters; requires custom code for hierarchy. |
| **Postprocessors** | Highly modular `NodePostprocessor` hook ecosystem. | Requires building custom LCEL (LangChain Expression Language) chains. |
| **Query Engine** | Out-of-the-box streaming, caching, and source tracking. | Highly manual source-verification assembly. |

---

## Decision

We chose **LlamaIndex** as our core orchestration framework.

---

## Consequences

### Positive
*   **Factual Faithfulness (RAGAS: 0.724)**: Enabled us to implement the `Sentence-Window Chunker` natively. The model retrieves tiny, highly specific sentences (minimizing noise) but feeds the LLM the larger context (maximizing comprehension), satisfying our precision goals.
*   **Modular Pipeline**: Postprocessors like our custom similarity-based `DeduplicationPostprocessor` and cross-encoder `CrossEncoderReranker` fit cleanly into LlamaIndex's `QueryEngine` pipeline via the `node_postprocessors` hook.
*   **Structured Metadata**: Ingestion parsed files into rich nodes preserving metadata (filename, page numbers), which are passed directly to the frontend to ensure 100% auditable sources.

### Negative / Trade-Offs
*   **Library Maturity**: LlamaIndex's transition to Pydantic v2 has introduced library-level bugs (e.g., `ValidationError` in embedding wrappers). We resolved this via dynamic runtime monkeypatching inside our embedder layer.
*   **Integration Limits**: Integrating external evaluation libraries like Ragas required custom extraction logic since the direct integration wrappers were occasionally unstable. We bypassed this by extracting raw prompt responses programmatically.
