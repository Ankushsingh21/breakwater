"""Auditor Agent - writes an immutable record of every agent decision.
Firestore in the cloud, local JSONL in dev - this is the audit trail that makes
the whole pipeline explainable, not a black box."""
import json
import os
from datetime import datetime, timezone
from services.firestore_client import write_record

LOCAL_LOG_PATH = "data/audit_log.jsonl"


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

    if os.getenv("USE_LOCAL_STORE", "true").lower() == "true":
        os.makedirs(os.path.dirname(LOCAL_LOG_PATH), exist_ok=True)
        with open(LOCAL_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    else:
        write_record(entry)

    return entry


def read_all():
    if not os.path.exists(LOCAL_LOG_PATH):
        return []
    with open(LOCAL_LOG_PATH) as f:
        return [json.loads(line) for line in f]
