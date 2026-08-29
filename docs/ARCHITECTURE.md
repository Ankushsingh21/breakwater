# Breakwater Architecture: Enterprise Scale-to-Zero Reconciliation

Breakwater is a multi-agent autonomous reconciliation system designed to process enterprise transaction feeds securely, concurrently, and cost-effectively.

## Architectural Flow

Data feeds (Ledger and Processor CSVs) are ingested via a dedicated file-upload FastAPI endpoint. To bypass serverless HTTP timeouts while handling massive scale, the system employs a **Parallelized ThreadPool Orchestrator** to manage the AI swarm asynchronously.

```text
 Data feeds (Ledger CSV + Processor CSV)
        |
        v
 FastAPI POST /upload_and_reconcile (Instant 202 Accepted)
        |
        v
 Deterministic Matcher (Resolves ~90% of records in <1s via Pandas)
        |
        v
 ThreadPool Orchestrator (10 Concurrent Workers for the 10% "breaks")
        |
        v
 Agent Swarm (Investigator -> Severity Tagger -> Resolver)
        |
        +---------------------+
        v                     v
   Audit log (Firestore)   Human reviewer
   full reasoning trail    ambiguous escalation
        |                     |
        +----------+----------+
                   v
     Dashboard (Vanilla JS Polling) & Auditor CSV Export
```

## Agent Swarm & Model Selection

A core design principle of Breakwater is **Cost-Aware Routing**. We strictly avoid monolithic LLM calls, instead routing specific tasks to the most efficient capable model tier. We rely exclusively on Google Cloud Vertex AI Model-as-a-Service (MaaS) endpoints to maintain a true scale-to-zero footprint and avoid expensive dedicated GPU provisioning.

| Agent | Model / Approach | Responsibility |
|---|---|---|
| **Matcher** | `Pandas` (Deterministic) | Clears the massive majority of transactions instantly using exact ID, amount, and timestamp matching. |
| **RAG Memory** | `text-embedding-005` (Vertex AI) | Generates vector embeddings of current breaks to search Firestore for identical historical resolutions, acting as a cheap semantic pre-filter. |
| **Investigator** | `gemini-3.5-flash` (Vertex AI Multi-Region) | Evaluates the context of unmatched breaks to classify *why* a break happened (e.g., timing difference, currency rounding) and calculates a confidence score. Incorporates RAG context if found. |
| **Severity Tagger** | `gemma-4-26b-a4b-it-maas` (Vertex AI Global MaaS) | A lightweight, open-model classification step to tag business priority (low, medium, high) based on risk and monetary value for dashboard triage. |
| **Resolver** | `gemini-3.5-flash` (Vertex AI Multi-Region) | Auto-fixes known-safe classes with generated accounting narratives. Escalates low-confidence anomalies to human operations. |
| **Auditor** | `Firestore` (No LLM) | Writes an immutable, append-only record of every AI agent's decision and reasoning, acting as the system's memory. |

## Key Design Decisions
* **Parallelized Asynchronous Execution:** By offloading break resolution to a heavily throttled `ThreadPoolExecutor`, the UI remains perfectly responsive. The application processes hundreds of LLM calls concurrently in the background without triggering Cloud Run CPU timeouts or Vertex AI quota limits (429 errors).
* **True RAG for Historical Decisions:** The system learns from past resolutions. Using `text-embedding-005`, the Investigator searches for previously resolved breaks with high cosine similarity (>= 0.88) and injects that historical precedent into the prompt context before Gemini makes its decision.
* **Safe-by-Default Fallbacks:** Auto-resolution only fires on >= 0.70 confidence scores. Lower confidence, Vertex AI quota limits, or network timeouts immediately route to human escalation with a structured investigation packet. Breakwater never guesses.
* **Human-in-the-Loop (HITL) UI:** A dedicated override endpoint allows human operators to intervene on escalated breaks directly from the dashboard, proving the AI augments human workflows rather than replacing them.
* **Explainability & Compliance:** Enterprise financial systems require strict auditability. Breakwater does not just store the final status; the Auditor Agent logs the explicit reasoning chain, confidence score, and model layer used for every transaction. This is easily exportable via the `/export` endpoint for compliance review.
