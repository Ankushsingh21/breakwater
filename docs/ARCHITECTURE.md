# Breakwater Architecture: Enterprise Scale-to-Zero Reconciliation

Breakwater is a multi-agent autonomous reconciliation system designed to process enterprise transaction feeds securely, concurrently, and cost-effectively.

## Architectural Flow

Data feeds (Ledger and Processor CSVs) are ingested via a dedicated file-upload FastAPI endpoint. To bypass serverless HTTP timeouts while handling massive scale, the system employs a **Parallelized ThreadPool Orchestrator** to manage the AI swarm asynchronously.

```
> Data feeds (Ledger CSV + Processor CSV)
>        |
>        v
> FastAPI POST /upload_and_reconcile (Instant 202 Accepted)
>        |
>        v
> Deterministic Matcher (Resolves ~90% of records in <1s via Pandas)
>        |
>        v
> ThreadPool Orchestrator (10 Concurrent Workers for the 10% "breaks")
>        |
>        v
> Agent Swarm (Investigator -> Severity Tagger -> Resolver)
>        |
>        +---------------------+
>        v                     v
>   Audit log (Firestore)   Human reviewer
>   full reasoning trail    ambiguous escalation
>        |                     |
>        +----------+----------+
>                   v
>     Dashboard (Vanilla JS Polling) & Auditor CSV Export

```
## Agent Swarm & Model Selection

A core design principle of Breakwater is **Cost-Aware Routing**. We strictly avoid monolithic LLM calls, instead routing specific tasks to the most efficient capable model tier. We rely exclusively on Google Cloud Vertex AI Model-as-a-Service (MaaS) endpoints to maintain a true scale-to-zero footprint and avoid expensive dedicated GPU provisioning.

| Agent | Model / Approach | Responsibility |
|---|---|---|
| **Matcher** | `Pandas` (Deterministic) | Clears the massive majority of transactions instantly using exact ID, amount, and timestamp matching. |
| **Investigator** | `gemini-3.5-flash` (Vertex AI Multi-Region) | Evaluates the context of unmatched breaks to classify *why* a break happened (e.g., timing difference, currency rounding) and calculates a confidence score. |
| **Severity Tagger** | `gemma-4-26b-a4b-it-maas` (Vertex AI Global MaaS) | A lightweight, open-model classification step to tag business priority (low, medium, high) based on risk and monetary value for dashboard triage. |
| **Resolver** | `gemini-3.5-flash` (Vertex AI Multi-Region) | Auto-fixes known-safe classes with generated accounting narratives. Escalates low-confidence anomalies to human operations. |
| **Auditor** | `Firestore` (No LLM) | Writes an immutable, append-only record of every AI agent's decision and reasoning, acting as the system's memory. |

## Key Design Decisions
* **Parallelized Asynchronous Execution:** By offloading break resolution to a heavily throttled `ThreadPoolExecutor`, the UI remains perfectly responsive. The application processes hundreds of LLM calls concurrently in the background without triggering Cloud Run CPU timeouts or Vertex AI quota limits (429 errors).
* **Safe-by-Default Fallbacks:** Auto-resolution only fires on >= 0.70 confidence scores. Lower confidence, Vertex AI quota limits, or network timeouts immediately route to human escalation with a structured investigation packet. Breakwater never guesses.
* **Dynamic Currency & Data Sanitization:** Financial data is dirty. The pipeline sanitizes `None` types and unspools array collisions before hitting the models. The frontend dynamically renders currencies (USD, EUR, GBP, INR) based on ISO codes derived from the source data.
* **Explainability & Compliance:** Enterprise financial systems require strict auditability. Breakwater does not just store the final status; the Auditor Agent logs the explicit reasoning chain, confidence score, and model layer used for every transaction. This is easily exportable via the `/export` endpoint for compliance review.
