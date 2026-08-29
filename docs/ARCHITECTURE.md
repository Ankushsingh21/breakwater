# Breakwater Architecture: Enterprise Scale-to-Zero Reconciliation

Breakwater is a multi-agent autonomous reconciliation system designed to process high-volume financial transaction feeds securely, concurrently, and with full auditability.

## Architectural Flow

To handle enterprise workflows, Breakwater accepts direct CSV file uploads (Ledger and Processor data). To prevent HTTP timeouts and handle massive scale, the system leverages a hybrid approach: synchronous deterministic matching for bulk clearance, followed by parallelized asynchronous background tasks for AI processing.

```text
[ Ledger CSV ] & [ Processor CSV ]
       │
       v
FastAPI POST /upload_and_reconcile 
       │
       v
Deterministic Matcher (Resolves 90%+ of records instantly in-memory)
       │
       ├──> (Matches) ──> Instant Settlement
       │
       v
Unmatched Discrepancy "Breaks" 
       │
       v
ThreadPoolExecutor (Parallel Asynchronous Workers)
       ├──> Investigator (Gemini 3.5 Flash)
       ├──> Severity Tagger (Gemma 4 MaaS)
       └──> Resolver (Gemini 3.5 Flash)
       │
       v
Audit Log (Google Cloud Firestore)
       │
       ├──> Live Dashboard (Vanilla JS Polling)
       └──> Auditor Report (CSV Export)
