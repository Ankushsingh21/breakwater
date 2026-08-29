"""Auditor Agent - writes an immutable record of every agent decision.
Firestore in the cloud, local JSON in dev - this is the audit trail that makes
the whole pipeline explainable, not a black box."""
from datetime import datetime, timezone
from services.firestore_client import write_record, get_all_breaks

def record(break_record, investigation, resolution):
    l = break_record.get("ledger") or {}
    p = break_record.get("processor") or {}
    
    # Handle list wrapping if multiple matches exist
    if isinstance(l, list) and len(l) > 0:
        l = l[0]
    if isinstance(p, list) and len(p) > 0:
        p = p[0]
        
    # Safely pull amount from ledger, processor, or break_record
    raw_amt = l.get("amount") if l.get("amount") is not None else p.get("amount")
    if raw_amt is None:
        raw_amt = break_record.get("amount", 0.0)
        
    try:
        amount_val = float(raw_amt)
    except (TypeError, ValueError):
        amount_val = 0.0

    entry = {
        "transaction_id": break_record.get("transaction_id") or l.get("transaction_id") or p.get("transaction_id"),
        "amount": amount_val,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "matcher_reason": break_record.get("reason"),
        "counterparty": l.get("counterparty") or p.get("counterparty"),
        "ledger": l,
        "processor": p,
        "investigation": investigation,
        "resolution": resolution,
    }

    # Delegate to unified firestore_client
    write_record(entry)
    return entry

def read_all():
    return get_all_breaks()
