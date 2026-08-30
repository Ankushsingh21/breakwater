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
    investigation = investigate(br)
    br["investigation"] = investigation
    
    # B. Parse exact variables required by the Gemma 4 MaaS Tagger
    b_type = investigation.get("break_type", "unknown")
    amt = br.get("amount") or br.get("ledger", {}).get("amount") or 0
    conf = investigation.get("confidence", 0)
    
    br["investigation"]["severity"] = tag_severity(b_type, amt, conf)
    
    # C. Resolver Agent decides action
    resolution = resolve(br, investigation)
    br["resolution"] = resolution
    
    # D. Auditor Agent permanently logs the decision to Firestore
    write_record(br)
    
    print(f"[Orchestrator] Break processed and audited. Status: {resolution.get('status')}")
    return br
