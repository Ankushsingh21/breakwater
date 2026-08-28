"""Thin wrapper around a Gemma model on Vertex AI. Falls back to a deterministic
heuristic if Vertex AI isn't configured, so the pipeline still runs standalone."""
import os

GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemini-1.5-flash-002")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

_endpoint = None
if _PROJECT:
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        # Hard-route to us-east1 to bypass free-tier region locks
        vertexai.init(project=_PROJECT, location="us-east1")
        _endpoint = GenerativeModel(GEMMA_MODEL)
    except Exception as e:
        print(f"[gemma_client] Vertex AI unavailable: {e}")


def tag_severity(break_type, amount, confidence):
    if _endpoint is None:
        return _fallback_severity(break_type, amount, confidence)
    prompt = (
        f"Classify this reconciliation break's business severity as exactly one word "
        f"(low, medium, or high). Break type: {break_type}. Amount: {amount}. "
        f"Classification confidence: {confidence}."
    )
    try:
        response = _endpoint.generate_content(prompt)
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
