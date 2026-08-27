# Breakwater — architecture

## Flow

Data feeds (ledger + processor records) are ingested asynchronously via Pub/Sub, which triggers the agent swarm. The swarm matches, investigates, and resolves every break, then either writes to the audit log (auto-resolved cases) or escalates to a human reviewer (ambiguous cases). The dashboard reads live from the audit log.

```
Data feeds (ledger + processor)
        |
        v
Pub/Sub ingestion (async batch trigger)
        |
        v
Agent swarm (ADK)
  Matcher -> Investigator -> Resolver -> Auditor
        |
        +---------------------+
        v                     v
  Audit log (Firestore)   Human reviewer
  full reasoning trail    ambiguous break escalation
        |
        v
  Dashboard (Cloud Run)
  live break feed + stats
```

## Agents

| Agent | Model / approach | Responsibility |
|---|---|---|
| Matcher | None (deterministic) | Matches records on ID + amount + timestamp. No LLM cost on the easy majority. |
| Investigator | Gemini 3.5 Flash | Classifies *why* a break happened, with a confidence score and reasoning, for the ambiguous minority the Matcher couldn't resolve. |
| Resolver | Gemini 3.5 Flash | Auto-fixes known-safe, high-confidence break types with a generated correcting entry; escalates everything else with a structured packet. |
| Auditor | None (Firestore / local JSONL) | Writes an immutable, timestamped record of every decision and its reasoning — this is the system's explainability layer. |
| Orchestrator | ADK sequential pipeline | Wires the four agents together, triggerable manually or asynchronously via Pub/Sub. |

## Design decisions worth calling out in the write-up

- **LLM calls are reserved for genuinely ambiguous cases.** Duplicate and missing-entry breaks are classified deterministically before anything reaches Gemini — this keeps cost and latency down and demonstrates knowing *when* reasoning is warranted, not reaching for an LLM everywhere.
- **Safe-by-default resolution.** The Resolver only auto-fixes when confidence is high (≥0.7); anything less gets escalated rather than guessed. In offline/dev mode without a Gemini key, the fallback stub deliberately returns lower confidence, so the system defaults to escalation rather than false auto-fixes — a production-minded safety margin, not just a fallback for convenience.
- **Full auditability.** Every autonomous decision is traceable to the evidence and reasoning that produced it, which matters both for the hackathon's architecture criterion and for the real-world credibility of "an agent that touches financial records."
- **Async by design.** Pub/Sub ingestion means the pipeline can run on a schedule (e.g. via Cloud Scheduler) without a human triggering it — genuinely "runs in the background," not just a script waiting for a button click.
