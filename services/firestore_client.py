import os
import json
import time
from datetime import datetime

_db = None
USE_LOCAL = os.getenv("USE_LOCAL_STORE", "false").lower() == "true"
LOCAL_WORKFLOW_FILE = "local_workflow_state.json"
LOCAL_AUDIT_FILE = "local_immutable_audit.json"

def _get_db():
    global _db
    if _db is None and not USE_LOCAL:
        from google.cloud import firestore
        _db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    return _db

def clear_db():
    if USE_LOCAL:
        if os.path.exists(LOCAL_WORKFLOW_FILE): 
            os.remove(LOCAL_WORKFLOW_FILE)
        return
        
    try:
        db = _get_db()
        # Only delete the active UI state
        for doc in db.collection("workflow_active").stream():
            doc.reference.delete()
    except Exception as e:
        print(f"[firestore_client] Error clearing workflow DB: {e}")

def write_record(entry):
    timestamp = datetime.utcnow().isoformat()
    audit_event = {
        "timestamp": timestamp,
        "event_type": "AI_INITIAL_RESOLUTION",
        "transaction_id": entry.get("transaction_id") or entry.get("ledger", {}).get("transaction_id"),
        "data": entry
    }

    if USE_LOCAL:
        # 1. Update mutable state
        records = get_all_breaks()
        records.append(entry)
        with open(LOCAL_WORKFLOW_FILE, "w") as f: json.dump(records, f)
        
        # 2. Append to immutable audit log
        audit_records = []
        if os.path.exists(LOCAL_AUDIT_FILE):
            with open(LOCAL_AUDIT_FILE, "r") as f: audit_records = json.load(f)
        audit_records.append(audit_event)
        with open(LOCAL_AUDIT_FILE, "w") as f: json.dump(audit_records, f)
        return

    db = _get_db()
    db.collection("workflow_active").add(entry)
    db.collection("audit_events").add(audit_event)

def update_break_status(transaction_id, status, narrative):
    timestamp = datetime.utcnow().isoformat()
    audit_event = {
        "timestamp": timestamp,
        "event_type": "HUMAN_HITL_OVERRIDE",
        "transaction_id": transaction_id,
        "new_status": status,
        "narrative": narrative
    }

    if USE_LOCAL:
        # 1. Update mutable state
        records = get_all_breaks()
        for r in records:
            t_id = r.get("transaction_id") or r.get("ledger", {}).get("transaction_id")
            if t_id == transaction_id:
                if "resolution" not in r: r["resolution"] = {}
                r["resolution"]["status"] = status
                r["resolution"]["narrative"] = narrative
                break
        with open(LOCAL_WORKFLOW_FILE, "w") as f: json.dump(records, f)
        
        # 2. Append to immutable audit log
        audit_records = []
        if os.path.exists(LOCAL_AUDIT_FILE):
            with open(LOCAL_AUDIT_FILE, "r") as f: audit_records = json.load(f)
        audit_records.append(audit_event)
        with open(LOCAL_AUDIT_FILE, "w") as f: json.dump(audit_records, f)
        return

    db = _get_db()
    # 1. Update mutable state
    for doc in db.collection("workflow_active").stream():
        d = doc.to_dict()
        t_id = d.get("transaction_id") or d.get("ledger", {}).get("transaction_id")
        if t_id == transaction_id:
            doc.reference.update({"resolution.status": status, "resolution.narrative": narrative})
            break
            
    # 2. Append to immutable audit log (No updates or deletes ever happen here)
    db.collection("audit_events").add(audit_event)

def get_all_breaks():
    if USE_LOCAL:
        if os.path.exists(LOCAL_WORKFLOW_FILE):
            with open(LOCAL_WORKFLOW_FILE, "r") as f: return json.load(f)
        return []
    try:
        db = _get_db()
        return [doc.to_dict() for doc in db.collection("workflow_active").stream()]
    except Exception:
        return []

def get_stats():
    breaks = get_all_breaks()
    resolved = sum(1 for b in breaks if b.get("resolution", {}).get("status") == "auto_resolved")
    escalated = sum(1 for b in breaks if b.get("resolution", {}).get("status") == "escalated")
    manually_approved = sum(1 for b in breaks if b.get("resolution", {}).get("status") == "manually_approved")
    
    return {
        "breaks_found": len(breaks),
        "auto_resolved": resolved,
        "escalated": escalated,
        "manually_approved": manually_approved
    }
