"""Pattern Memory - reuses a prior high-confidence classification for breaks with
the same signature (counterparty + matcher reason) instead of re-calling the LLM.
This is what lets Breakwater get faster and cheaper the longer it runs, and it
produces a genuinely demoable metric: memory hit rate over a run."""
from agents import auditor


def _signature(counterparty, reason):
    return f"{counterparty}:{reason}"


def lookup(break_record):
    l = break_record.get("ledger") or {}
    p = break_record.get("processor") or {}
    counterparty = l.get("counterparty") or p.get("counterparty")
    sig = _signature(counterparty, break_record.get("reason"))

    for entry in reversed(auditor.read_all()):
        prior = entry.get("investigation", {})
        if prior.get("confidence", 0) < 0.5:
            continue
        prior_sig = _signature(entry.get("counterparty"), entry.get("matcher_reason"))
        if prior_sig == sig:
            return {**prior, "source": "pattern_memory"}
    return None
