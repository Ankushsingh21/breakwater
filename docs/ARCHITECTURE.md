# Breakwater Architecture: Enterprise Scale-to-Zero Reconciliation

Breakwater is a multi-agent autonomous reconciliation system designed to process 50,000+ transaction feeds securely, concurrently, and cheaply.

## Architectural Flow

Data feeds (ledger + processor records) are ingested via an asynchronous FastAPI endpoint. To prevent HTTP timeouts and handle massive scale, the system employs a **Pub/Sub Fan-Out pattern**.

```text
Data feeds (ledger + processor)
        |
        v
FastAPI POST /reconcile (Instant 202 Accepted)
        |
        v
Deterministic Matcher (Resolves 95% of records in <1s)
        |
        v
Pub/Sub Ingestion Queue (For the 5% true "breaks")
        |
        v
Cloud Run Autoscaling Workers (Agent Swarm)
  Embedding Filter -> Investigator -> Tagger -> Resolver -> Auditor
        |
        +---------------------+
        v                     v
  Audit log (Firestore)   Human reviewer
  full reasoning trail    ambiguous escalation
        |
        v
  Dashboard (Vanilla JS Polling)
