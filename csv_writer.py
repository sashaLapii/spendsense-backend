#!/usr/bin/env python3
"""
csv_writer.py - CSV export for SpendSense
Universal format for both original and RBC formats
"""

import csv
from pathlib import Path
from typing import List

from unified_parser import UnifiedTransaction


def write_csv_unified(transactions: List[UnifiedTransaction], out_path: Path):
    """
    Write transactions to CSV in universal format
    
    Args:
        transactions: List of UnifiedTransaction objects
        out_path: Output CSV file path
    """
    if not transactions:
        print("No transactions to write")
        return
    
    out_path = Path(out_path)
    
    fieldnames = [
        "Date",
        "Description",
        "Amount_CAD",
        "Currency",
        "Original_Amount",
        "Exchange_Rate",
        "Cardmember",
        "Posting_Date",
        "Merchant_Country",
        "Notes",
        "Format",
    ]
    
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for tx in transactions:
            writer.writerow({
                "Date": tx.date,
                "Description": tx.description,
                "Amount_CAD": f"{tx.amount_cad:.2f}",
                "Currency": tx.currency,
                "Original_Amount": f"{tx.original_amount:.2f}",
                "Exchange_Rate": f"{tx.exchange_rate:.6f}",
                "Cardmember": tx.cardmember or "",
                "Posting_Date": tx.posting_date or "",
                "Merchant_Country": tx.merchant_country or "",
                "Notes": tx.notes,
                "Format": tx.format_type,
            })