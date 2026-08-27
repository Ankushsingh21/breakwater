"""Resolver Agent - autonomously fixes known-safe breaks, escalates the rest with
a structured investigation packet instead of guessing."""

AUTO_RESOLVE_TYPES = {"timing_diff", "currency_rounding", "duplicate"}


def resolve(break_record, investigation):
    break_type = investigation["break_type"]
    confidence = investigation.get("confidence", 0)

    if break_type in AUTO_RESOLVE_TYPES and confidence >= 0.7:
        return {"status": "auto_resolved", "break_type": break_type, "narrative": _narrative_for(break_type, break_record)}

    packet = {
        "transaction_id": break_record.get("transaction_id"),
        "break_type": break_type,
        "confidence": confidence,
        "reasoning": investigation.get("reasoning"),
        "ledger": break_record.get("ledger"),
        "processor": break_record.get("processor"),
    }
    return {"status": "escalated", "break_type": break_type, "packet": packet}


def _narrative_for(break_type, break_record):
    txn = break_record.get("transaction_id")
    if break_type == "duplicate":
        return f"Duplicate processor entry for {txn} - booking a reversing entry to cancel the extra charge."
    if break_type == "timing_diff":
        return f"{txn} settled on a different date than the ledger post - timing difference, marking as reconciled."
    if break_type == "currency_rounding":
        return f"{txn} amount differs by a small margin consistent with FX rounding - booking a rounding adjustment entry."
    return f"{txn} auto-resolved."
