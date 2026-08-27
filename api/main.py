"""FastAPI backend - trigger reconciliation runs, serve stats + breaks + the dashboard."""
from fastapi import FastAPI
from fastapi.responses import FileResponse

from agents.orchestrator import run_pipeline

app = FastAPI(title="Breakwater")

_last_run = {"summary": None, "breaks": []}


@app.post("/reconcile")
def reconcile():
    global _last_run
    _last_run = run_pipeline()
    return _last_run["summary"]


@app.get("/stats")
def stats():
    return _last_run["summary"] or {"message": "No run yet. POST /reconcile first."}


@app.get("/breaks")
def breaks():
    return _last_run["breaks"]


@app.get("/breaks/{transaction_id}")
def break_detail(transaction_id: str):
    for b in _last_run["breaks"]:
        if b["transaction_id"] == transaction_id:
            return b
    return {"error": "not found"}


@app.get("/")
def dashboard():
    return FileResponse("dashboard/index.html")
