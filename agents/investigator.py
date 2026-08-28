"""Investigator Agent - determines the root cause of the break."""
from services.gemini_client import classify_break
from services.embeddings import check_near_duplicate

def investigate(break_record):
    # 1. Cheap Vector Pre-Filter: Check for semantic duplicates first
    is_near_dup = check_near_duplicate(break_record)
    
    if is_near_dup:
        print("[Investigator] Caught near-duplicate via text embeddings. Bypassing LLM.")
        return {
            "break_type": "duplicate",
            "confidence": 0.95,
            "reasoning": "Embedding similarity confirms transaction descriptions are semantically identical despite minor text variations.",
            "source": "embedding_prefilter"
        }

    # 2. Fallback to Gemini Reasoning for ambiguous breaks
    ledger_str = str(break_record.get("ledger", {}))
    processor_str = str(break_record.get("processor", {}))
    reason = break_record.get("reason", "unknown")
    
    result = classify_break(ledger_str, processor_str, reason)
    result["source"] = "gemini_reasoning"
    
    return result
