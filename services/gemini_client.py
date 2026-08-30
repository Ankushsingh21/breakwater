import json
import os

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

_client = None
if PROJECT_ID:
    try:
        from google import genai
        
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

Respond with ONLY valid JSON in this exact shape. Do NOT wrap it in markdown blockticks:
{"break_type": "duplicate|timing_diff|currency_rounding|missing_entry|unknown", "confidence": 0.8, "reasoning": "one sentence"}
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
        text = response.text.strip()
        
        # Robustly strip markdown fences often added by Gemini 3.5
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        print(f"[gemini_client] API call failed, using fallback: {e}\nRaw output was: {response.text if 'response' in locals() else 'None'}")
        return _fallback_classify(reason)

def _fallback_classify(reason):
    if reason == "amount_mismatch":
        return {"break_type": "currency_rounding", "confidence": 0.6, "reasoning": "Amount differs by a small margin (fallback rule)."}
    if reason == "timestamp_mismatch":
        return {"break_type": "timing_diff", "confidence": 0.6, "reasoning": "Timestamps differ but amounts match (fallback rule)."}
    return {"break_type": "unknown", "confidence": 0.3, "reasoning": "Fallback stub could not classify."}
