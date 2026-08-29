# Breakwater: Enterprise Multi-Agent Financial Reconciliation Engine

![Google Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Vertex AI](https://img.shields.io/badge/Vertex_AI-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)

**Breakwater** is a multi-agent autonomous reconciliation system built for the **All Things Agentic Hackathon**. 

Given two transaction feeds that should agree but don't (e.g., a bank ledger vs. a payment processor), Breakwater deterministically matches what it can, investigates *why* every mismatch ("break") happened, autonomously fixes the safe ones with a full audit trail, and escalates ambiguous edge cases with a structured risk packet.

## Why This Exists (The Enterprise Problem)
Reconciliation is a real, expensive, high-volume operational chore in finance and FinOps. Today, it is largely manual, slow, and doesn't scale. Breakwater automates the entire loop—not just the matching (a solved problem), but the harder part: reasoning about *why* a break happened, assessing the business risk, and safely resolving it in a way that satisfies compliance auditors.

##  Multi-Agent Architecture
Breakwater uses a hybrid event-driven pipeline, combining high-speed deterministic rules with Google's latest generative AI models via the **Vertex AI GenAI SDK**.

1. **Matcher (Pandas Engine):** Deterministic matching on ID, amount, and timestamp. Clears the easy 90%+ volume instantly for free.
2. **Investigator & Resolver (`gemini-3.5-flash`):** Evaluates context around unmatched breaks to classify the root cause (`duplicate`, `timing_diff`, `currency_rounding`, `missing_entry`). If confidence is high, it autonomously drafts a correcting entry. If ambiguous, it escalates.
3. **Business Risk Tagger (`gemma-4-26b-a4b-it-maas`):** A secondary agent using Vertex AI's global Model-as-a-Service endpoint to categorize the business severity (`low`, `medium`, `high`) of the break for human operators.
4. **Auditor (Google Cloud Firestore):** Writes an immutable, append-only record of every AI decision, its reasoning, and confidence score. This makes the system fully explainable, not a black box.
5. **Orchestrator:** A parallelized Python `ThreadPoolExecutor` that safely throttles and routes requests to Vertex AI, bypassing serverless timeouts and resolving hundreds of breaks in seconds.

##  Quickstart (Run Local & Demo)

You can run the entire pipeline locally. 

**1. Install & Generate Data**
```bash
pip install -r requirements.txt

# Generate synthetic ledger.csv and processor.csv for the demo (~80 breaks)
python data/generate_synthetic_data.py --rows 1000
