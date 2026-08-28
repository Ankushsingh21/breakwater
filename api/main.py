import os
import json
import base64
from fastapi import FastAPI, Request, BackgroundTasks
from google.cloud import pubsub_v1
from agents.matcher import run as run_matcher
from agents.orchestrator import process_single_break

app = FastAPI()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
TOPIC_ID = "breakwater-trigger"

publisher = pubsub_v1.PublisherClient() if PROJECT_ID else None
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID) if publisher else None

@app.post("/reconcile")
async def trigger_reconciliation():
    """1. Runs fast deterministic matching. 2. Fans out breaks to Pub/Sub."""
    match_results = run_matcher()
    breaks = match_results.get("breaks", [])
    
    if publisher and topic_path:
        # Enterprise Fan-Out: Publish each break as an independent job
        for br in breaks:
            publisher.publish(topic_path, json.dumps(br).encode("utf-8"))
        
        return {
            "status": "processing",
            "message": f"Successfully matched records. Fanned out {len(breaks)} breaks to Pub/Sub for AI investigation."
        }
    else:
        # Fallback for local dev without Pub/Sub
        for br in breaks:
            process_single_break(br)
        return {"status": "processed_locally"}

@app.post("/process_break")
async def pubsub_push_handler(request: Request):
    """Cloud Run executes this endpoint dynamically for every Pub/Sub message."""
    envelope = await request.json()
    if not envelope or "message" not in envelope:
        return {"status": "bad request"}
    
    pubsub_message = envelope["message"]
    if "data" in pubsub_message:
        # Decode the transaction break payload
        br_data = base64.b64decode(pubsub_message["data"]).decode("utf-8")
        br = json.loads(br_data)
        
        # Pass to the ADK Orchestrator
        process_single_break(br)
        
    return {"status": "ok"} # Acknowledges to Pub/Sub that the break is handled
