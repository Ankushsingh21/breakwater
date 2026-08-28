"""Pattern Memory - reuses prior high-confidence classifications."""
from services.firestore_client import get_all_breaks

def _signature(counterparty, reason):
    return f"{counterparty}:{reason}"

def lookup(break_record):
    l = break_record.get("ledger") or {}
    p = break_record.get("processor") or {}
    counterparty = l.get("counterparty") or p.get("counterparty")
    sig = _signature(counterparty, break_record.get("reason"))

    # Fetch from unified firestore client
    for entry in reversed(get_all_breaks()):
        prior = entry.get("investigation", {})
        if prior.get("confidence", 0) < 0.5:
            continue
        prior_sig = _signature(entry.get("counterparty"), entry.get("matcher_reason"))
        if prior_sig == sig:
            return {**prior, "source": "pattern_memory"}
    return None
