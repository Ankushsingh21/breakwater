"""Severity Tagger Agent - lightweight priority classification using Gemma.
Runs after the Investigator, before the Resolver, purely for dashboard triage."""
from services.gemma_client import tag_severity


def tag(break_record, investigation):
    l = break_record.get("ledger") or {}
    p = break_record.get("processor") or {}
    amount = l.get("amount") or (p.get("amount") if p else None)
    return tag_severity(investigation.get("break_type"), amount, investigation.get("confidence", 0))
