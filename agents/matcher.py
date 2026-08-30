"""Matcher Agent - deterministic, no LLM. Uses Pandas to classify exact matches and break reasons."""
import pandas as pd
import numpy as np

def run(ledger_path: str, processor_path: str):
    try:
        df_ledger = pd.read_csv(ledger_path)
        df_processor = pd.read_csv(processor_path)
    except Exception as e:
        print(f"[Matcher] Error reading CSVs: {e}")
        return {"matched": [], "breaks": []}

    # Standardize columns
    df_ledger.columns = [c.strip().lower() for c in df_ledger.columns]
    df_processor.columns = [c.strip().lower() for c in df_processor.columns]

    req_cols = ['transaction_id', 'amount', 'currency']
    for col in req_cols:
        if col not in df_ledger.columns: df_ledger[col] = ""
        if col not in df_processor.columns: df_processor[col] = ""

    # MERGE ONLY ON ID so we can compare amounts side-by-side
    merged = pd.merge(
        df_ledger, 
        df_processor, 
        on='transaction_id', 
        how='outer', 
        indicator=True,
        suffixes=('_ledger', '_processor')
    )

    merged = merged.replace({np.nan: ""})
    merged = merged.fillna("")

    matched = []
    breaks = []

    for _, row in merged.iterrows():
        _merge = row['_merge']
        t_id = row['transaction_id']

        # Helper to dynamically rebuild the dictionary for the AI Swarm
        l_dict = {k.replace('_ledger', ''): v for k, v in row.items() if '_ledger' in k or k == 'transaction_id'}
        p_dict = {k.replace('_processor', ''): v for k, v in row.items() if '_processor' in k or k == 'transaction_id'}

        if _merge == 'left_only':
            breaks.append({
                "transaction_id": t_id, "amount": row['amount_ledger'],
                "ledger": l_dict, "processor": {}, "reason": "missing_entry"
            })
        elif _merge == 'right_only':
            breaks.append({
                "transaction_id": t_id, "amount": row['amount_processor'],
                "ledger": {}, "processor": p_dict, "reason": "missing_entry"
            })
        else: # Both exist, now we check for discrepancies!
            try:
                amt_l = float(row['amount_ledger']) if row['amount_ledger'] != "" else 0.0
                amt_p = float(row['amount_processor']) if row['amount_processor'] != "" else 0.0
            except:
                amt_l, amt_p = 0.0, 0.0

            amount_diff = abs(amt_l - amt_p)

            # 1. Check for Amount Mismatch (Tolerance of 1 cent)
            if amount_diff > 0.01:
                breaks.append({
                    "transaction_id": t_id, "amount": amt_l,
                    "ledger": l_dict, "processor": p_dict, "reason": "amount_mismatch",
                })
            # 2. Check for Timestamp Mismatch (if your CSV has a timestamp column)
            elif 'timestamp_ledger' in row and 'timestamp_processor' in row and row['timestamp_ledger'] != row['timestamp_processor']:
                breaks.append({
                    "transaction_id": t_id, "amount": amt_l,
                    "ledger": l_dict, "processor": p_dict, "reason": "timestamp_mismatch"
                })
            # 3. Otherwise, it is an exact match!
            else:
                matched.append(row.to_dict())

    return {
        "matched": matched,
        "breaks": breaks
    }
