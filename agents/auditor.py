"""Auditor Agent - writes an immutable record of every agent decision.
Firestore in the cloud, local JSON in dev - this is the audit trail that makes
the whole pipeline explainable, not a black box."""
from datetime import datetime, timezone
from services.firestore_client import write_record, get_all_breaks

def record(break_record, investigation, resolution):
    l = break_record.get("ledger") or {}
    p = break_record.get("processor") or {}
    
    entry = {
        "transaction_id": break_record.get("transaction_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "matcher_reason": break_record.get("reason"),
        "counterparty": l.get("counterparty") or p.get("counterparty"),
        "investigation": investigation,
        "resolution": resolution,
    }

    # Delegate entirely to the unified firestore_client
    write_record(entry)
    return entry

def read_all():
    return get_all_breaks()
