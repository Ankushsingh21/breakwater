# Breakwater

Multi-agent autonomous reconciliation system. Given two transaction feeds that should agree but don't, Breakwater matches what it can, investigates *why* every mismatch ("break") happened, autonomously fixes the safe ones with a full audit trail, and escalates the ambiguous ones with a structured investigation packet instead of guessing.

Built for the All Things Agentic Hackathon — Taskmaster track.

## Why this exists

Reconciliation is a real, expensive, high-volume operational chore in any business with two systems of record that must agree (a ledger vs. a payment processor, orders vs. shipments, usage vs. billing). Today it's manual, slow, and doesn't scale. Breakwater automates the whole loop — not just matching (a solved problem), but the harder part: reasoning about *why* a break happened and safely resolving it.

## Architecture

Five agents, each with one job, wired into one asynchronous pipeline:

1. **Matcher** (no LLM) — deterministic matching on ID + amount + timestamp. Handles the easy 90%+ for free.
2. **Investigator** (Gemini 3.5 Flash) — classifies every break: `duplicate`, `timing_diff`, `currency_rounding`, `missing_entry`, or `unknown`, with a confidence score and reasoning.
3. **Resolver** (Gemini 3.5 Flash) — for high-confidence, known-safe break types, autonomously drafts a correcting entry and books it. For anything ambiguous, it escalates with a structured packet instead of guessing.
4. **Auditor** (Firestore, local JSONL in dev) — writes an immutable record of every decision and its reasoning. This is what makes the system explainable, not a black box.
5. **Orchestrator** — wires the above into one pipeline, triggerable manually or via Pub/Sub for asynchronous background runs.

See `docs/ARCHITECTURE.md` for the full diagram description.

**Safe-by-default note:** without a `GEMINI_API_KEY`, the Investigator falls back to a conservative rule-based stub that returns lower confidence scores — which means the Resolver correctly escalates instead of auto-fixing when it can't reason properly. This lets you run and demo the entire pipeline locally with zero setup and zero cost, and it's also a legitimate production-safety behavior worth mentioning in your write-up.

## Quickstart (local, no GCP needed)

```bash
pip install -r requirements.txt
python data/generate_synthetic_data.py --rows 5000 --break-rate 0.08
uvicorn api.main:app --reload
```

Open `http://localhost:8000`, click **Run reconciliation**.

## Enabling real Gemini reasoning

```bash
cp .env.example .env
# fill in GEMINI_API_KEY and GOOGLE_CLOUD_PROJECT
```
`services/gemini_client.py` will automatically use the real API once a key is present — no code changes needed.

## Deploying to Cloud Run

```bash
bash deploy/deploy.sh
```
This builds the container, deploys to Cloud Run, and wires up a Pub/Sub topic + push subscription so the pipeline can also be triggered asynchronously (e.g. from Cloud Scheduler for periodic autonomous runs), not just manually.

## Project structure

```
breakwater/
├── data/generate_synthetic_data.py   # synthetic ledger + processor feeds, with injected breaks
├── agents/
│   ├── matcher.py         # Agent 1 - deterministic matching
│   ├── investigator.py    # Agent 2 - Gemini-based break classification
│   ├── resolver.py        # Agent 3 - auto-fix or escalate
│   ├── auditor.py         # Agent 4 - immutable audit trail
│   └── orchestrator.py    # wires all agents into one pipeline
├── services/
│   ├── gemini_client.py       # Gemini wrapper + offline fallback stub
│   └── firestore_client.py    # Firestore wrapper (local JSONL fallback in dev)
├── api/main.py             # FastAPI: POST /reconcile, GET /stats, GET /breaks
├── dashboard/index.html    # single-page live dashboard
├── deploy/deploy.sh        # Cloud Run + Pub/Sub deployment
├── Dockerfile
└── docs/
    ├── ARCHITECTURE.md
    └── BUILD_PLAN.md
```

## For the submission

- `docs/ARCHITECTURE.md` — paste this into your submission's required architecture write-up / diagram
- `docs/BUILD_PLAN.md` — day-by-day build log, useful for your write-up's "how we built it" section
- Demo script: generate a large dataset (`--rows 50000`), deploy to Cloud Run, click **Run reconciliation** live on camera, and walk through 2-3 individual breaks in the table to show the reasoning behind each decision.
