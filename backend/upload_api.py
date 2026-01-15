"""
Upload API Endpoints for Connector SDK

Provides:
- POST /upload/bank_statement - Create Dataset via CSVStatementConnector
- POST /upload/erp_excel - Create Dataset via ExcelERPConnector
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from decimal import Decimal
import json

from database import get_db
from connector_sdk import NormalizedBatch, DataHealthReport
from connectors_impl import (
    CSVStatementConnector, ExcelERPConnector, WarehouseSQLConnector,
    ConnectorSDKRegistry
)
from lineage_models import (
    LineageDataset, RawRecord as LineageRawRecord, CanonicalRecord,
    generate_dataset_id
)


router = APIRouter(prefix="/upload", tags=["Upload API"])


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

def dataset_response(dataset: LineageDataset, health_report: DataHealthReport) -> Dict[str, Any]:
    """Build dataset response."""
    return {
        "dataset_id": dataset.dataset_id,
        "id": dataset.id,
        "source_type": dataset.source_type,
        "row_count": dataset.row_count,
        "schema_fingerprint": dataset.schema_fingerprint,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "health_report": health_report.to_dict() if health_report else None
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BANK STATEMENT UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/bank_statement")
async def upload_bank_statement(
    file: UploadFile = File(...),
    entity_id: Optional[int] = Form(None),
    locale: str = Form("ISO"),
    default_currency: str = Form("EUR"),
    source_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload bank statement CSV and create Dataset.
    
    Uses CSVStatementConnector to:
    1. Extract raw records from CSV
    2. Normalize to canonical bank_txns format
    3. Generate canonical IDs for idempotency
    4. Create Dataset with health report
    
    Args:
        file: CSV file upload
        entity_id: Entity this data belongs to
        locale: Date parsing locale ("ISO", "EU", "US", "DE")
        default_currency: Default currency if not specified
        source_name: Optional name for this data source
    
    Returns:
        Dataset with health report
    """
    # Read file content
    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Create connector
    config = {
        "locale": locale,
        "default_currency": default_currency.upper(),
        "source_name": source_name or file.filename
    }
    
    connector = CSVStatementConnector(config, entity_id)
    
    # Test connector
    test_result = connector.test()
    if not test_result.success:
        raise HTTPException(status_code=500, detail=test_result.message)
    
    try:
        # Extract raw data
        raw_batch = connector.extract(content)
        
        if raw_batch.row_count == 0:
            raise HTTPException(status_code=400, detail="No data rows found in CSV")
        
        # Normalize to canonical format
        normalized_batch = connector.normalize(raw_batch)
        
        # Create dataset in database
        dataset = LineageDataset(
            dataset_id=generate_dataset_id(),
            entity_id=entity_id,
            source_type=connector.source_type,
            source_summary_json={
                "filename": file.filename,
                "locale": locale,
                "default_currency": default_currency
            },
            schema_fingerprint=normalized_batch.schema_fingerprint,
            schema_columns_json=[
                {"name": col, "type": raw_batch.column_types.get(col, "unknown")}
                for col in raw_batch.columns
            ],
            row_count=len(normalized_batch.bank_txns)
        )
        db.add(dataset)
        db.flush()
        
        # Store raw records
        for raw_record in raw_batch.records:
            db_raw = LineageRawRecord(
                dataset_id=dataset.id,
                source_table=raw_record.source_table,
                source_row_id=str(raw_record.row_index),
                raw_payload_json=raw_record.raw_data,
                raw_hash=raw_record.raw_hash,
                is_processed=1
            )
            db.add(db_raw)
        
        # Store canonical records
        total_amount = Decimal('0')
        for normalized in normalized_batch.bank_txns:
            # Check for existing canonical_id (idempotency)
            existing = db.query(CanonicalRecord).filter(
                CanonicalRecord.dataset_id == dataset.id,
                CanonicalRecord.canonical_id == normalized.canonical_id
            ).first()
            
            if existing:
                continue  # Skip duplicate
            
            db_canonical = CanonicalRecord(
                dataset_id=dataset.id,
                record_type="BankTxn",
                canonical_id=normalized.canonical_id,
                payload_json=normalized.data,
                amount=float(normalized.amount) if normalized.amount else None,
                currency=normalized.currency,
                record_date=normalized.record_date,
                counterparty=normalized.counterparty,
                external_id=normalized.external_id
            )
            db.add(db_canonical)
            
            if normalized.amount:
                total_amount += abs(normalized.amount)
        
        # Update dataset totals
        dataset.amount_total_base = float(total_amount)
        dataset.currency = default_currency.upper()
        
        # Set date range
        dates = [n.record_date for n in normalized_batch.bank_txns if n.record_date]
        if dates:
            dataset.date_range_start = min(dates)
            dataset.date_range_end = max(dates)
        
        db.commit()
        db.refresh(dataset)
        
        return dataset_response(dataset, normalized_batch.health_report)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process CSV: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ERP EXCEL UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/erp_excel")
async def upload_erp_excel(
    file: UploadFile = File(...),
    entity_id: Optional[int] = Form(None),
    record_type: Optional[str] = Form(None),
    locale: str = Form("ISO"),
    default_currency: str = Form("EUR"),
    sheet_name: Optional[str] = Form(None),
    source_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload ERP Excel (AR/AP) and create Dataset.
    
    Uses ExcelERPConnector to:
    1. Extract raw records from Excel
    2. Auto-detect AR (invoices) vs AP (vendor bills)
    3. Normalize to canonical format
    4. Generate canonical IDs for idempotency
    5. Create Dataset with health report
    
    Args:
        file: Excel file upload
        entity_id: Entity this data belongs to
        record_type: "ar" for invoices, "ap" for vendor bills, None for auto-detect
        locale: Date parsing locale ("ISO", "EU", "US", "DE")
        default_currency: Default currency if not specified
        sheet_name: Specific sheet to process (auto-detects if not specified)
        source_name: Optional name for this data source
    
    Returns:
        Dataset with health report
    """
    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm')):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Please upload an Excel file (.xlsx, .xls, .xlsm)"
        )
    
    # Read file content
    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Create connector
    config = {
        "record_type": record_type,
        "locale": locale,
        "default_currency": default_currency.upper(),
        "sheet_name": sheet_name,
        "source_name": source_name or file.filename
    }
    
    connector = ExcelERPConnector(config, entity_id)
    
    # Test connector
    test_result = connector.test()
    if not test_result.success:
        raise HTTPException(status_code=500, detail=test_result.message)
    
    try:
        # Extract raw data
        raw_batch = connector.extract(content)
        
        if raw_batch.row_count == 0:
            raise HTTPException(status_code=400, detail="No data rows found in Excel")
        
        # Normalize to canonical format
        normalized_batch = connector.normalize(raw_batch)
        
        total_records = len(normalized_batch.invoices) + len(normalized_batch.vendor_bills)
        if total_records == 0:
            raise HTTPException(status_code=400, detail="No valid records found after normalization")
        
        # Determine primary record type for source_type
        source_type = "ar_invoice" if len(normalized_batch.invoices) >= len(normalized_batch.vendor_bills) else "ap_bill"
        
        # Create dataset in database
        dataset = LineageDataset(
            dataset_id=generate_dataset_id(),
            entity_id=entity_id,
            source_type=source_type,
            source_summary_json={
                "filename": file.filename,
                "sheet_name": raw_batch.metadata.get("sheet_name"),
                "available_sheets": raw_batch.metadata.get("available_sheets", []),
                "record_type": record_type,
                "locale": locale,
                "default_currency": default_currency
            },
            schema_fingerprint=normalized_batch.schema_fingerprint,
            schema_columns_json=[
                {"name": col, "type": raw_batch.column_types.get(col, "unknown")}
                for col in raw_batch.columns
            ],
            row_count=total_records
        )
        db.add(dataset)
        db.flush()
        
        # Store raw records
        for raw_record in raw_batch.records:
            db_raw = LineageRawRecord(
                dataset_id=dataset.id,
                source_table=raw_record.source_table,
                source_row_id=str(raw_record.row_index),
                raw_payload_json=raw_record.raw_data,
                raw_hash=raw_record.raw_hash,
                is_processed=1
            )
            db.add(db_raw)
        
        # Store canonical records
        total_amount = Decimal('0')
        
        # Process invoices
        for normalized in normalized_batch.invoices:
            existing = db.query(CanonicalRecord).filter(
                CanonicalRecord.dataset_id == dataset.id,
                CanonicalRecord.canonical_id == normalized.canonical_id
            ).first()
            
            if existing:
                continue
            
            db_canonical = CanonicalRecord(
                dataset_id=dataset.id,
                record_type="Invoice",
                canonical_id=normalized.canonical_id,
                payload_json=normalized.data,
                amount=float(normalized.amount) if normalized.amount else None,
                currency=normalized.currency,
                record_date=normalized.record_date,
                due_date=normalized.due_date,
                counterparty=normalized.counterparty,
                external_id=normalized.external_id
            )
            db.add(db_canonical)
            
            if normalized.amount:
                total_amount += abs(normalized.amount)
        
        # Process vendor bills
        for normalized in normalized_batch.vendor_bills:
            existing = db.query(CanonicalRecord).filter(
                CanonicalRecord.dataset_id == dataset.id,
                CanonicalRecord.canonical_id == normalized.canonical_id
            ).first()
            
            if existing:
                continue
            
            db_canonical = CanonicalRecord(
                dataset_id=dataset.id,
                record_type="VendorBill",
                canonical_id=normalized.canonical_id,
                payload_json=normalized.data,
                amount=float(normalized.amount) if normalized.amount else None,
                currency=normalized.currency,
                record_date=normalized.record_date,
                due_date=normalized.due_date,
                counterparty=normalized.counterparty,
                external_id=normalized.external_id
            )
            db.add(db_canonical)
            
            if normalized.amount:
                total_amount += abs(normalized.amount)
        
        # Update dataset totals
        dataset.amount_total_base = float(total_amount)
        dataset.currency = default_currency.upper()
        
        # Set date range
        all_records = normalized_batch.invoices + normalized_batch.vendor_bills
        dates = [n.record_date for n in all_records if n.record_date]
        if dates:
            dataset.date_range_start = min(dates)
            dataset.date_range_end = max(dates)
        
        db.commit()
        db.refresh(dataset)
        
        return dataset_response(dataset, normalized_batch.health_report)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to process Excel: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH REPORT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/preview")
async def preview_upload(
    file: UploadFile = File(...),
    file_type: str = Query(..., description="File type: 'csv' or 'excel'"),
    locale: str = Query("ISO"),
    default_currency: str = Query("EUR"),
    db: Session = Depends(get_db)
):
    """
    Preview upload without creating dataset.
    
    Returns health report and schema information without persisting data.
    Useful for validating data before committing.
    """
    content = await file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    
    config = {
        "locale": locale,
        "default_currency": default_currency.upper(),
        "source_name": file.filename
    }
    
    if file_type == "csv":
        connector = CSVStatementConnector(config, entity_id=None)
    elif file_type == "excel":
        connector = ExcelERPConnector(config, entity_id=None)
    else:
        raise HTTPException(status_code=400, detail="Invalid file_type. Use 'csv' or 'excel'")
    
    try:
        raw_batch = connector.extract(content)
        normalized_batch = connector.normalize(raw_batch)
        
        # Return preview without persisting
        return {
            "filename": file.filename,
            "file_type": file_type,
            "row_count": raw_batch.row_count,
            "schema_fingerprint": normalized_batch.schema_fingerprint,
            "columns": raw_batch.columns,
            "column_types": raw_batch.column_types,
            "health_report": normalized_batch.health_report.to_dict() if normalized_batch.health_report else None,
            "sample_records": [
                {
                    "canonical_id": r.canonical_id[:16] + "...",
                    "data": r.data
                }
                for r in normalized_batch.get_all_records()[:5]
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to preview: {str(e)}")
