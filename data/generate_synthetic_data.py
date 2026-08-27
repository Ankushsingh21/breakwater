"""Generate synthetic ledger + processor feeds with injected reconciliation breaks."""
import argparse
import csv
import os
import random
from datetime import datetime, timedelta

CURRENCIES = ["USD", "EUR", "GBP", "INR"]
COUNTERPARTIES = ["Acme Corp", "Globex", "Initech", "Umbrella Ltd", "Stark Industries", "Wayne Enterprises"]


def rand_amount():
    return round(random.uniform(10, 50000), 2)


def rand_ts(base):
    return base + timedelta(minutes=random.randint(0, 60 * 24 * 30))


def generate(n_rows=5000, break_rate=0.08, seed=42, out_dir="data"):
    random.seed(seed)
    base = datetime(2026, 1, 1)
    ledger, processor = [], []

    for i in range(n_rows):
        row = {
            "transaction_id": f"TXN{i:07d}",
            "amount": rand_amount(),
            "currency": random.choice(CURRENCIES),
            "timestamp": rand_ts(base).isoformat(),
            "counterparty": random.choice(COUNTERPARTIES),
        }
        ledger.append(dict(row))
        processor.append(dict(row))

    n_breaks = int(n_rows * break_rate)
    break_types = ["duplicate", "timing_diff", "currency_rounding", "missing_entry"]
    break_ids = random.sample(range(n_rows), n_breaks)

    for idx, i in enumerate(break_ids):
        kind = break_types[idx % len(break_types)]
        if kind == "duplicate":
            processor.append(dict(processor[i]))
        elif kind == "timing_diff":
            ts = datetime.fromisoformat(processor[i]["timestamp"])
            processor[i]["timestamp"] = (ts + timedelta(hours=random.randint(6, 48))).isoformat()
        elif kind == "currency_rounding":
            processor[i]["amount"] = round(processor[i]["amount"] * random.uniform(0.995, 1.005), 2)
        elif kind == "missing_entry":
            processor[i] = None

    processor = [p for p in processor if p is not None]

    os.makedirs(out_dir, exist_ok=True)
    for name, rows in [("ledger", ledger), ("processor", processor)]:
        path = os.path.join(out_dir, f"{name}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["transaction_id", "amount", "currency", "timestamp", "counterparty"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} rows to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--break-rate", type=float, default=0.08)
    parser.add_argument("--out-dir", type=str, default="data")
    args = parser.parse_args()
    generate(n_rows=args.rows, break_rate=args.break_rate, out_dir=args.out_dir)
