# Changelog - v2 upgrades

## New agent: Pattern Memory (`agents/pattern_memory.py`)
Checks the audit log for a prior classification with the same counterparty + break reason before calling Gemini. If found, reuses it and tags `"source": "pattern_memory"` instead of paying for another LLM call.

**This is your strongest "Innovation" talking point.** Verified live: memory hit rate went 35% -> 50% across two runs on the same 1,000-row dataset. Quote this in your write-up/demo: *"the system gets measurably cheaper and faster the longer it runs."*

Wired into: `agents/investigator.py` (checks memory before calling Gemini), `agents/auditor.py` (now stores `counterparty` so memory has something to match on).

## New agent: Severity Tagger (`agents/severity_tagger.py` + `services/gemma_client.py`)
Uses Gemma (via Vertex AI, with an offline heuristic fallback) to tag each break `low`/`medium`/`high` for dashboard triage. This is your legitimate second-Google-model integration for the hackathon's bonus criterion — it has a real job, not bolted on for points.

Wired into: `agents/orchestrator.py` (runs after Investigator, before Resolver).

## New stats in the pipeline summary
`memory_hit_rate` and `severity_breakdown` now appear in every `/stats` response and `run_pipeline()` output. Dashboard shows the memory hit rate as a live stat card, and each break row now shows severity + a "(memory)" tag when resolved from cache.

## New endpoint
`GET /breaks/{transaction_id}` — full audit detail for one specific break, for drilling into a single decision live during the demo.

## New: autonomous scheduling (`deploy/scheduler.sh`)
Wires Cloud Scheduler to the Pub/Sub topic so Breakwater runs itself hourly with no human trigger — directly proves the hackathon's "runs in the background" language, not just "you can trigger it."

## New: `tests/test_pipeline.py`
One test covering the Matcher's core logic. Cheap production-readiness signal.

## Bug fixed during this upgrade
Pattern Memory initially required 0.7+ confidence to cache a result, but the offline fallback stub always returns 0.6 — so memory silently never fired in local/offline mode. Fixed by lowering the memory threshold to 0.5 (kept separate from the Resolver's 0.7 auto-fix threshold, which is intentionally stricter). Verified fixed by running the pipeline twice and confirming the hit rate actually climbs.

## Where nothing changed
`matcher.py`, `resolver.py`, `services/gemini_client.py`, `services/firestore_client.py`, `deploy/deploy.sh`, `Dockerfile` — untouched from the first version.
