#!/usr/bin/env python3
"""
unified_parser.py - Unified PDF parser for SpendSense
Supports both original format and RBC format
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Literal
from datetime import datetime

import pdfplumber
import pandas as pd


# ============================================================================
# Common data structure
# ============================================================================

@dataclass
class UnifiedTransaction:
    """Universal transaction structure for both formats"""
    date: str                           # ISO format YYYY-MM-DD
    description: str
    amount_cad: float                   # always in CAD (positive = spending, negative = payment)
    currency: str                       # original currency
    original_amount: float              # amount in original currency
    exchange_rate: float                # exchange rate
    cardmember: Optional[str] = None    # for original format
    posting_date: Optional[str] = None  # for RBC format
    merchant_country: Optional[str] = None  # for RBC format
    notes: str = ""                     # additional info (only for original format)
    format_type: str = "unknown"        # "original" or "rbc"


# ============================================================================
# Format detection
# ============================================================================

def detect_pdf_format(pdf_path: Path) -> Literal["original", "rbc", "unknown"]:
    """
    Detect PDF format by analyzing first few pages
    Returns: "original", "rbc", or "unknown"
    """
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            # Check first 3 pages
            text_sample = ""
            for i, page in enumerate(pdf.pages[:3]):
                text = page.extract_text() or ""
                text_sample += text + "\n"
                if len(text_sample) > 5000:  # enough sample
                    break
            
            # RBC format indicators
            rbc_indicators = [
                r"JAN \d{2} JAN \d{2}",
                r"FEB \d{2} FEB \d{2}",
                r"Foreign Currency",
                r"TOTAL ACCOUNT BALANCE",
                r"Exchange rate\s*-\s*[\d.]+",
            ]
            
            # Original format indicators
            original_indicators = [
                r"JASON DIMAND",
                r"GRIGORII VOLK",
                r"\d{1,2}\s+[A-Za-z]{3}\.?\s+\d{4}",  # "1 Jan 2024"
                r"Cardmember",
                r"\bFS\b",  # FlexibleFlag
            ]
            
            rbc_score = sum(1 for pattern in rbc_indicators if re.search(pattern, text_sample, re.I))
            original_score = sum(1 for pattern in original_indicators if re.search(pattern, text_sample, re.I))
            
            if rbc_score >= 2:
                return "rbc"
            elif original_score >= 2:
                return "original"
            else:
                return "unknown"
    except Exception:
        return "unknown"


# ============================================================================
# Original format parser (from app_pyside6_v18.py)
# ============================================================================

MONTHS = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}
DATE_PATTERNS = [
    r"(?P<date>\b\d{1,2}\s+[A-Za-z]{3}\.?\s+\d{2,4}\b)",
    r"(?P<date>\b\d{1,2}/\d{1,2}/\d{2,4}\b)"
]
AMOUNT_PATTERN = r"(?P<amount>\(?-?\$?\s*[\d.,]+(?:\.\d{2}|\,\d{2})?\)?)"
CARDMEMBERS_HINTS = ["JASON DIMAND", "GRIGORII VOLK", "GRIGORII", "JASON"]

HEADER_RE_SINGLE = re.compile(r"^-?\s*\d{1,2}\s+[A-Za-z]{3}\.?$", re.I)
HEADER_RE_RANGE  = re.compile(r"\b\d{1,2}\s+[A-Za-z]{3}\.?\s+\d{4}\s*-\s*\d{1,2}\s+[A-Za-z]{3}\.?\s+\d{4}\b", re.I)


def _parse_iso_date(s: str) -> str:
    m = re.match(r"^\s*(\d{1,2})\s+([A-Za-z]{3})\.?\s+(\d{2,4})\s*$", s)
    if m:
        d = int(m.group(1))
        mon_abbr = m.group(2)[:3].title()
        y = int(m.group(3))
        y = y + 2000 if y < 100 else y
        mon = MONTHS.get(mon_abbr)
        if mon:
            return datetime(y, mon, d).date().isoformat()
    
    m = re.match(r"^\s*(\d{1,2})/(\d{1,2})/(\d{2,4})\s*$", s)
    if m:
        d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        if mth > 12 and d <= 12:
            d, mth = mth, d
        try:
            return datetime(y, mth, d).date().isoformat()
        except:
            return s.strip()
    return s.strip()


def _amount_to_float(text: str) -> float:
    t = text.replace("USD","").replace("\u00A0"," ").strip()
    neg = t.startswith("-") or (t.startswith("(") and t.endswith(")"))
    if "," in t and "." not in t:
        t = t.replace(",", ".")
    t = t.replace("(", "").replace(")", "").replace("$", "").replace(" ", "").replace(",", "")
    if t == "" or t == "-":
        return 0.0
    try:
        val = float(t)
    except:
        val = float(re.sub(r"[^\d.]", "", t) or 0)
    if 2000 <= val <= 2099 and "." not in text:
        raise ValueError("Header year captured as amount")
    return -abs(val) if neg else val


def _lines_from_words(page, y_tol=3):
    words = page.extract_words(use_text_flow=True) or []
    if not words:
        return []
    words.sort(key=lambda w: (round(w.get('top',0)/y_tol), w.get('x0',0)))
    lines, cur_key, cur_words = [], None, []
    for w in words:
        key = round(w.get('top',0)/y_tol)
        if key != cur_key and cur_words:
            lines.append(" ".join([cw['text'] for cw in cur_words]))
            cur_words = []
        cur_key = key
        cur_words.append(w)
    if cur_words:
        lines.append(" ".join([cw['text'] for cw in cur_words]))
    return lines


def parse_original_format(pdf_path: Path) -> List[UnifiedTransaction]:
    """Parse original format PDF (from app_pyside6_v18.py)"""
    rows = []
    
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1, y_tolerance=3)
            raw_lines = text.splitlines() if text else _lines_from_words(page)
            
            for raw in raw_lines:
                line = re.sub(r"\s+", " ", raw).strip()
                if not line:
                    continue
                if HEADER_RE_RANGE.search(line):
                    continue
                
                d_str = None
                for dp in DATE_PATTERNS:
                    md = re.search(dp, line)
                    if md:
                        d_str = md.group("date")
                        break
                if not d_str:
                    continue
                
                amts = [m.group("amount") for m in re.finditer(AMOUNT_PATTERN, line)]
                amts = [a for a in amts if re.search(r"\d", a)]
                if not amts:
                    rest = line[line.find(d_str)+len(d_str):].strip()
                    if HEADER_RE_SINGLE.match(rest) or HEADER_RE_SINGLE.match(line):
                        continue
                    else:
                        continue
                
                amount_text = amts[-1]
                found_cm, last_pos = None, -1
                for cm in CARDMEMBERS_HINTS:
                    pos = line.rfind(cm)
                    if pos > last_pos:
                        last_pos = pos
                        found_cm = cm if pos != -1 else found_cm
                
                start = line.find(d_str) + len(d_str)
                end = line.rfind(amount_text)
                description = line[start:end].strip()
                if found_cm and found_cm in description:
                    description = description[:description.rfind(found_cm)].strip()
                description = description.rstrip("-").strip()
                
                if HEADER_RE_SINGLE.match(description):
                    continue
                
                flexible = description.endswith(" FS") or line.endswith(" FS")
                try:
                    amount_val = _amount_to_float(amount_text)
                except ValueError:
                    continue
                
                # Create UnifiedTransaction
                tx = UnifiedTransaction(
                    date=_parse_iso_date(d_str),
                    description=description,
                    amount_cad=amount_val,
                    currency="USD",
                    original_amount=amount_val,
                    exchange_rate=1.0,
                    cardmember=found_cm,
                    notes="FS" if flexible else "",
                    format_type="original"
                )
                rows.append(tx)
    
    return rows


# ============================================================================
# RBC format parser (simplified - no Type, no Notes)
# ============================================================================

MONTHS_RBC = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}

COUNTRY_CODES = {
    "CAN", "USA", "POL", "DEU", "ESP", "CZE", "HUN", "CHE", "AUT",
    "LTU", "LVA", "EST", "GRC", "FRA", "ITA", "GBR", "IRL", "NLD",
    "BEL", "PRT", "SVK", "SVN", "HRV", "ROU", "BGR", "MNE", "SRB",
    "BIH", "MKD", "ALB", "CYP", "MLT", "SWE", "NOR", "FIN", "DNK",
    "ISL", "TUR",
}

TX_START_RE = re.compile(
    r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) "
    r"\d{2} (JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) \d{2} "
)


def _extract_year_rbc(lines: List[str]) -> int:
    years = []
    for line in lines[:80]:
        for m in re.findall(r"\b(20\d{2})\b", line):
            years.append(int(m))
    if not years:
        return 2025
    return max(years)


def _parse_header_line_rbc(line: str, year: int) -> Optional[tuple]:
    m = re.match(
        r"^(?P<m1>[A-Z]{3}) (?P<d1>\d{2}) "
        r"(?P<m2>[A-Z]{3}) (?P<d2>\d{2}) (?P<rest>.+)$",
        line.strip(),
    )
    if not m:
        return None
    tdate = f"{year}-{MONTHS_RBC[m.group('m1')]}-{m.group('d1')}"
    pdate = f"{year}-{MONTHS_RBC[m.group('m2')]}-{m.group('d2')}"
    desc = m.group("rest").strip()
    return tdate, pdate, desc


def _parse_fx_line_rbc(line: str):
    m = re.match(
        r"^Foreign Currency\s*-\s*([A-Z]{3})\s+([\d,]+\.\d{2})\s+"
        r"Exchange rate\s*-\s*([.\d]+)$",
        line.strip(),
    )
    if not m:
        return None
    cur = m.group(1)
    orig = float(m.group(2).replace(",", ""))
    rate = float(m.group(3))
    return cur, orig, rate


def _parse_cad_amount_rbc(line: str) -> Optional[float]:
    line = line.strip()
    m = re.match(r"^(-?)\$\s*([\d,]+\.\d{2})$", line)
    if m:
        sign = -1 if m.group(1) == "-" else 1
        return sign * float(m.group(2).replace(",", ""))
    
    m2 = re.search(r"(-?)\$\s*([\d,]+\.\d{2})", line)
    if m2:
        sign = -1 if m2.group(1) == "-" else 1
        return sign * float(m2.group(2).replace(",", ""))
    return None


def _infer_country_rbc(desc: str) -> str:
    tokens = desc.split()
    for tok in reversed(tokens):
        if tok in COUNTRY_CODES:
            return tok
    return ""


def _parse_group_rbc(group_lines: List[str], year: int) -> Optional[UnifiedTransaction]:
    header = group_lines[0]
    hdr = _parse_header_line_rbc(header, year)
    if not hdr:
        return None
    tdate, pdate, desc = hdr
    
    # FX info
    fx_cur = fx_orig = fx_rate = None
    for l in group_lines[1:]:
        if l.startswith("Foreign Currency"):
            fx = _parse_fx_line_rbc(l)
            if fx:
                fx_cur, fx_orig, fx_rate = fx
                break
    
    # CAD amount
    header_cad = _parse_cad_amount_rbc(header)
    cad_amount = header_cad
    if cad_amount is None:
        for l in group_lines[1:]:
            if l.startswith("TOTAL ACCOUNT BALANCE") or l.startswith("NEW BALANCE"):
                continue
            val = _parse_cad_amount_rbc(l)
            if val is not None:
                cad_amount = val
    if cad_amount is None:
        return None
    
    if fx_cur:
        sign = 1 if cad_amount >= 0 else -1
        orig_amt = sign * fx_orig
        currency = fx_cur
        rate = fx_rate
    else:
        orig_amt = cad_amount
        currency = "CAD"
        rate = 1.0
    
    merchant_country = _infer_country_rbc(desc)
    
    return UnifiedTransaction(
        date=tdate,
        description=desc,
        amount_cad=cad_amount,
        currency=currency,
        original_amount=orig_amt,
        exchange_rate=rate,
        posting_date=pdate,
        merchant_country=merchant_country,
        notes="",
        format_type="rbc"
    )


def _group_transactions_rbc(lines: List[str]) -> List[List[str]]:
    groups: List[List[str]] = []
    current: List[str] = []
    
    for line in lines:
        if TX_START_RE.match(line.strip()):
            if current:
                groups.append(current)
                current = []
            current.append(line.strip())
        else:
            if current:
                current.append(line.strip())
    
    if current:
        groups.append(current)
    
    return groups


def parse_rbc_format(pdf_path: Path) -> List[UnifiedTransaction]:
    """Parse RBC format PDF (simplified)"""
    lines: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.rstrip()
                if line:
                    lines.append(line)
    
    year = _extract_year_rbc(lines)
    groups = _group_transactions_rbc(lines)
    
    txs: List[UnifiedTransaction] = []
    for g in groups:
        tx = _parse_group_rbc(g, year)
        if tx:
            txs.append(tx)
    
    return txs


# ============================================================================
# Auto parser with format detection
# ============================================================================

def parse_pdf_auto(pdf_path: Path) -> tuple[List[UnifiedTransaction], str]:
    """
    Automatically detect format and parse PDF
    Returns: (transactions, format_type)
    """
    format_type = detect_pdf_format(pdf_path)
    
    if format_type == "original":
        txs = parse_original_format(pdf_path)
        return txs, "original"
    elif format_type == "rbc":
        txs = parse_rbc_format(pdf_path)
        return txs, "rbc"
    else:
        # Try both formats
        try:
            txs = parse_original_format(pdf_path)
            if txs:
                return txs, "original"
        except:
            pass
        
        try:
            txs = parse_rbc_format(pdf_path)
            if txs:
                return txs, "rbc"
        except:
            pass
        
        return [], "unknown"


def transactions_to_dataframe(transactions: List[UnifiedTransaction]) -> pd.DataFrame:
    """Convert transactions to pandas DataFrame"""
    if not transactions:
        return pd.DataFrame()
    
    data = []
    for tx in transactions:
        row = {
            "Date": tx.date,
            "Description": tx.description,
            "Amount_CAD": tx.amount_cad,
            "Currency": tx.currency,
            "Original_Amount": tx.original_amount,
            "Exchange_Rate": tx.exchange_rate,
            "Cardmember": tx.cardmember or "",
            "Posting_Date": tx.posting_date or "",
            "Merchant_Country": tx.merchant_country or "",
            "Notes": tx.notes,
            "Format": tx.format_type,
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    df.sort_values(by=["Date", "Description"], inplace=True, kind="stable")
    return df