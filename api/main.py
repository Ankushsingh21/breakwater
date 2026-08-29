import os
import json
import base64
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from google.cloud import pubsub_v1

from agents.matcher import run as run_matcher
from agents.orchestrator import process_single_break
from services.firestore_client import get_all_breaks, get_stats, clear_db

app = FastAPI()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
TOPIC_ID = "breakwater-trigger"

publisher = pubsub_v1.PublisherClient() if PROJECT_ID else None
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID) if publisher else None

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("dashboard/index.html", "r") as f:
        return f.read()

@app.get("/stats")
async def get_dashboard_stats():
    return get_stats()

@app.get("/breaks")
async def get_dashboard_breaks():
    return get_all_breaks()

@app.post("/reconcile")
async def trigger_reconciliation():
    """1. Clears old data. 2. Matches records. 3. Fans out to Pub/Sub."""
    clear_db()  # Wipes the old $0.00 records from previous runs
    
    match_results = run_matcher()
    breaks = match_results.get("breaks", [])
    
    if publisher and topic_path:
        for br in breaks:
            publisher.publish(topic_path, json.dumps(br).encode("utf-8"))
        
        return {"status": "processing", "message": f"Fanned out {len(breaks)} breaks."}
    else:
        for br in breaks:
            process_single_break(br)
        return {"status": "processed_locally"}

@app.post("/process_break")
async def pubsub_push_handler(request: Request):
    envelope = await request.json()
    if not envelope or "message" not in envelope:
        return {"status": "bad request"}
    
    pubsub_message = envelope["message"]
    if "data" in pubsub_message:
        br_data = base64.b64decode(pubsub_message["data"]).decode("utf-8")
        br = json.loads(br_data)
        process_single_break(br)
        
    return {"status": "ok"}
