# REST API Specification & Examples

This document outlines the API endpoints, schemas, authentication, rate limits, and `curl` examples for interacting with the production-grade Industrial RAG Assistant API.

---

## 🔒 Authentication & Rate Limiting

All endpoints except **Health** (`/health`) and **Metrics** (`/metrics`) are secured.

### 1. API Key Authentication
Pass your API key in the `X-API-Key` header of every request:
```http
X-API-Key: your_secure_api_key_here
```
If the header is missing or incorrect, the API returns:
- **Status Code:** `401 Unauthorized`
- **Body:** `{"detail": "Unauthorized: Invalid or missing X-API-Key header."}`

### 2. Rate Limiting (Throttling)
- **Limit:** **10 requests per minute per IP address**.
- When the limit is exceeded, the API blocks the request and returns:
  - **Status Code:** `429 Too Many Requests`
  - **Headers:** Includes a `Retry-After: <seconds>` header telling the client how long to wait before retrying.
  - **Body:** `{"detail": "Too Many Requests: Rate limit exceeded. Try again in 45 seconds."}`

---

## 🚀 API Endpoints

### 1. Health Status (`/health`)
Checks the availability of the FastAPI service, Qdrant database, and Ollama LLM service.
- **Method:** `GET`
- **Authentication:** None (Public)
- **Rate Limit:** Exempt

#### Example Curl:
```bash
curl http://localhost:8000/health
```

#### Response (200 OK):
```json
{
  "status": "healthy",
  "qdrant": "connected",
  "ollama": "connected"
}
```

---

### 2. Query RAG (`/query`)
Executes a natural language query against the loaded PDF manuals. Includes caching, HyDE query expansion, RRF hybrid search, Cross-Encoder reranking, and citation-forced formatting.
- **Method:** `POST`
- **Authentication:** Required (`X-API-Key`)
- **Rate Limit:** Active

#### Request Body Schema:
| Field | Type | Required | Description |
| :--- | :---: | :---: | :--- |
| `question` | `string` | **Yes** | The maintenance question to ask the RAG engine. |
| `session_id` | `string` | No | Optional identifier to track user sessions. |

#### Example Curl:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rag_default_secret_key_2026" \
  -d '{"question": "What is the consequence of internal corrosion in a compressed air receiver vessel?"}'
```

#### Response (200 OK):
```json
{
  "answer": "Internal corrosion in a compressed air receiver vessel poses a serious safety hazard. It can result in a sudden burst, which shares physical characteristics with an explosion. This creates a severe risk of bodily injury to nearby personnel and catastrophic damage to installations. Draining internal condensing water every 8 hours or at least once daily is required to prevent this corrosion (page 2).",
  "sources": [
    {
      "filename": "compressor_manual.pdf",
      "page": "2",
      "score": 0.8924,
      "text_preview": "A corroded vessel can result in a sudden burst, which in cases has similarities to an explosion. There is serious risk for people injury..."
    }
  ],
  "latency_ms": 142.15
}
```

---

### 3. Stream Query Token Flow (`/query/stream`)
Streams generated answer tokens in real-time using **Server-Sent Events (SSE)**.
- **Method:** `POST`
- **Authentication:** Required (`X-API-Key`)
- **Rate Limit:** Active
- **Content-Type:** `text/event-stream`

#### Example Curl:
```bash
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: rag_default_secret_key_2026" \
  -d '{"question": "How often must receiver water be drained?"}'
```

#### Event Flow Output:
```http
event: sources
data: [{"filename": "manual.pdf", "page": "2", "score": 0.912, "text_preview": "A frequent draining..."}]

event: token
data: {"token": " Draining"}

event: token
data: {"token": " the"}

event: token
data: {"token": " water"}

event: token
data: {"token": " condensation"}

event: token
data: {"token": " is"}

event: token
data: {"token": " required"}

event: token
data: {"token": " every"}

event: token
data: {"token": " 8"}

event: token
data: {"token": " hours."}

event: end
data: {}
```

---

### 4. Ingest PDF Manual (`/ingest`)
Uploads and queues a PDF manual for asynchronous parsing, chunking, and upsertion to the Qdrant database.
- **Method:** `POST`
- **Authentication:** Required (`X-API-Key`)
- **Rate Limit:** Active
- **Payload:** `multipart/form-data` with `file` field.
- **Limit:** PDF files only, maximum file size of 50MB.

#### Example Curl:
```bash
curl -X POST http://localhost:8000/ingest \
  -H "X-API-Key: rag_default_secret_key_2026" \
  -F "file=@/path/to/compressor_manual.pdf"
```

#### Response (202 Accepted):
```json
{
  "status": "accepted",
  "job_id": "4a123e4d-72ab-4cde-a11b-123456789abc",
  "message": "Ingestion job successfully queued."
}
```

---

### 5. Check Ingestion Job Status (`/ingest/status/{job_id}`)
Checks the current status of an asynchronous background ingestion job.
- **Method:** `GET`
- **Authentication:** Required (`X-API-Key`)
- **Rate Limit:** Active

#### Example Curl:
```bash
curl http://localhost:8000/ingest/status/4a123e4d-72ab-4cde-a11b-123456789abc \
  -H "X-API-Key: rag_default_secret_key_2026"
```

#### Response (200 OK):
- **Pending/Processing:**
  ```json
  {
    "job_id": "4a123e4d-72ab-4cde-a11b-123456789abc",
    "status": "processing"
  }
  ```
- **Success:**
  ```json
  {
    "job_id": "4a123e4d-72ab-4cde-a11b-123456789abc",
    "status": "success"
  }
  ```
- **Failure:**
  ```json
  {
    "job_id": "4a123e4d-72ab-4cde-a11b-123456789abc",
    "status": "failed: Unsupported PDF structure or corrupt file format."
  }
  ```

---

### 6. Prometheus Metrics (`/metrics`)
Exposes live performance metrics in standard Prometheus exposition format. Ideal for integration with Grafana.
- **Method:** `GET`
- **Authentication:** None (Public)
- **Rate Limit:** Exempt

#### Example Curl:
```bash
curl http://localhost:8000/metrics
```

#### Response (200 OK - Text/Plain):
```text
# HELP rag_queries_total Number of queries received
# TYPE rag_queries_total counter
rag_queries_total{endpoint="/query"} 42
rag_queries_total{endpoint="/query/stream"} 12

# HELP rag_errors_total Number of queries resulting in errors
# TYPE rag_errors_total counter
rag_errors_total{error_type="internal_error"} 0
rag_errors_total{error_type="validation_error"} 1

# HELP rag_tokens_generated_total Total generated tokens
# TYPE rag_tokens_generated_total counter
rag_tokens_generated_total 3154

# HELP rag_query_latency_seconds Query latency histogram
# TYPE rag_query_latency_seconds histogram
rag_query_latency_seconds_bucket{le="0.1"} 12
rag_query_latency_seconds_bucket{le="0.5"} 34
rag_query_latency_seconds_bucket{le="1.0"} 41
rag_query_latency_seconds_bucket{le="2.0"} 42
rag_query_latency_seconds_bucket{le="+Inf"} 42
rag_query_latency_seconds_sum 14.285
rag_query_latency_seconds_count 42
```
