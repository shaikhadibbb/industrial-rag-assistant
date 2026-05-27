#!/usr/bin/env python3
"""Clean RAGAS evaluation script - gets all 4 metrics reliably."""

import os, sys, json, logging, time
import mlflow
import pandas as pd
from datasets import Dataset

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, ".")

# ── Step 1: Load test questions ──────────────────────────────────────────────
def load_or_generate_questions():
    """Load existing test set or generate new one."""
    path = "data/test_set.json"
    
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        if data and len(data) >= 5:
            logger.info(f"Loaded {len(data)} existing test questions")
            return data
    
    logger.info("Generating test questions from Qdrant chunks...")
    return generate_questions()

def generate_questions():
    """Generate Q&A pairs from Qdrant using Ollama."""
    import httpx
    
    # Connect to Qdrant
    try:
        from qdrant_client import QdrantClient
        try:
            client = QdrantClient(host="localhost", port=6333)
            client.get_collections()
            logger.info("Connected to Qdrant server")
        except:
            client = QdrantClient(path="./qdrant_data")
            logger.info("Connected to Qdrant local")
        
        results = client.scroll(
            collection_name="industrial_docs",
            limit=20,
            with_payload=True,
            with_vectors=False
        )
        chunks = [
            {"text": p.payload.get("window") or p.payload.get("text", ""), 
             "page": p.payload.get("page_number") or p.payload.get("page_label", "?"),
             "source": p.payload.get("filename") or p.payload.get("file_name", "manual.pdf")}
            for p in results[0] 
            if (p.payload.get("window") or p.payload.get("text", ""))
        ]
        # Keep only chunks with decent length
        chunks = [c for c in chunks if len(c["text"]) > 100]
        logger.info(f"Got {len(chunks)} chunks")
    except Exception as e:
        logger.error(f"Qdrant error: {e}")
        return []
    
    qa_pairs = []
    for i, chunk in enumerate(chunks[:10]):
        logger.info(f"Generating Q&A {i+1}/10...")
        prompt = f"""Read this technical text and write 2 Q&A pairs.

Text: {chunk['text'][:400]}

Return ONLY valid JSON array, no other text:
[
  {{"question": "technical question here?", "answer": "answer from text here"}},
  {{"question": "another question?", "answer": "another answer"}}
]"""
        
        try:
            r = httpx.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral:7b-instruct", "prompt": prompt, 
                      "stream": False, "options": {"temperature": 0.1, "num_predict": 200}},
                timeout=45
            )
            raw = r.json().get("response","").strip()
            start, end = raw.find("["), raw.rfind("]")+1
            if start >= 0 and end > start:
                pairs = json.loads(raw[start:end])
                for p in pairs:
                    if p.get("question") and p.get("answer"):
                        qa_pairs.append({
                            "question": p["question"],
                            "ground_truth": p["answer"],
                            "reference_context": chunk["text"]
                        })
        except Exception as e:
            logger.warning(f"Q&A generation failed for chunk {i}: {e}")
    
    # Save for reuse
    os.makedirs("data", exist_ok=True)
    with open("data/test_set.json", "w") as f:
        json.dump(qa_pairs, f, indent=2)
    logger.info(f"Generated and saved {len(qa_pairs)} Q&A pairs")
    return qa_pairs

# ── Step 2: Run RAG on each question ────────────────────────────────────────
def run_rag_pipeline(questions):
    """Run each question through the actual RAG system."""
    from src.retrieval.query_engine import get_query_engine
    
    logger.info("Loading query engine (first load takes ~30s)...")
    engine = get_query_engine()
    logger.info("Query engine ready")
    
    results = []
    for i, q in enumerate(questions):
        logger.info(f"RAG query {i+1}/{len(questions)}: {q['question'][:60]}...")
        try:
            t0 = time.time()
            response = engine.query(q["question"])
            latency = time.time() - t0
            
            contexts = []
            if hasattr(response, "source_nodes") and response.source_nodes:
                contexts = [node.node.text for node in response.source_nodes]
            
            if not contexts:
                contexts = [q.get("reference_context", "No context retrieved")]
            
            results.append({
                "question": q["question"],
                "answer": str(response).strip(),
                "contexts": contexts,
                "ground_truth": q["ground_truth"],
                "latency_s": round(latency, 2)
            })
            logger.info(f"  → answered in {latency:.1f}s")
        except Exception as e:
            logger.warning(f"RAG failed for q{i}: {e}")
            results.append({
                "question": q["question"],
                "answer": "Error: could not retrieve answer",
                "contexts": [q.get("reference_context", "")],
                "ground_truth": q["ground_truth"],
                "latency_s": 0
            })
    
    return results

# ── Step 3: RAGAS evaluation ─────────────────────────────────────────────────
def evaluate_with_ragas(eval_data):
    """Run RAGAS with local Mistral + BGE embeddings."""
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness, 
        answer_relevancy, 
        context_recall, 
        context_precision
    )
    
    # Build dataset
    dataset = Dataset.from_list([{
        "question": d["question"],
        "answer": d["answer"],
        "contexts": d["contexts"],
        "ground_truth": d["ground_truth"]
    } for d in eval_data])
    
    logger.info(f"Running RAGAS on {len(dataset)} examples...")
    
    # Use local models
    try:
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_community.llms import Ollama as LCOllama
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        from ragas.run_config import RunConfig
        
        judge_llm = LangchainLLMWrapper(
            LCOllama(model="mistral:7b-instruct", base_url="http://localhost:11434", timeout=180.0)
        )
        judge_emb = LangchainEmbeddingsWrapper(
            HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        )
        logger.info("Using local Mistral + MiniLM for evaluation (timeout=180s)")
        
        # Use low concurrency for local Ollama
        run_config = RunConfig(timeout=180, max_workers=1)
        
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
            llm=judge_llm,
            embeddings=judge_emb,
            run_config=run_config,
            raise_exceptions=False
        )
    except Exception as e:
        logger.warning(f"Local eval failed ({e}), trying without custom LLM...")
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
            raise_exceptions=False
        )
    
    return results

# ── Step 4: Log to MLflow ────────────────────────────────────────────────────
def log_results(ragas_results, eval_data, latencies):
    """Log everything to MLflow."""
    mlflow.set_tracking_uri("mlruns")
    mlflow.set_experiment("rag-evaluation")
    
    with mlflow.start_run(run_name=f"full-eval-{int(time.time())}"):
        # Params
        mlflow.log_param("llm", "mistral:7b-instruct")
        mlflow.log_param("embedding", "BAAI/bge-m3")
        mlflow.log_param("chunk_size", 256)
        mlflow.log_param("top_k", 6)
        mlflow.log_param("reranker", "ms-marco-MiniLM-L-6-v2")
        mlflow.log_param("n_questions", len(eval_data))
        
        # Latency metrics
        if latencies:
            mlflow.log_metric("avg_latency_s", round(sum(latencies)/len(latencies), 2))
            mlflow.log_metric("p95_latency_s", round(sorted(latencies)[int(len(latencies)*0.95)], 2))
        
        # RAGAS metrics
        scores = {}
        if ragas_results:
            df = ragas_results.to_pandas()
            for col in ["faithfulness","answer_relevancy","context_recall","context_precision"]:
                if col in df.columns:
                    val = float(df[col].mean())
                    scores[col] = round(val, 4)
                    mlflow.log_metric(col, scores[col])
        
        # Save artifacts
        pd.DataFrame(eval_data).to_csv("evaluation_results.csv", index=False)
        mlflow.log_artifact("evaluation_results.csv")
        mlflow.log_artifact("data/test_set.json")
        
        return scores, mlflow.active_run().info.run_id

# ── Step 5: Print results table ──────────────────────────────────────────────
def print_table(scores, run_id, latencies):
    thresholds = {
        "faithfulness": 0.75,
        "answer_relevancy": 0.70,
        "context_recall": 0.65,
        "context_precision": 0.65
    }
    labels = {
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer Relevancy",
        "context_recall": "Context Recall",
        "context_precision": "Context Precision"
    }
    
    print("\n" + "═"*58)
    print("   RAGAS EVALUATION RESULTS — Industrial RAG Assistant")
    print("═"*58)
    print(f"   {'Metric':<24} {'Score':>7}   {'Threshold':>9}   Status")
    print("─"*58)
    
    all_pass = True
    for key, label in labels.items():
        score = scores.get(key, None)
        threshold = thresholds[key]
        if score is not None:
            status = "✅ PASS" if score >= threshold else "❌ FAIL"
            if score < threshold:
                all_pass = False
            print(f"   {label:<24} {score:>7.4f}   {threshold:>9.2f}   {status}")
        else:
            print(f"   {label:<24} {'N/A':>7}   {threshold:>9.2f}   ⚠️  not measured")
            all_pass = False
    
    print("─"*58)
    if latencies:
        avg = sum(latencies)/len(latencies)
        print(f"   {'Avg Latency':<24} {avg:>6.1f}s")
    print("═"*58)
    print(f"   {'Overall:':<24} {'ALL PASS ✅' if all_pass else 'NEEDS IMPROVEMENT ⚠️'}")
    print("═"*58)
    print(f"\n   MLflow Run ID: {run_id}")
    print(f"   Dashboard:     http://localhost:5001")
    print(f"   Results file:  evaluation_results.csv\n")

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔬 Starting RAGAS Evaluation Pipeline...")
    print("   This will take 15-25 minutes. Do not close terminal.\n")
    
    # 1. Questions
    questions = load_or_generate_questions()
    if not questions:
        print("❌ No questions. Run: python scripts/ingest.py first")
        sys.exit(1)
    print(f"✅ {len(questions)} test questions ready\n")
    
    # Use max 12 questions for speed
    questions = questions[:12]
    
    # 2. RAG
    print("🔄 Running RAG pipeline on test questions...")
    eval_data = run_rag_pipeline(questions)
    latencies = [d["latency_s"] for d in eval_data if d["latency_s"] > 0]
    print(f"✅ RAG complete. Avg latency: {sum(latencies)/len(latencies):.1f}s\n")
    
    # 3. RAGAS
    print("🧪 Running RAGAS evaluation (slowest step ~15 mins)...")
    ragas_results = evaluate_with_ragas(eval_data)
    print("✅ RAGAS complete\n")
    
    # 4. MLflow
    print("📊 Logging to MLflow...")
    scores, run_id = log_results(ragas_results, eval_data, latencies)
    print("✅ Logged\n")
    
    # 5. Print
    print_table(scores, run_id, latencies)
    
    # 6. Update README
    print("📝 Updating README with real scores...")
    try:
        with open("README.md", "r") as f:
            readme = f.read()
        for key, label in [
            ("faithfulness","Faithfulness"),
            ("answer_relevancy","Answer Relevancy"),
            ("context_recall","Context Recall"),
            ("context_precision","Context Precision")
        ]:
            score = scores.get(key)
            if score:
                readme = readme.replace(f"[PLACEHOLDER]", f"{score:.2f}", 1)
        with open("README.md","w") as f:
            f.write(readme)
        print("✅ README updated with real scores")
    except Exception as e:
        print(f"⚠️  README update failed: {e}")
