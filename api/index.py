#!/usr/bin/env python3
"""
SpendSense Web Backend for Vercel
FastAPI server with PDF processing
"""

import os
import uuid
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
import aiofiles

# Import existing parsers (unchanged)
from unified_parser import parse_pdf_auto, UnifiedTransaction, transactions_to_dataframe
from excel_writer import write_excel_unified
from csv_writer import write_csv_unified

# Setup
app = FastAPI(title="SpendSense Web API", version="1.0.0")

# CORS middleware - Allow all origins for Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use temp directories for Vercel
UPLOAD_DIR = Path(tempfile.gettempdir()) / "spendsense_uploads"
EXPORT_DIR = Path(tempfile.gettempdir()) / "spendsense_exports"
UPLOAD_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# In-memory session storage (for serverless)
active_sessions: Dict[str, Dict[str, Any]] = {}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SpendSense API is running", "status": "healthy"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "SpendSense Web API"}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF file for processing"""
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Save uploaded file to temp directory
    file_path = UPLOAD_DIR / f"{session_id}_{file.filename}"
    
    try:
        content = await file.read()
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "message": "File uploaded successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )


@app.post("/api/process/{session_id}")
async def process_pdf(session_id: str):
    """Process uploaded PDF using existing parsers"""
    
    # Find uploaded file
    pdf_files = list(UPLOAD_DIR.glob(f"{session_id}_*.pdf"))
    if not pdf_files:
        raise HTTPException(
            status_code=404,
            detail="PDF file not found for this session"
        )
    
    pdf_path = pdf_files[0]
    
    try:
        # Use existing parser (unchanged)
        transactions, format_type = parse_pdf_auto(pdf_path)
        
        if not transactions:
            raise HTTPException(
                status_code=400,
                detail="Could not parse PDF. Please check the file format."
            )
        
        # Calculate statistics
        total_amount = sum(tx.amount_cad for tx in transactions)
        transaction_count = len(transactions)
        
        # Calculate totals by category
        totals = {}
        if format_type == "original":
            for tx in transactions:
                key = tx.cardmember or "Unknown"
                totals[key] = totals.get(key, 0.0) + tx.amount_cad
        elif format_type == "rbc":
            spending = sum(tx.amount_cad for tx in transactions if tx.amount_cad > 0)
            payments = sum(tx.amount_cad for tx in transactions if tx.amount_cad < 0)
            totals = {
                "Spending": spending,
                "Payments": payments
            }
        
        # Get date range
        dates = [tx.date for tx in transactions]
        date_range = {
            "min_date": min(dates) if dates else None,
            "max_date": max(dates) if dates else None
        }
        
        # Convert transactions to serializable format
        transactions_data = []
        for tx in transactions:
            transactions_data.append({
                "date": tx.date,
                "description": tx.description,
                "amount_cad": tx.amount_cad,
                "currency": tx.currency,
                "original_amount": tx.original_amount,
                "exchange_rate": tx.exchange_rate,
                "cardmember": tx.cardmember,
                "posting_date": tx.posting_date,
                "merchant_country": tx.merchant_country,
                "notes": tx.notes,
                "format_type": tx.format_type
            })
        
        # Store session data
        active_sessions[session_id] = {
            "transactions": transactions,
            "format_type": format_type,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        # Clean up uploaded file
        try:
            pdf_path.unlink()
        except:
            pass
        
        return {
            "session_id": session_id,
            "format_type": format_type,
            "total_amount": total_amount,
            "transaction_count": transaction_count,
            "totals": totals,
            "date_range": date_range,
            "transactions": transactions_data
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}"
        )


@app.post("/api/export/{session_id}")
async def export_data(
    session_id: str,
    export_type: str = Form(),  # "excel" or "csv"
    include_summary: bool = Form(default=True)
):
    """Export processed data using existing writers"""
    
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )
    
    session_data = active_sessions[session_id]
    transactions = session_data["transactions"]
    format_type = session_data["format_type"]
    
    try:
        if export_type == "excel":
            export_path = EXPORT_DIR / f"{session_id}_export.xlsx"
            # Use existing excel writer (unchanged)
            write_excel_unified(transactions, export_path, format_type, include_summary)
            
            # Read file content for response
            with open(export_path, 'rb') as f:
                content = f.read()
            
            # Clean up
            try:
                export_path.unlink()
            except:
                pass
            
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=spendsense_export_{session_id}.xlsx"}
            )
        
        elif export_type == "csv":
            export_path = EXPORT_DIR / f"{session_id}_export.csv"
            # Use existing csv writer (unchanged)
            write_csv_unified(transactions, export_path)
            
            # Read file content for response
            with open(export_path, 'rb') as f:
                content = f.read()
            
            # Clean up
            try:
                export_path.unlink()
            except:
                pass
            
            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=spendsense_export_{session_id}.csv"}
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid export type. Use 'excel' or 'csv'"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export data: {str(e)}"
        )


# Vercel handler
handler = app