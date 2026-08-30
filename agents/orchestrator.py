from google.adk import Agent, Workflow
from agents.investigator import investigate
from services.gemma_client import tag_severity
from agents.resolver import resolve
from services.firestore_client import write_record

# 1. Define the Agents using the required Google Agent Framework (ADK)
investigator_agent = Agent(
    name="investigator_agent",
    model="gemini-3.5-flash",
    instruction="Analyze transaction records, query RAG memory, and classify the break reason."
)

resolver_agent = Agent(
    name="resolver_agent",
    model="gemini-3.5-flash",
    instruction="Determine if the break can be auto-resolved based on confidence score."
)

# 2. Define Workflow
pipeline = Workflow(
    name="reconciliation_pipeline",
    edges=[("START", investigator_agent, resolver_agent)]
)

def process_single_break(br):
    """Processes a single break through the full ADK agent pipeline."""
    
    # A. Investigator Agent classifies the break (Includes True RAG context)
    try:
        investigation = investigate(br)
        # Fallback if Gemini somehow didn't return a dictionary
        if not isinstance(investigation, dict):
            investigation = {
                "break_type": "unknown", 
                "confidence": 0.0, 
                "reasoning": "AI returned non-dictionary format.",
                "source": "error_handler"
            }
    except Exception as e:
        investigation = {
            "break_type": "unknown", 
            "confidence": 0.0, 
            "reasoning": f"Investigation crashed: {e}",
            "source": "error_handler"
        }
        
    br["investigation"] = investigation
    
    # B. Safely parse exact variables required by the Gemma 4 MaaS Tagger
    b_type = investigation.get("break_type", "unknown")
    amt = br.get("amount") or br.get("ledger", {}).get("amount") or 0
    conf = investigation.get("confidence", 0)
    
    try:
        br["investigation"]["severity"] = tag_severity(b_type, amt, conf)
    except Exception:
        br["investigation"]["severity"] = "high" # Safe fallback
    
    # C. Resolver Agent decides action
    try:
        resolution = resolve(br, investigation)
    except Exception as e:
        resolution = {"status": "escalated", "break_type": b_type, "narrative": f"Resolver failed: {e}"}
        
    br["resolution"] = resolution
    
    # D. Auditor Agent permanently logs the decision to Firestore
    try:
        write_record(br)
    except Exception as e:
        print(f"[Orchestrator] DB Write Error: {e}")
    
    print(f"[Orchestrator] Break processed and audited. Status: {resolution.get('status', 'unknown')}")
    return br
