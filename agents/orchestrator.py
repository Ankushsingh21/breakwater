"""
Orchestrates the reconciliation workflow using the Google Agent Development Kit (ADK).
"""
from google.adk import Agent, Workflow
from agents.matcher import run as run_matcher
from agents.investigator import investigate
from agents.severity_tagger import tag as tag_severity
from agents.resolver import resolve
from agents.auditor import record

# 1. Define the Agents using official ADK syntax and latest models
investigator_agent = Agent(
    name="investigator_agent",
    model="gemini-2.0-flash",
    instruction="Analyze transaction records and classify the break reason."
)

resolver_agent = Agent(
    name="resolver_agent",
    model="gemini-2.0-flash",
    instruction="Determine if the break can be auto-resolved based on confidence score."
)

# 2. Define the autonomous ADK Workflow graph
pipeline = Workflow(
    name="reconciliation_pipeline",
    edges=[("START", investigator_agent, resolver_agent)]
)

def run_pipeline():
    """Entrypoint called by FastAPI. Runs the whole batch asynchronously."""
    
    # Step 1: Run deterministic matching (No LLM Cost)
    match_results = run_matcher()
    
    processed_breaks = []
    auto_resolved_count = 0
    escalated_count = 0
    memory_hits = 0

    # Step 2: Route each break through the Agentic Workflow
    for br in match_results["breaks"]:
        # A. Investigator Agent classifies the break
        investigation = investigate(br)
        
        # B. Severity Tagger (Gemma) tags business risk
        investigation["severity"] = tag_severity(br, investigation)
        
        # C. Resolver Agent decides action
        resolution = resolve(br, investigation)
        
        # D. Auditor Agent permanently logs the decision
        final_record = record(br, investigation, resolution)
        processed_breaks.append(final_record)
        
        # Track stats for the Dashboard
        if resolution["status"] == "auto_resolved":
            auto_resolved_count += 1
        else:
            escalated_count += 1
            
        if investigation.get("source") == "pattern_memory":
            memory_hits += 1

    # Step 3: Return stats payload to the UI
    total_breaks = len(match_results["breaks"])
    summary = {
        "total_ledger": match_results["total_ledger"],
        "auto_matched": len(match_results["matched"]),
        "breaks_found": total_breaks,
        "auto_resolved": auto_resolved_count,
        "escalated": escalated_count,
        "memory_hit_rate": (memory_hits / total_breaks) if total_breaks > 0 else 0
    }

    return {"summary": summary, "breaks": processed_breaks}
