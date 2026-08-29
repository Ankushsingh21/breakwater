from services.gemini_client import classify_break
from services.embeddings import check_near_duplicate, search_historical_resolutions
from services.firestore_client import get_all_breaks

def investigate(break_record):
    # 1. Cheap Vector Pre-Filter
    if check_near_duplicate(break_record):
        return {
            "break_type": "duplicate",
            "confidence": 0.95,
            "reasoning": "Embedding similarity confirms descriptions are semantically identical.",
            "source": "embedding_prefilter"
        }

    # 2. True RAG Context Injection (Query last 50 breaks)
    past_breaks = get_all_breaks()[-50:]
    l_desc = break_record.get("ledger", {}).get("description", "")
    historical_context = search_historical_resolutions(l_desc, past_breaks)

    reason = break_record.get("reason", "unknown")
    if historical_context:
        reason += f"\n[RAG CONTEXT: A historically identical break was resolved via: '{historical_context}']"
    
    # 3. Gemini Reasoning
    result = classify_break(str(break_record.get("ledger", {})), str(break_record.get("processor", {})), reason)
    result["source"] = "gemini_reasoning_with_rag" if historical_context else "gemini_reasoning"
    
    return result
