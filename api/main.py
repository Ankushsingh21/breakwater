import os
import csv
import time
from io import StringIO
from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse

from agents.matcher import run as run_matcher
from agents.orchestrator import process_single_break
from services.firestore_client import get_all_breaks, get_stats, clear_db

app = FastAPI()

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

def process_swarm_in_background(breaks):
    """Runs the LLM agents natively in the background thread."""
    for br in breaks:
        try:
            process_single_break(br)
        except Exception as e:
            print(f"[Swarm Error] Failed processing break: {e}")

@app.post("/upload_and_reconcile")
async def upload_and_reconcile(
    background_tasks: BackgroundTasks,
    ledger: UploadFile = File(...),
    processor: UploadFile = File(...)
):
    """Accepts enterprise CSVs, matches instantly, and queues the agents."""
    os.makedirs("data", exist_ok=True)
    ledger_path = f"data/{ledger.filename}"
    processor_path = f"data/{processor.filename}"
    
    with open(ledger_path, "wb") as f:
        f.write(await ledger.read())
    with open(processor_path, "wb") as f:
        f.write(await processor.read())
        
    clear_db()
    
    # 1. Deterministic Matcher (Fast)
    match_results = run_matcher(ledger_path=ledger_path, processor_path=processor_path)
    breaks = match_results.get("breaks", [])
    matched_count = len(match_results.get("matched", []))
    target_breaks = len(breaks)

    # 2. Asynchronous LLM Agents (Slow)
    if target_breaks > 0:
        background_tasks.add_task(process_swarm_in_background, breaks)
    
    return {
        "status": "processing", 
        "target_breaks": target_breaks,
        "matched": matched_count
    }

@app.get("/export")
async def export_csv():
    """Generates a downloadable CSV audit report."""
    breaks = get_all_breaks()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Record ID", "Break Type", "Amount", "Currency", "Severity", "Status", "Agent Narrative"])
    
    for br in breaks:
        l = br.get("ledger") or {}
        p = br.get("processor") or {}
        
        if isinstance(l, list) and len(l) > 0: l = l[0]
        if isinstance(p, list) and len(p) > 0: p = p[0]
        
        record_id = br.get("transaction_id") or l.get("transaction_id") or p.get("transaction_id")
        amount = br.get("amount") or l.get("amount") or p.get("amount", 0)
        currency = l.get("currency") or p.get("currency", "USD")
        b_type = br.get("investigation", {}).get("break_type", "unknown")
        severity = br.get("investigation", {}).get("severity", "unknown")
        status = br.get("resolution", {}).get("status", "processing")
        narrative = br.get("resolution", {}).get("narrative", "")
        
        writer.writerow([record_id, b_type, amount, currency, severity, status, narrative])
    
    output.seek(0)
    return StreamingResponse(
        output, 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=reconciliation_audit_report.csv"}
    )

def process_swarm_in_background(breaks):
    """Runs the LLM agents natively in the background thread."""
    for br in breaks:
        try:
            process_single_break(br)
            # Add a 0.5s pause to stay under Vertex AI Free Tier quotas
            time.sleep(0.5)
        except Exception as e:
            print(f"[Swarm Error] Failed processing break: {e}")
