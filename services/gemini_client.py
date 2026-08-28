import json
import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

_client = None
if PROJECT_ID:
    try:
        from google import genai
        
        # Add vertexai=True to route to Google Cloud instead of AI Studio
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="us-central1" 
        )
        print(f"[gemini_client] Successfully initialized GenAI Vertex client for {PROJECT_ID}")
    except Exception as e:
        print(f"[gemini_client] GenAI SDK unavailable: {e}")

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
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
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
