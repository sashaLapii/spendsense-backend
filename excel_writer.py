#!/usr/bin/env python3
"""
excel_writer.py - Excel export for SpendSense
Supports both original and RBC formats
"""

from pathlib import Path
from typing import List
import pandas as pd

from unified_parser import UnifiedTransaction


def write_excel_unified(
    transactions: List[UnifiedTransaction],
    out_path: Path,
    format_type: str,
    do_summary: bool = True
):
    """
    Write transactions to Excel with format-specific sheets
    
    Args:
        transactions: List of UnifiedTransaction objects
        out_path: Output Excel file path
        format_type: "original" or "rbc"
        do_summary: Whether to create summary sheets
    """
    if not transactions:
        print("No transactions to write")
        return
    
    out_path = Path(out_path)
    
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        wb = writer.book
        
        # Formats
        wrap = wb.add_format({'text_wrap': True})
        money = wb.add_format({"num_format":"$#,##0.00;[Red]-$#,##0.00","align":"right"})
        hdr = wb.add_format({"bold": True})
        total_fmt = wb.add_format({"bold": True, "top":1})
        
        # Main transactions sheet
        if format_type == "original":
            _write_original_format(transactions, writer, wrap, money, hdr, total_fmt, do_summary)
        elif format_type == "rbc":
            _write_rbc_format(transactions, writer, wrap, money, hdr, total_fmt, do_summary)
        else:
            _write_generic_format(transactions, writer, wrap, money, hdr)


def _write_original_format(transactions, writer, wrap, money, hdr, total_fmt, do_summary):
    """Write Excel for original format (with Cardmember)"""
    # Create DataFrame
    data = []
    for tx in transactions:
        data.append({
            "Date": tx.date,
            "Description": tx.description,
            "Cardmember": tx.cardmember or "",
            "Amount": tx.amount_cad,
            "Currency": tx.currency,
            "Notes": tx.notes,
        })
    
    df = pd.DataFrame(data)
    
    # Transactions sheet
    df.to_excel(writer, sheet_name="Transactions", index=False)
    ws_tx = writer.sheets["Transactions"]
    ws_tx.set_row(0, None, hdr)
    ws_tx.set_column(0, 0, 12)  # Date
    ws_tx.set_column(1, 1, 60, wrap)  # Description
    ws_tx.set_column(2, 2, 24)  # Cardmember
    ws_tx.set_column(3, 3, 14, money)  # Amount
    ws_tx.set_column(4, 4, 8)  # Currency
    ws_tx.set_column(5, 5, 20)  # Notes
    ws_tx.freeze_panes(1, 0)
    
    if do_summary and not df.empty:
        members = [m for m in df["Cardmember"].unique() if m]
        members.sort()
        
        # Wide sheet
        wide = pd.DataFrame({"Date": df["Date"], "Description": df["Description"]})
        for m in members:
            wide[m] = df.apply(lambda r: r["Amount"] if r["Cardmember"]==m else None, axis=1)
        
        wide.to_excel(writer, sheet_name="Wide", index=False)
        ws = writer.sheets["Wide"]
        ws.set_row(0, None, hdr)
        ws.set_column(0, 0, 12)
        ws.set_column(1, 1, 60, wrap)
        for idx in range(2, 2+len(members)):
            ws.set_column(idx, idx, 14, money)
        ws.freeze_panes(1, 0)
        
        # Totals row
        nrows = len(wide) + 1
        ws.write(nrows, 1, "ИТОГО", total_fmt)
        for c_idx in range(2, 2+len(members)):
            col_letter = chr(ord('A') + c_idx)
            ws.write_formula(nrows, c_idx, f"=SUM({col_letter}2:{col_letter}{nrows})", money)
        
        # Summary sheet
        sum_data = {m: float(df.loc[df["Cardmember"]==m, "Amount"].sum()) for m in members}
        sum_data["TOTAL"] = float(df["Amount"].sum())
        sum_df = pd.DataFrame([sum_data])
        sum_df.to_excel(writer, sheet_name="Summary", index=False)
        ws2 = writer.sheets["Summary"]
        for i in range(len(members)+1):
            ws2.set_column(i, i, 16, money)
        ws2.set_row(0, None, hdr)
        
        # Per-member sheets
        for m in members:
            sub = df[df["Cardmember"]==m].copy()
            name = (m or "Member")[:31]
            sub.to_excel(writer, sheet_name=name, index=False)
            wsx = writer.sheets[name]
            wsx.set_row(0, None, hdr)
            wsx.set_column(0, 0, 12)
            wsx.set_column(1, 1, 60, wrap)
            wsx.set_column(2, 2, 24)
            wsx.set_column(3, 3, 14, money)
            wsx.set_column(4, 4, 8)
            wsx.set_column(5, 5, 20)
            wsx.freeze_panes(1, 0)


def _write_rbc_format(transactions, writer, wrap, money, hdr, total_fmt, do_summary):
    """Write Excel for RBC format (simplified - no Type column)"""
    # Create DataFrame
    data = []
    for tx in transactions:
        data.append({
            "Date": tx.date,
            "Posting_Date": tx.posting_date or "",
            "Description": tx.description,
            "Country": tx.merchant_country or "",
            "Currency": tx.currency,
            "Original_Amount": tx.original_amount,
            "CAD_Amount": tx.amount_cad,
            "Exchange_Rate": tx.exchange_rate,
        })
    
    df = pd.DataFrame(data)
    
    # Transactions sheet
    df.to_excel(writer, sheet_name="Transactions", index=False)
    ws_tx = writer.sheets["Transactions"]
    ws_tx.set_row(0, None, hdr)
    ws_tx.set_column(0, 0, 12)  # Date
    ws_tx.set_column(1, 1, 12)  # Posting_Date
    ws_tx.set_column(2, 2, 50, wrap)  # Description
    ws_tx.set_column(3, 3, 10)  # Country
    ws_tx.set_column(4, 4, 8)  # Currency
    ws_tx.set_column(5, 5, 14, money)  # Original_Amount
    ws_tx.set_column(6, 6, 14, money)  # CAD_Amount
    ws_tx.set_column(7, 7, 12)  # Exchange_Rate
    ws_tx.freeze_panes(1, 0)
    
    if do_summary and not df.empty:
        # Summary: Spending vs Payments
        spending = df[df["CAD_Amount"] > 0]["CAD_Amount"].sum()
        payments = abs(df[df["CAD_Amount"] < 0]["CAD_Amount"].sum())
        net = df["CAD_Amount"].sum()
        
        summary_data = [{
            "Category": "Траты (Spending)",
            "Total_CAD": float(spending)
        }, {
            "Category": "Пополнения (Payments)",
            "Total_CAD": float(payments)
        }, {
            "Category": "Итого (Net)",
            "Total_CAD": float(net)
        }]
        
        sum_df = pd.DataFrame(summary_data)
        sum_df.to_excel(writer, sheet_name="Summary", index=False)
        ws2 = writer.sheets["Summary"]
        ws2.set_row(0, None, hdr)
        ws2.set_column(0, 0, 24)
        ws2.set_column(1, 1, 16, money)
        
        # Summary by Currency
        curr_summary = df.groupby("Currency").agg({
            "Original_Amount": "sum",
            "CAD_Amount": "sum"
        }).reset_index()
        curr_summary.to_excel(writer, sheet_name="Summary_by_Currency", index=False)
        ws3 = writer.sheets["Summary_by_Currency"]
        ws3.set_row(0, None, hdr)
        ws3.set_column(0, 0, 12)
        ws3.set_column(1, 1, 16, money)
        ws3.set_column(2, 2, 16, money)
        
        # Summary by Country
        if df["Country"].notna().any():
            country_summary = df[df["Country"]!=""].groupby("Country")["CAD_Amount"].sum().reset_index()
            country_summary.columns = ["Country", "Total_CAD"]
            country_summary = country_summary.sort_values("Total_CAD", ascending=False)
            country_summary.to_excel(writer, sheet_name="Summary_by_Country", index=False)
            ws4 = writer.sheets["Summary_by_Country"]
            ws4.set_row(0, None, hdr)
            ws4.set_column(0, 0, 12)
            ws4.set_column(1, 1, 16, money)


def _write_generic_format(transactions, writer, wrap, money, hdr):
    """Write Excel for unknown format (generic)"""
    data = []
    for tx in transactions:
        data.append({
            "Date": tx.date,
            "Description": tx.description,
            "Amount_CAD": tx.amount_cad,
            "Currency": tx.currency,
            "Original_Amount": tx.original_amount,
            "Exchange_Rate": tx.exchange_rate,
            "Notes": tx.notes,
        })
    
    df = pd.DataFrame(data)
    df.to_excel(writer, sheet_name="Transactions", index=False)
    ws = writer.sheets["Transactions"]
    ws.set_row(0, None, hdr)
    ws.set_column(0, 0, 12)
    ws.set_column(1, 1, 60, wrap)
    ws.set_column(2, 2, 14, money)
    ws.set_column(3, 3, 8)
    ws.set_column(4, 4, 14, money)
    ws.set_column(5, 5, 12)
    ws.set_column(6, 6, 30)
    ws.freeze_panes(1, 0)