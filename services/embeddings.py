import os
import math

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")

_client = None
_cache = {}  # In-memory cache prevents Vertex API Quota exhaustion during RAG

if _PROJECT:
    try:
        from google import genai
        _client = genai.Client(vertexai=True, project=_PROJECT, location="us-central1")
    except Exception as e:
        print(f"[embeddings] GenAI client unavailable: {e}")

def get_embedding(text: str):
    if not _client or not text: return None
    if text in _cache: return _cache[text]
    try:
        response = _client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
        emb = response.embeddings[0].values
        _cache[text] = emb
        return emb
    except Exception:
        return None

def cosine_similarity(v1, v2):
    if not v1 or not v2: return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    mag1 = math.sqrt(sum(x * x for x in v1))
    mag2 = math.sqrt(sum(y * y for y in v2))
    return dot_product / (mag1 * mag2) if mag1 and mag2 else 0.0

def check_near_duplicate(break_record, threshold=0.92):
    l_desc = break_record.get("ledger", {}).get("description", "")
    p_desc = break_record.get("processor", {}).get("description", "")
    if not l_desc or not p_desc: return False
    
    v1 = get_embedding(l_desc)
    v2 = get_embedding(p_desc)
    return cosine_similarity(v1, v2) >= threshold

def search_historical_resolutions(current_desc, historical_breaks, threshold=0.88):
    """True RAG: Finds the most similar past resolution to guide current AI decisions."""
    current_emb = get_embedding(current_desc)
    if not current_emb: return None
    
    best_match = None
    highest_sim = threshold
    
    for br in historical_breaks:
        if br.get("resolution", {}).get("status") not in ("auto_resolved", "manually_approved"): continue
        
        past_desc = br.get("ledger", {}).get("description", "")
        past_emb = get_embedding(past_desc)
        if not past_emb: continue
        
        sim = cosine_similarity(current_emb, past_emb)
        if sim > highest_sim:
            highest_sim = sim
            best_match = br.get("resolution", {}).get("narrative", "")
            
    return best_match
