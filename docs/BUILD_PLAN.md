# Breakwater — 6-day build plan

The core pipeline (all 5 agents, API, dashboard) already exists in this repo as a working starting point. Use it as your Day 1-3 foundation and focus your remaining days on hardening, cloud deployment, and the demo.

## Day 1 — Verify and extend the local pipeline
- Run the starter locally: `pip install -r requirements.txt`, generate data, `uvicorn api.main:app --reload`, confirm the dashboard works end to end
- Read through all 5 agent files until you can explain each one's job in one sentence — you'll need this fluency for Q&A
- Tune `data/generate_synthetic_data.py`: add 1-2 more realistic break patterns if you have time (e.g. a partial-amount split payment)

## Day 2 — Real Gemini integration
- Get a `GEMINI_API_KEY`, fill in `.env`, confirm `services/gemini_client.py` is hitting the real API (check logs for fallback warnings — if you see them, your key isn't loading)
- Run against a mid-size dataset (~10,000 rows) and spot-check 10-15 Investigator classifications by hand — correct the prompt in `PROMPT_TEMPLATE` if reasoning quality is weak
- Tighten the Resolver's `AUTO_RESOLVE_TYPES` and confidence threshold based on what you observe

## Day 3 — Firestore + Cloud Run
- Enable Firestore in your GCP project, set `USE_LOCAL_STORE=false`, confirm `services/firestore_client.py` writes real records
- Build and deploy with `bash deploy/deploy.sh`
- Confirm the deployed dashboard works end to end against real Cloud Run + Firestore

## Day 4 — Scale + Pub/Sub
- Generate a large dataset: `python data/generate_synthetic_data.py --rows 75000`
- Run a full batch reconciliation against it — this is your proof of "handles the heavy lifting of massive datasets," so time it and note the numbers for your write-up
- Confirm the Pub/Sub topic + push subscription created by `deploy.sh` actually triggers `/reconcile` — test with `gcloud pubsub topics publish breakwater-trigger --message="run"`
- Optional: wire Cloud Scheduler to the Pub/Sub topic for a periodic autonomous run, so your demo can show it firing without you touching a button

## Day 5 — Polish + optional bonus points
- Polish the dashboard: sort breaks by status, add a click-to-expand row showing the full audit entry (ledger vs. processor side by side)
- Optional bonus (only if time allows): add a lightweight Gemma-based severity tagger agent for a legitimate second-model integration — don't force it in if it costs you polish time elsewhere
- Write `tests/test_pipeline.py` covering the Matcher's core matching logic on a small fixture

## Day 6 — Demo, docs, submit
- Record the demo video: show a live triggered run against the large dataset, then walk through 2-3 individual breaks in the dashboard, reading out the Investigator's reasoning and the Resolver's action for each
- Finalize `README.md` and `docs/ARCHITECTURE.md` (already drafted — just confirm they match what you actually built)
- Publish a short blog/social post about the build (small bonus points per the hackathon rules)
- Final pass against the submission checklist: public repo, complete README, video proves live GCP execution, required stack (Gemini + ADK + a GCP service) clearly visible
