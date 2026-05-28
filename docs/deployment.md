# Render.com Deployment Guide

This guide deploys the **Industrial RAG Assistant** (FastAPI + Qdrant + Ollama) to [Render.com](https://render.com) — no credit card required.

---

## Architecture on Render

```
Internet → Render Web Service (FastAPI/Docker)
                 ↓
         Qdrant Cloud (free tier) — vector storage
         Ollama API (external or Render private service)
```

Since Render's free tier gives you **1 web service** with **512 MB RAM**, we use:
- **Qdrant Cloud** (free 1GB cluster) for vector storage
- The app's **local Qdrant fallback** (`./qdrant_data`) for demo deployments

---

## Step 1: Push to GitHub

```bash
git add .
git commit -m "feat: add Render deployment config"
git push origin main
```

---

## Step 2: Create a Free Qdrant Cloud Cluster

1. Go to → **https://cloud.qdrant.io** → Sign up (free, no card)
2. Create a **Free** cluster (1 GB, region: `us-east-1` or `eu-west`)
3. Copy your:
   - **Cluster URL**: `https://xxxx.us-east.aws.cloud.qdrant.io`
   - **API Key** (from the dashboard → API Keys tab)

---

## Step 3: Deploy on Render

### 3a. Create a New Web Service

1. Go to → **https://dashboard.render.com** → **New → Web Service**
2. Connect your GitHub repository: `industrial-rag-assistant`
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `industrial-rag-assistant` |
| **Runtime** | `Docker` |
| **Dockerfile Path** | `./Dockerfile` |
| **Instance Type** | `Free` |
| **Health Check Path** | `/health` |

### 3b. Set Environment Variables

In the Render dashboard → **Environment** tab, add:

| Key | Value |
|-----|-------|
| `API_KEY` | Generate a strong key: `openssl rand -hex 32` |
| `QDRANT_HOST` | Your Qdrant Cloud URL (without `https://`) |
| `QDRANT_PORT` | `6333` |
| `QDRANT_API_KEY` | Your Qdrant Cloud API key |
| `OLLAMA_BASE_URL` | Your Ollama endpoint (see note below) |
| `ALLOWED_ORIGINS` | `*` (or your frontend URL) |
| `PYTHONUNBUFFERED` | `1` |

> **Note on Ollama**: Render free tier cannot run Ollama (requires GPU/high RAM).
> Options:
> - Use [Groq API](https://groq.com) (free, fast) — see `src/generation/llm_client.py`
> - Run Ollama locally and expose via [ngrok](https://ngrok.com) for testing
> - Use a [Modal.com](https://modal.com) Ollama endpoint (free credits)

### 3c. Deploy

Click **Create Web Service**. Render will:
1. Pull your GitHub repo
2. Build the Docker image
3. Run health checks on `/health`
4. Give you a public URL: `https://industrial-rag-assistant.onrender.com`

---

## Step 4: Verify Deployment

```bash
# Health check
curl https://industrial-rag-assistant.onrender.com/health

# Expected (services degraded if Ollama not configured):
# {"status": "degraded", "qdrant": "connected", "ollama": "disconnected: ..."}

# Test query (replace YOUR_API_KEY)
curl -X POST https://industrial-rag-assistant.onrender.com/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{"question": "What are the maintenance intervals for the compressor?"}'
```

---

## Step 5: Ingest Documents

```bash
curl -X POST https://industrial-rag-assistant.onrender.com/ingest \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@data/raw/your_manual.pdf"
```

---

## Local Development with Docker Compose

For full local stack (Qdrant + Ollama + FastAPI):

```bash
# Start all services
docker-compose up --build

# Pull Ollama model (run once)
docker exec -it ollama_prod ollama pull mistral:7b-instruct

# Test locally
curl http://localhost/health
```

---

## Render Deployment Checklist

- [ ] `render.yaml` committed to repo root
- [ ] GitHub repo connected to Render
- [ ] `API_KEY` set in Render environment vars
- [ ] `QDRANT_HOST` set to Qdrant Cloud URL
- [ ] Health check path set to `/health`
- [ ] Deployment successful (green status in dashboard)
- [ ] `/health` endpoint returns 200 OK

---

## Cost Summary

| Service | Tier | Cost |
|---------|------|------|
| Render Web Service | Free | $0/month |
| Qdrant Cloud | Free (1GB) | $0/month |
| Groq LLM API | Free (rate limited) | $0/month |
| **Total** | | **$0/month** |
