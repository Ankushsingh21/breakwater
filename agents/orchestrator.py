from google.adk import Agent, Workflow
from agents.investigator import investigate
from agents.severity_tagger import tag as tag_severity
from agents.resolver import resolve
from agents.auditor import record

# 1. Define the Agents using Gemini 3.5 Flash
investigator_agent = Agent(
    name="investigator_agent",
    model="gemini-3.5-flash",
    instruction="Analyze transaction records and classify the break reason."
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
    """Processes a single break through the full agent pipeline."""
    # A. Investigator Agent classifies the break
    investigation = investigate(br)
    
    # B. Severity Tagger (Gemma 4 MaaS) tags business risk
    investigation["severity"] = tag_severity(br, investigation)
    
    # C. Resolver Agent decides action
    resolution = resolve(br, investigation)
    
    # D. Auditor Agent permanently logs the decision
    final_record = record(br, investigation, resolution)
    
    print(f"[Orchestrator] Break processed and audited. Status: {resolution['status']}")
    return final_record
