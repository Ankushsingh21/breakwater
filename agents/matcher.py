"""Matcher Agent - deterministic, no LLM. Matches ledger vs processor records using Pandas."""
import pandas as pd

AMOUNT_TOLERANCE = 0.01

def run(ledger_path="data/ledger.csv", processor_path="data/processor.csv"):
    try:
        ledger = pd.read_csv(ledger_path)
        processor = pd.read_csv(processor_path)
    except Exception as e:
        print(f"[Matcher] Error reading data: {e}")
        return {"matched": [], "breaks": [], "total_ledger": 0, "total_processor": 0}

    breaks = []
    matched = []
    
    # Convert to dicts for fast iteration
    ledger_records = ledger.to_dict('records')
    proc_records = processor.to_dict('records')
    
    proc_by_id = {}
    for p in proc_records:
        proc_by_id.setdefault(p["transaction_id"], []).append(p)
        
    seen_ledger_ids = set()

    for l in ledger_records:
        seen_ledger_ids.add(l["transaction_id"])
        candidates = proc_by_id.get(l["transaction_id"], [])

        if not candidates:
            breaks.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": None, "reason": "no_processor_match"})
            continue
        if len(candidates) > 1:
            breaks.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": candidates, "reason": "multiple_processor_matches"})
            continue

        p = candidates[0]
        amount_diff = abs(float(l["amount"]) - float(p["amount"]))
        
        if amount_diff > AMOUNT_TOLERANCE:
            breaks.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": p, "reason": "amount_mismatch", "amount_diff": amount_diff})
            continue
        if str(l["timestamp"]) != str(p["timestamp"]):
            breaks.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": p, "reason": "timestamp_mismatch"})
            continue

        matched.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": p})

    # Find processor-only records
    for txn_id, rows in proc_by_id.items():
        if txn_id not in seen_ledger_ids:
            for p in rows:
                breaks.append({"transaction_id": txn_id, "ledger": None, "processor": p, "reason": "processor_only"})

    return {
        "matched": matched, 
        "breaks": breaks, 
        "total_ledger": len(ledger), 
        "total_processor": len(processor)
    }

if __name__ == "__main__":
    result = run()
    print(f"matched={len(result['matched'])} breaks={len(result['breaks'])}")
