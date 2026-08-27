"""Investigator Agent - classifies WHY a break happened.
Cheap, obvious cases are classified deterministically (no LLM cost).
Genuinely ambiguous cases (amount/timestamp mismatches) go to Gemini."""
from services.gemini_client import classify_break
from agents import pattern_memory


def investigate(break_record):
    l = break_record.get("ledger")
    p = break_record.get("processor")
    reason = break_record.get("reason")

    if reason == "multiple_processor_matches":
        return {"break_type": "duplicate", "confidence": 0.95, "reasoning": "Processor feed has more than one record for this transaction ID.", "source": "rule"}
    if reason in ("no_processor_match", "processor_only"):
        return {"break_type": "missing_entry", "confidence": 0.85, "reasoning": "Transaction present in only one feed.", "source": "rule"}

    remembered = pattern_memory.lookup(break_record)
    if remembered:
        return remembered

    result = classify_break(l, p, reason)
    result.setdefault("source", "gemini")
    return result
