"""Matcher Agent - deterministic, no LLM. Matches ledger vs processor records."""
import csv
from collections import defaultdict

AMOUNT_TOLERANCE = 0.01


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def run(ledger_path="data/ledger.csv", processor_path="data/processor.csv"):
    ledger = load_csv(ledger_path)
    processor = load_csv(processor_path)

    proc_by_id = defaultdict(list)
    for row in processor:
        proc_by_id[row["transaction_id"]].append(row)

    matched, breaks = [], []
    seen_ledger_ids = set()

    for l in ledger:
        seen_ledger_ids.add(l["transaction_id"])
        candidates = proc_by_id.get(l["transaction_id"], [])

        if len(candidates) == 0:
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
        if l["timestamp"] != p["timestamp"]:
            breaks.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": p, "reason": "timestamp_mismatch"})
            continue

        matched.append({"transaction_id": l["transaction_id"], "ledger": l, "processor": p})

    for txn_id, rows in proc_by_id.items():
        if txn_id not in seen_ledger_ids:
            for p in rows:
                breaks.append({"transaction_id": txn_id, "ledger": None, "processor": p, "reason": "processor_only"})

    return {"matched": matched, "breaks": breaks, "total_ledger": len(ledger), "total_processor": len(processor)}


if __name__ == "__main__":
    result = run()
    print(f"matched={len(result['matched'])} breaks={len(result['breaks'])}")
