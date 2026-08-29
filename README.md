# Breakwater: Enterprise Multi-Agent Financial Reconciliation Engine

![Google Cloud Run](https://img.shields.io/badge/Google_Cloud_Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Vertex AI](https://img.shields.io/badge/Vertex_AI-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)

**Breakwater** is a multi-agent autonomous reconciliation system built for the **All Things Agentic Hackathon**. 

Given two transaction feeds that should agree but don't (e.g., a bank ledger vs. a payment processor), Breakwater deterministically matches what it can, investigates *why* every mismatch ("break") happened, autonomously fixes the safe ones with a full audit trail, and escalates ambiguous edge cases to a Human-in-the-Loop (HITL) review dashboard.

## Why This Exists (The Enterprise Problem)
Reconciliation is a real, expensive, high-volume operational chore in finance and FinOps. Today, it is largely manual, slow, and doesn't scale. Breakwater automates the entire loop—not just the matching (a solved problem), but the harder part: reasoning about *why* a break happened, assessing the business risk, and safely resolving it in a way that satisfies compliance auditors.

## 🧠 Multi-Agent Architecture
Breakwater uses a hybrid event-driven pipeline, combining high-speed deterministic rules with Google's latest generative AI models via the **Vertex AI GenAI SDK**.

1. **Matcher (Pandas Engine):** Deterministic matching on ID, amount, and timestamp. Clears the easy 90%+ volume instantly for free.
2. **Investigator & Resolver (`gemini-3.5-flash`):** Evaluates context around unmatched breaks to classify the root cause (`duplicate`, `timing_diff`, `currency_rounding`, `missing_entry`). If confidence is high, it autonomously drafts a correcting entry. If ambiguous, it escalates.
3. **True RAG Memory (`text-embedding-005`):** Queries a vector space of historically resolved breaks. If Gemini finds an identical past resolution, it leverages that context to resolve the current break.
4. **Business Risk Tagger (`gemma-4-26b-a4b-it-maas`):** A secondary agent using Vertex AI's global Model-as-a-Service endpoint to categorize the business severity (`low`, `medium`, `high`) of the break for human operators.
5. **Auditor (Google Cloud Firestore):** Writes an immutable, append-only record of every AI decision, its reasoning, and confidence score. This makes the system fully explainable, not a black box.
6. **Orchestrator:** A parallelized Python `ThreadPoolExecutor` that safely throttles and routes requests to Vertex AI, bypassing serverless timeouts and resolving hundreds of breaks in seconds.

## 🚀 Quickstart (Run Local & Demo)

You can run the entire pipeline locally. 

**1. Install & Generate Data**
```bash
pip install -r requirements.txt

# Generate synthetic ledger.csv and processor.csv for the demo (~80 breaks)
python data/generate_synthetic_data.py --rows 1000
```

**2. Configure Vertex AI**
```bash
cp .env.example .env
# Fill in your GOOGLE_CLOUD_PROJECT ID. 
# Ensure Vertex AI API is enabled in your GCP project.
```

**3. Run the App**
```bash
uvicorn api.main:app --reload --port 8080
```
Open `http://localhost:8080`. Drag and drop the generated `ledger.csv` and `processor.csv` files into the UI and click **Upload & Reconcile**.

> **Safe-by-default note:** If Vertex AI quotas are hit or network connectivity fails, the Investigator gracefully falls back to a conservative rule-based stub that returns low confidence scores (30%). This guarantees the Resolver correctly escalates to human review instead of auto-fixing blindly. 

## ☁️ Deploying to Google Cloud Run

To deploy Breakwater as a serverless enterprise application:
```bash
bash deploy/deploy.sh
```
*Note: To ensure the AI swarm processes large background batches without Cloud Run throttling the CPU, ensure your service has "CPU is always allocated" enabled in the GCP Console.*

## 📁 Project Structure

```text
breakwater/
├── data/generate_synthetic_data.py  # Generates CSV ledger + processor feeds
├── agents/
│   ├── matcher.py           # Agent 1 - Deterministic Pandas matching
│   ├── investigator.py      # Agent 2 - Gemini reasoning, classification & RAG
│   ├── resolver.py          # Agent 3 - Auto-fix or escalate logic
│   └── orchestrator.py      # Parallel ThreadPool orchestration
├── services/
│   ├── gemini_client.py     # Vertex AI Gemini 3.5 Flash integration
│   ├── gemma_client.py      # Vertex AI Gemma 4 MaaS integration
│   ├── embeddings.py        # Vertex AI text-embedding-005 for RAG
│   └── firestore_client.py  # Firestore immutable audit trail wrapper
├── api/main.py              # FastAPI: File uploads, background tasks, CSV export
├── dashboard/index.html     # Live polling Vanilla JS & Chart.js dashboard
├── deploy/deploy.sh         # GCP Cloud Run deployment script
└── docs/
    ├── ARCHITECTURE.md      # Detailed system design
    └── BUILD_PLAN.md        # Hackathon build log
```

## 🎥 Note for Judges: How to Test the Application Live
1. **Get the Test Data:** Navigate to the `data/` folder in this repository and download the provided `ledger.csv` and `processor.csv` test files. 
2. **Upload the Files:** Open the live application URL (or your local `http://localhost:8080`). Drag and drop the downloaded CSV files into their respective upload fields.
3. **Run the Reconciliation:** Click **Upload & Reconcile**. Notice how the deterministic matching engine clears identical records instantly, while the parallelized AI swarm processes the remaining breaks asynchronously. Watch the Chart.js visual analytics update in real-time.
4. **Inspect the AI Reasoning:** Click on any populated row in the UI to expand the **Agent Audit Trail**. You will see exactly which Vertex AI model made the decision, its confidence score, and the one-sentence accounting narrative it generated. 
5. **Human-in-the-Loop Override:** For rows marked "Escalated", click the "Approve Resolution (HITL Override)" button to manually intervene, proving the system's human-augmentation design.
6. **Export the Audit Log:** Click **Download Audit Report** to generate the final CSV file that a real-world financial controller would hand to compliance auditors.
