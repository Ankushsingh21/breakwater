import json
import os
import re

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

_client = None
if PROJECT_ID:
    try:
        from google import genai
        from google.genai import types
        
        _client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="us"
        )
        print(f"[gemini_client] Successfully initialized GenAI Vertex client for {PROJECT_ID}")
    except Exception as e:
        print(f"[gemini_client] GenAI SDK unavailable: {e}")

PROMPT_TEMPLATE = """You are a reconciliation investigator at a bank.
Two transaction records disagree. Classify the break and explain why in one sentence.

Ledger record: {ledger}
Processor record: {processor}
Matcher flagged reason: {reason}

Return ONLY a JSON object with EXACTLY these three keys:
"break_type": strictly one of ["duplicate", "timing_diff", "currency_rounding", "missing_entry", "unknown"]
"confidence": a float between 0.0 and 1.0
"reasoning": a one sentence explanation string
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
        # Force strict JSON mode in Gemini 3.5
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1 # Keep it highly deterministic
        )
        
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        
        text = response.text.strip()
        
        # In case the model still sneaks in markdown fences despite strict JSON mode
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
            
        return json.loads(text)
    except Exception as e:
        print(f"[gemini_client] API call failed: {e}\nRaw output was: {response.text if 'response' in locals() else 'None'}")
        return _fallback_classify(reason)

def _fallback_classify(reason):
    if reason == "amount_mismatch":
        return {"break_type": "currency_rounding", "confidence": 0.6, "reasoning": "Amount differs by a small margin (fallback rule)."}
    if reason == "timestamp_mismatch":
        return {"break_type": "timing_diff", "confidence": 0.6, "reasoning": "Timestamps differ but amounts match (fallback rule)."}
    return {"break_type": "unknown", "confidence": 0.3, "reasoning": "Fallback stub could not classify."}
