import os
import json
import base64
from fastapi import FastAPI, Request, BackgroundTasks
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

@app.post("/reset")
async def reset_system():
    clear_db()
    return {"status": "ok"}

@app.post("/reconcile")
async def trigger_reconciliation(background_tasks: BackgroundTasks):
    """Wipes old data, runs deterministic matching instantly, and queues LLM agents."""
    clear_db()
    
    # Run the Matcher instantly to get exact numbers for the UI
    match_results = run_matcher()
    breaks = match_results.get("breaks", [])
    matched_count = len(match_results.get("matched", []))
    target_breaks = len(breaks)

    def fan_out():
        if publisher and topic_path:
            for br in breaks:
                publisher.publish(topic_path, json.dumps(br).encode("utf-8"))
        else:
            for br in breaks:
                process_single_break(br)

    # Push the slow LLM processing to the background
    background_tasks.add_task(fan_out)
    
    # Return the exact target metrics to the UI so it knows when to stop polling
    return {
        "status": "processing", 
        "target_breaks": target_breaks,
        "matched": matched_count
    }

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
