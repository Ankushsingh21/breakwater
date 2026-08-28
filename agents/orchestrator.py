"""
Orchestrates the reconciliation workflow using the Google Agent Development Kit (ADK) 
State Graph. This makes the multi-agent decision process autonomous and observable.
"""
from google_adk.agents import StateGraph, AgentNode
from google_adk.memory import FirestoreMemory
from .investigator import classify_break
from .resolver import auto_resolve

# Define the state payload that passes between agents
class ReconciliationState(dict):
    ledger_record: dict
    processor_record: dict
    break_reason: str
    investigation_result: dict
    resolution_status: str

# Node 1: The Investigator Agent
def run_investigator(state: ReconciliationState):
    print(f"[ADK] Investigator Agent analyzing break: {state['break_reason']}")
    result = classify_break(
        state['ledger_record'], 
        state['processor_record'], 
        state['break_reason']
    )
    state['investigation_result'] = result
    return state

# Node 2: The Resolver Agent
def run_resolver(state: ReconciliationState):
    confidence = state['investigation_result'].get('confidence', 0.0)
    print(f"[ADK] Resolver Agent received confidence: {confidence}")
    
    if confidence > 0.7:
        state['resolution_status'] = "AUTO_RESOLVED"
    else:
        state['resolution_status'] = "ESCALATED_TO_HUMAN"
    return state

def build_agentic_pipeline():
    """Builds the ADK execution graph."""
    graph = StateGraph(ReconciliationState)
    
    # Register our agents as nodes
    graph.add_node("investigator", run_investigator)
    graph.add_node("resolver", run_resolver)
    
    # Define the autonomous workflow edges
    graph.add_edge("investigator", "resolver")
    graph.set_entry_point("investigator")
    
    # Compile the agentic workflow
    return graph.compile()

# Initialize the global pipeline instance
pipeline = build_agentic_pipeline()

def run_pipeline(break_record):
    """Entrypoint called by your FastAPI backend."""
    initial_state = {
        "ledger_record": break_record.get('ledger', {}),
        "processor_record": break_record.get('processor', {}),
        "break_reason": break_record.get('reason', 'unknown')
    }
    
    # Execute the autonomous graph
    final_state = pipeline.invoke(initial_state)
    return final_state
