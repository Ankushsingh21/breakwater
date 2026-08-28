import os

GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemini-2.5-flash")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

_client = None
if _PROJECT:
    try:
        from google import genai
        # Add vertexai=True to route to Google Cloud instead of AI Studio
        _client = genai.Client(
            vertexai=True,
            project=_PROJECT,
            location="us-central1"
        )
        print(f"[gemma_client] Successfully initialized GenAI Vertex client")
    except Exception as e:
        print(f"[gemma_client] GenAI client unavailable: {e}")

def tag_severity(break_type, amount, confidence):
    if _client is None:
        return _fallback_severity(break_type, amount, confidence)
    prompt = (
        f"Classify this reconciliation break's business severity as exactly one word "
        f"(low, medium, or high). Break type: {break_type}. Amount: {amount}. "
        f"Classification confidence: {confidence}."
    )
    try:
        response = _client.models.generate_content(
            model=GEMMA_MODEL,
            contents=prompt
        )
        word = response.text.strip().lower()
        return word if word in ("low", "medium", "high") else _fallback_severity(break_type, amount, confidence)
    except Exception as e:
        print(f"[gemma_client] call failed, using fallback: {e}")
        return _fallback_severity(break_type, amount, confidence)

def _fallback_severity(break_type, amount, confidence):
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0
    if break_type in ("missing_entry", "unknown") or amount > 20000:
        return "high"
    if confidence < 0.6:
        return "medium"
    return "low"
