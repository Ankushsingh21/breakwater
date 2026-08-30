"""Matcher Agent - deterministic, no LLM. Uses Pandas to clear exact matches."""
import pandas as pd

def run(ledger_path: str, processor_path: str):
    try:
        df_ledger = pd.read_csv(ledger_path)
        df_processor = pd.read_csv(processor_path)
    except Exception as e:
        print(f"[Matcher] Error reading CSVs: {e}")
        return {"matched": [], "breaks": []}

    # Standardize column names
    df_ledger.columns = [c.strip().lower() for c in df_ledger.columns]
    df_processor.columns = [c.strip().lower() for c in df_processor.columns]

    # Ensure required columns exist
    req_cols = ['transaction_id', 'amount', 'currency']
    for col in req_cols:
        if col not in df_ledger.columns: df_ledger[col] = None
        if col not in df_processor.columns: df_processor[col] = None

    # Exact Match on ID and Amount
    merged = pd.merge(
        df_ledger, 
        df_processor, 
        on=['transaction_id', 'amount'], 
        how='outer', 
        indicator=True,
        suffixes=('_ledger', '_processor')
    )

    matched = merged[merged['_merge'] == 'both'].to_dict('records')
    unmatched_ledger = merged[merged['_merge'] == 'left_only'].to_dict('records')
    unmatched_processor = merged[merged['_merge'] == 'right_only'].to_dict('records')

    breaks = []
    
    for row in unmatched_ledger:
        breaks.append({
            "transaction_id": row.get("transaction_id"),
            "amount": row.get("amount"),
            "ledger": row,
            "processor": None,
            "reason": "Missing in Processor"
        })
        
    for row in unmatched_processor:
        breaks.append({
            "transaction_id": row.get("transaction_id"),
            "amount": row.get("amount"),
            "ledger": None,
            "processor": row,
            "reason": "Missing in Ledger"
        })

    return {
        "matched": matched,
        "breaks": breaks
    }
