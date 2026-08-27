"""Minimal test - confirms the Matcher correctly separates matched vs break records
on a small synthetic fixture."""
import csv
import os
import tempfile

from agents import matcher


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["transaction_id", "amount", "currency", "timestamp", "counterparty"])
        writer.writeheader()
        writer.writerows(rows)


def test_matcher_finds_exact_matches_and_breaks():
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = os.path.join(tmp, "ledger.csv")
        processor_path = os.path.join(tmp, "processor.csv")

        base = {"currency": "USD", "timestamp": "2026-01-01T00:00:00", "counterparty": "Acme"}
        ledger_rows = [
            {**base, "transaction_id": "T1", "amount": "100.00"},
            {**base, "transaction_id": "T2", "amount": "50.00"},
        ]
        processor_rows = [
            {**base, "transaction_id": "T1", "amount": "100.00"},
            {**base, "transaction_id": "T2", "amount": "999.00"},
        ]
        _write_csv(ledger_path, ledger_rows)
        _write_csv(processor_path, processor_rows)

        result = matcher.run(ledger_path, processor_path)
        assert len(result["matched"]) == 1
        assert len(result["breaks"]) == 1
        assert result["breaks"][0]["reason"] == "amount_mismatch"
