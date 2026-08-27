"""Thin wrapper around Gemini. Falls back to a deterministic stub if no API key is
set, so the whole pipeline runs end-to-end locally with zero cost / zero setup."""
import json
import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
_API_KEY = os.getenv("GEMINI_API_KEY")

_client = None
if _API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=_API_KEY)
        _client = genai.GenerativeModel(MODEL)
    except Exception as e:
        print(f"[gemini_client] SDK unavailable, using fallback stub: {e}")

PROMPT_TEMPLATE = """You are a reconciliation investigator at a bank.
Two transaction records disagree. Classify the break and explain why in one sentence.

Ledger record: {ledger}
Processor record: {processor}
Matcher flagged reason: {reason}

Respond with ONLY valid JSON in this exact shape:
{{"break_type": "duplicate|timing_diff|currency_rounding|missing_entry|unknown", "confidence": 0.0-1.0, "reasoning": "one sentence"}}
"""


def classify_break(ledger, processor, reason):
    if _client is None:
        return _fallback_classify(reason)
    prompt = PROMPT_TEMPLATE.format(ledger=ledger, processor=processor, reason=reason)
    try:
        response = _client.generate_content(prompt)
        text = response.text.strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception as e:
        print(f"[gemini_client] call failed, using fallback: {e}")
        return _fallback_classify(reason)


def _fallback_classify(reason):
    if reason == "amount_mismatch":
        return {"break_type": "currency_rounding", "confidence": 0.6, "reasoning": "Amount differs by a small margin, consistent with FX rounding (fallback rule)."}
    if reason == "timestamp_mismatch":
        return {"break_type": "timing_diff", "confidence": 0.6, "reasoning": "Timestamps differ but amounts match, consistent with settlement timing lag (fallback rule)."}
    return {"break_type": "unknown", "confidence": 0.3, "reasoning": "Fallback stub could not confidently classify this break."}
