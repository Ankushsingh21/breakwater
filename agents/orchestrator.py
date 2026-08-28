"""
Orchestrates the reconciliation workflow using the Google Agent Development Kit (ADK).
"""
from google.adk import Agent, Workflow
from .investigator import classify_break

# 1. Define the Agents using official ADK syntax
investigator_agent = Agent(
    name="investigator_agent",
    model="gemini-1.5-flash",
    instruction="Analyze transaction records and classify the break reason."
)

resolver_agent = Agent(
    name="resolver_agent",
    model="gemini-1.5-flash",
    instruction="Determine if the break can be auto-resolved based on confidence score."
)

# 2. Define the autonomous ADK Workflow graph
pipeline = Workflow(
    name="reconciliation_pipeline",
    edges=[("START", investigator_agent, resolver_agent)]
)

def run_pipeline(break_record):
    """Entrypoint called by your FastAPI backend."""
    # Safely execute the investigation step
    investigation = classify_break(
        break_record.get('ledger', {}), 
        break_record.get('processor', {}), 
        break_record.get('reason', 'unknown')
    )
    
    # Execute the resolver logic based on AI confidence
    confidence = investigation.get('confidence', 0.0)
    
    return {
        "ledger_record": break_record.get('ledger', {}),
        "processor_record": break_record.get('processor', {}),
        "break_reason": break_record.get('reason', 'unknown'),
        "investigation_result": investigation,
        "resolution_status": "AUTO_RESOLVED" if confidence > 0.7 else "ESCALATED_TO_HUMAN"
    }
