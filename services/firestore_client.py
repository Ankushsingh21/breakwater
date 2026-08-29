import os
import json

_db = None
USE_LOCAL = os.getenv("USE_LOCAL_STORE", "false").lower() == "true"
LOCAL_FILE = "local_audit_trail.json"

def _get_db():
    global _db
    if _db is None and not USE_LOCAL:
        from google.cloud import firestore
        _db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
    return _db

def clear_db():
    if USE_LOCAL:
        if os.path.exists(LOCAL_FILE): os.remove(LOCAL_FILE)
        return
    try:
        db = _get_db()
        collection = os.getenv("FIRESTORE_COLLECTION", "audit_trail")
        for doc in db.collection(collection).stream():
            doc.reference.delete()
    except Exception as e:
        print(f"[firestore_client] Error clearing DB: {e}")

def write_record(entry):
    if USE_LOCAL:
        records = get_all_breaks()
        records.append(entry)
        with open(LOCAL_FILE, "w") as f: json.dump(records, f)
        return

    db = _get_db()
    db.collection(os.getenv("FIRESTORE_COLLECTION", "audit_trail")).add(entry)

def update_break_status(transaction_id, status, narrative):
    """Updates a break after human HITL intervention."""
    if USE_LOCAL:
        records = get_all_breaks()
        for r in records:
            t_id = r.get("transaction_id") or r.get("ledger", {}).get("transaction_id")
            if t_id == transaction_id:
                if "resolution" not in r: r["resolution"] = {}
                r["resolution"]["status"] = status
                r["resolution"]["narrative"] = narrative
                break
        with open(LOCAL_FILE, "w") as f: json.dump(records, f)
        return

    db = _get_db()
    collection = os.getenv("FIRESTORE_COLLECTION", "audit_trail")
    for doc in db.collection(collection).stream():
        d = doc.to_dict()
        t_id = d.get("transaction_id") or d.get("ledger", {}).get("transaction_id")
        if t_id == transaction_id:
            doc.reference.update({"resolution.status": status, "resolution.narrative": narrative})
            break

def get_all_breaks():
    if USE_LOCAL:
        if os.path.exists(LOCAL_FILE):
            with open(LOCAL_FILE, "r") as f: return json.load(f)
        return []
    try:
        db = _get_db()
        return [doc.to_dict() for doc in db.collection(os.getenv("FIRESTORE_COLLECTION", "audit_trail")).stream()]
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
