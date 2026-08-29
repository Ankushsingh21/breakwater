import os
import csv
import time
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from agents.matcher import run as run_matcher
from agents.orchestrator import process_single_break
from services.firestore_client import get_all_breaks, get_stats, clear_db, update_break_status

app = FastAPI()

class OverrideRequest(BaseModel):
    transaction_id: str
    status: str
    narrative: str

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

@app.post("/override")
async def override_break(req: OverrideRequest):
    """HITL Endpoint: Allows human operators to override escalated breaks."""
    update_break_status(req.transaction_id, req.status, req.narrative)
    return {"status": "success"}

def _safe_process(br):
    try:
        l = br.get("ledger")
        p = br.get("processor")
        
        if l is None: br["ledger"] = {}
        elif isinstance(l, list): br["ledger"] = l[0] if len(l) > 0 else {}
            
        if p is None: br["processor"] = {}
        elif isinstance(p, list): br["processor"] = p[0] if len(p) > 0 else {}

        process_single_break(br)
        time.sleep(0.20)
    except Exception as e:
        print(f"[Swarm Error] Failed processing break: {e}")

def process_swarm_in_background(breaks):
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(_safe_process, breaks)
    print("[Swarm] All background processing completed.")

@app.post("/upload_and_reconcile")
async def upload_and_reconcile(
    background_tasks: BackgroundTasks,
    ledger: UploadFile = File(...),
    processor: UploadFile = File(...)
):
    os.makedirs("data", exist_ok=True)
    ledger_path = f"data/{ledger.filename}"
    processor_path = f"data/{processor.filename}"
    
    with open(ledger_path, "wb") as f: f.write(await ledger.read())
    with open(processor_path, "wb") as f: f.write(await processor.read())
        
    clear_db()
    
    match_results = run_matcher(ledger_path=ledger_path, processor_path=processor_path)
    breaks = match_results.get("breaks", [])
    matched_count = len(match_results.get("matched", []))
    target_breaks = len(breaks)

    if target_breaks > 0:
        background_tasks.add_task(process_swarm_in_background, breaks)
    
    return {"status": "processing", "target_breaks": target_breaks, "matched": matched_count}

@app.get("/export")
async def export_csv():
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
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=reconciliation_audit_report.csv"})
