"""Orchestrator - wires Matcher -> Investigator -> Resolver -> Auditor into one
asynchronous pipeline. This is the multi-agent core of Breakwater."""
from agents import matcher, investigator, severity_tagger, resolver, auditor


def run_pipeline(ledger_path="data/ledger.csv", processor_path="data/processor.csv"):
    match_result = matcher.run(ledger_path, processor_path)
    results = []

    for br in match_result["breaks"]:
        investigation = investigator.investigate(br)
        investigation["severity"] = severity_tagger.tag(br, investigation)
        resolution = resolver.resolve(br, investigation)
        entry = auditor.record(br, investigation, resolution)
        results.append(entry)

    total_breaks = len(match_result["breaks"])
    memory_hits = sum(1 for r in results if r["investigation"].get("source") == "pattern_memory")
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    for r in results:
        sev = r["investigation"].get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    summary = {
        "total_ledger": match_result["total_ledger"],
        "total_processor": match_result["total_processor"],
        "auto_matched": len(match_result["matched"]),
        "breaks_found": total_breaks,
        "auto_resolved": sum(1 for r in results if r["resolution"]["status"] == "auto_resolved"),
        "escalated": sum(1 for r in results if r["resolution"]["status"] == "escalated"),
        "memory_hit_rate": round(memory_hits / total_breaks, 3) if total_breaks else 0,
        "severity_breakdown": severity_counts,
    }
    return {"summary": summary, "breaks": results}


if __name__ == "__main__":
    out = run_pipeline()
    print(out["summary"])
