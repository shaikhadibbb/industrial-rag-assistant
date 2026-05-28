# Evaluation Framework

This document details the evaluation methodology, dataset composition, and metrics used to measure the quality of the Industrial RAG Assistant.

---

## 📊 Dataset Composition

Our current baseline evaluation dataset consists of **25 manually curated Q&A pairs** derived from industrial documentation and manual templates. 

In Phase 2, we will expand this to **50+ Q&A pairs** mapped across the following core industrial categories:

| Category | Target Weight | Focus Area |
| :--- | :---: | :--- |
| **Troubleshooting** | **40%** | Diagnostics, fault codes, error resolutions, and repair procedures. |
| **Safety Procedures** | **25%** | LOTO (Lock-Out Tag-Out), emergency shutdowns, protective equipment requirements. |
| **Part Identification** | **20%** | Component names, assembly specifications, and spare parts catalog references. |
| **Maintenance Schedules** | **15%** | Preventative schedules, hourly intervals, lubrication requirements. |

---

## 📐 Metrics Description (RAGAS)

We utilize the **RAGAS** (Retrieval Augmented Generation Assessment) library to compute automated, model-graded metrics.

### 1. Faithfulness (Target: >0.70)
- **Definition:** Measures whether the generated answer is strictly grounded in the retrieved context.
- **Formula:** `Number of statements in answer supported by context / Total number of statements in answer`
- **Why it matters:** In industrial maintenance, hallucinating safety limits or torque specifications can cause physical injury or hardware damage.

### 2. Answer Relevancy (Target: >0.75)
- **Definition:** Assesses whether the generated answer directly addresses the user's question, without containing redundant or irrelevant details.
- **Formula:** Average semantic similarity between the original question and generated potential questions based on the answer.

### 3. Context Recall (Target: >0.70)
- **Definition:** Evaluates whether the retrieved context contains all the necessary ground-truth information required to answer the user's question.
- **Formula:** `Number of ground-truth statements present in retrieved context / Total number of ground-truth statements`

### 4. Context Precision (Target: >0.75)
- **Definition:** Measures whether the highly relevant context chunks are ranked higher in the retrieval results than irrelevant ones.
- **Formula:** Weighted precision calculated at various rank cutoffs.

---

## 🧪 Current Baselines & Target Metrics

| Metric | Current Baseline (v1) | Production Target | Gap |
| :--- | :---: | :---: | :---: |
| Faithfulness | **0.583** | **>0.70** | -0.117 |
| Answer Relevancy | **0.612** | **>0.75** | -0.138 |
| Context Recall | **0.554** | **>0.70** | -0.146 |
| Latency p95 | **~4.5s** | **<2.0s** | +2.5s |
