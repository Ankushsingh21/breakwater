"""Vertex AI wrapper. Automatically uses GCP IAM credentials in Cloud Run,
so no API key is required. Falls back to a deterministic stub if project isn't set."""
import json
import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_client = None
if PROJECT_ID:
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        
        # Hard-route to us-east1 to bypass free-tier region locks
        vertexai.init(project=PROJECT_ID, location="us-east1")
        _client = GenerativeModel(GEMINI_MODEL)
        print(f"[gemini_client] Successfully initialized Vertex AI in us-east1")
    except Exception as e:
        print(f"[gemini_client] Vertex AI SDK unavailable: {e}")

PROMPT_TEMPLATE = """You are a reconciliation investigator at a bank.
Two transaction records disagree. Classify the break and explain why in one sentence.

Ledger record: {ledger}
Processor record: {processor}
Matcher flagged reason: {reason}

Respond with ONLY valid JSON in this exact shape:
{{"break_type": "duplicate|timing_diff|currency_rounding|missing_entry|unknown", "confidence": 0.8, "reasoning": "one sentence"}}
"""

def classify_break(ledger, processor, reason):
    if _client is None:
        return _fallback_classify(reason)
    
    prompt = PROMPT_TEMPLATE.format(
        ledger=ledger, 
        processor=processor, 
        reason=reason
    )
    
    try:
        response = _client.generate_content(prompt)
        text = response.text.strip().strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[gemini_client] API call failed, using fallback: {e}")
        return _fallback_classify(reason)

def _fallback_classify(reason):
    if reason == "amount_mismatch":
        return {"break_type": "currency_rounding", "confidence": 0.6, "reasoning": "Amount differs by a small margin (fallback rule)."}
    if reason == "timestamp_mismatch":
        return {"break_type": "timing_diff", "confidence": 0.6, "reasoning": "Timestamps differ but amounts match (fallback rule)."}
    return {"break_type": "unknown", "confidence": 0.3, "reasoning": "Fallback stub could not classify."}
