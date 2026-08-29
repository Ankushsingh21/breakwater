"""Vertex AI text-embeddings client for semantic pre-filtering."""
import os
import math

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

_client = None
if _PROJECT:
    try:
        from google import genai
        _client = genai.Client(
            vertexai=True, 
            project=_PROJECT, 
            location="us-central1"
        )
        print(f"[embeddings] Successfully initialized GenAI client for {EMBEDDING_MODEL}")
    except Exception as e:
        print(f"[embeddings] GenAI client unavailable: {e}")

def get_embedding(text: str):
    if not _client or not text:
        return None
    try:
        response = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"[embeddings] API call failed: {e}")
        return None

def cosine_similarity(v1, v2):
    if not v1 or not v2: 
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    mag1 = math.sqrt(sum(x * x for x in v1))
    mag2 = math.sqrt(sum(y * y for y in v2))
    return dot_product / (mag1 * mag2) if mag1 and mag2 else 0.0

def check_near_duplicate(break_record, threshold=0.92):
    """Checks if ledger and processor descriptions are semantically identical."""
    l_desc = break_record.get("ledger", {}).get("description", "")
    p_desc = break_record.get("processor", {}).get("description", "")
    
    if not l_desc or not p_desc:
        return False
        
    v1 = get_embedding(l_desc)
    v2 = get_embedding(p_desc)
    
    similarity = cosine_similarity(v1, v2)
    return similarity >= threshold
