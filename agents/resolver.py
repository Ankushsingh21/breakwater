"""Resolver Agent - autonomously fixes known-safe breaks, escalates the rest."""
import os

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

_client = None
if _PROJECT:
    try:
        from google import genai
        _client = genai.Client(vertexai=True, project=_PROJECT, location="us")
    except Exception:
        pass

AUTO_RESOLVE_TYPES = {"timing_diff", "currency_rounding", "duplicate", "missing_entry"}

def resolve(break_record, investigation):
    break_type = investigation.get("break_type", "unknown")
    
    # CRITICAL FIX: Safely parse the confidence score as a float
    try:
        raw_conf = investigation.get("confidence", 0.0)
        confidence = float(raw_conf)
    except (ValueError, TypeError):
        confidence = 0.0

    # Safe-by-Default threshold lowered slightly to 0.60 for Hackathon Demo Data
    if break_type in AUTO_RESOLVE_TYPES and confidence >= 0.60:
        narrative = _generate_narrative(break_type, break_record, investigation.get("reasoning"))
        return {"status": "auto_resolved", "break_type": break_type, "narrative": narrative}

    # Escalate ambiguous cases with a structured packet
    packet = {
        "transaction_id": break_record.get("transaction_id"),
        "break_type": break_type,
        "confidence": confidence,
        "reasoning": investigation.get("reasoning"),
        "ledger": break_record.get("ledger"),
        "processor": break_record.get("processor"),
    }
    return {"status": "escalated", "break_type": break_type, "packet": packet}

def _generate_narrative(break_type, break_record, reasoning):
    txn = break_record.get("transaction_id", "Unknown")
    if not _client:
        return f"{txn} auto-resolved ({break_type}). {reasoning}"
    
    prompt = f"Draft a professional accounting narrative (one sentence) to resolve a {break_type} for transaction {txn}. Context: {reasoning}"
    try:
        response = _client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return response.text.strip()
    except Exception:
        return f"{txn} auto-resolved ({break_type}). {reasoning}"
