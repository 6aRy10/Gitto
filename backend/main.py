import os
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Body, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import Session
import models
import pandas as pd
import io
import datetime
from utils import (
    parse_excel_to_df, 
    run_forecast_model, 
    generate_canonical_id, 
    debug_log, 
    record_audit_log,
    get_forecast_aggregation,
    compare_snapshots,
    get_ar_prioritization,
    get_fx_exposure,
    predict_dispute_risk
)
from probabilistic_forecast_service import ProbabilisticForecastService

# Use shared database configuration
from database import get_db, init_db, engine

# Initialize database on startup
init_db()

app = FastAPI(
    title="CFO Cash Command Center API",
    version="1.0.0",
    description="Enterprise treasury intelligence platform"
)

# CORS Configuration - Use environment variables for production
allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001"  # Default to localhost for dev
).split(",")

# Clean up origins (remove whitespace)
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global exception handler for database errors
@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request, exc):
    """Handle database errors gracefully."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database error occurred. Please try again later.",
            "error_type": type(exc).__name__
        }
    )

@app.exception_handler(OperationalError)
async def database_connection_handler(request, exc):
    """Handle database connection errors."""
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database connection failed. Please check database configuration.",
            "error_type": "DatabaseConnectionError"
        }
    )

# Register collaboration API router (Finance-Native Collaboration - "GitHub for Cash")
from collaboration_api import router as collaboration_router
app.include_router(collaboration_router)

# Register lineage API router (Data Lineage + SyncRun spine)
from lineage_api import router as lineage_router
app.include_router(lineage_router)

# Register upload API router (Connector SDK uploads)
from upload_api import router as upload_router
app.include_router(upload_router)

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Test database connection
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        )

@app.get("/")
def read_root():
    return {"message": "CFO Cash Command Center API is running"}

@app.post("/upload/inspect")
async def inspect_file(file: UploadFile = File(...)):
    """Inspect an Excel file and return data health without saving"""
    content = await file.read()
    try:
        df, health = parse_excel_to_df(content)
        
        # Build preview data (first 10 rows)
        preview_rows = []
        for idx, row in df.head(10).iterrows():
            preview_rows.append({
                col: (str(val) if pd.notna(val) else None) 
                for col, val in row.items()
            })
        
        return {
            "health": health,
            "row_count": len(df),
            "columns": list(df.columns),
            "preview": preview_rows
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing Excel: {str(e)}")

@app.post("/upload/dry-run")
async def dry_run_upload(
    file: UploadFile = File(...),
    mapping_config: str = Form(None)
):
    """Validate file with mapping and return health report without saving"""
    content = await file.read()
    try:
        # Parse with optional column mapping
        mapping = None
        if mapping_config:
            import json
            mapping = json.loads(mapping_config)
        
        df, health = parse_excel_to_df(content, mapping_config=mapping)
        
        # Enhanced health check
        health['row_count'] = len(df)
        health['columns_mapped'] = list(df.columns)
        
        # Check for critical fields
        critical_fields = ['amount', 'expected_due_date', 'customer']
        missing_critical = []
        for field in critical_fields:
            if field not in df.columns or df[field].isna().all():
                missing_critical.append(field)
        
        if missing_critical:
            health['warnings'] = health.get('warnings', [])
            health['warnings'].append(f"Missing or empty critical fields: {missing_critical}")
        
        return {
            "health": health,
            "row_count": len(df),
            "ready_to_commit": len(missing_critical) == 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dry run failed: {str(e)}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), entity_id: int = None, db: Session = Depends(get_db)):
    """Upload and process Excel file to create a snapshot."""
    content = await file.read()
    try:
        df, health = parse_excel_to_df(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing Excel: {str(e)}")
    
    try:
        # Create Snapshot
        snapshot = models.Snapshot(
            name=f"Upload {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            data_health=health,
            entity_id=entity_id,
            total_rows=len(df),
            opening_bank_balance=2500000.0, # Mock default for demo
            min_cash_threshold=500000.0     # Mock default for demo
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error while creating snapshot: {str(e)}")

    # Automatically project recurring outflows for the new snapshot
    if entity_id:
        from cash_calendar_service import project_recurring_outflows
        project_recurring_outflows(db, entity_id, snapshot.id)

    # #region agent audit
    print(f"INGESTION AUDIT: Snapshot {snapshot.id}")
    print(f"Total Rows: {len(df)}")
    # #endregion
    
    # Save Invoices
    invoices = []
    seen_cids = set()  # Track canonical IDs to prevent duplicates within batch
    skipped_duplicates = 0
    
    # #region agent log
    debug_log("Starting bulk save", {"snapshot_id": snapshot.id, "row_count": len(df)}, "A", "main.py:upload_file")
    # #endregion

    def get_str(val):
        if pd.isna(val): return ''
        return str(val).strip()
    
    def get_int(val):
        if pd.isna(val): return 0
        try:
            s = str(val).split('.')[0]
            s = "".join(c for c in s if c.isdigit())
            return int(s) if s else 0
        except:
            return 0

    for _, row in df.iterrows():
        cid = generate_canonical_id(row, source="Excel", entity_id=entity_id)
        
        # Skip duplicates within the same batch
        if cid in seen_cids:
            skipped_duplicates += 1
            continue
        seen_cids.add(cid)

        inv = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=entity_id,
            canonical_id=cid,
            source_system="Excel",
            project_desc=get_str(row.get('project_desc')),
            project=get_str(row.get('project')),
            country=get_str(row.get('country')),
            customer=get_str(row.get('customer')),
            document_number=get_str(row.get('document_number')),
            terms_of_payment=get_str(row.get('terms_of_payment')),
            payment_terms_days=get_int(row.get('payment_terms_days')),
            document_date=row.get('document_date') if pd.notna(row.get('document_date')) else None,
            invoice_issue_date=row.get('invoice_issue_date') if pd.notna(row.get('invoice_issue_date')) else None,
            expected_due_date=row.get('expected_due_date') if pd.notna(row.get('expected_due_date')) else None,
            payment_date=row.get('payment_date') if pd.notna(row.get('payment_date')) else None,
            amount=float(row.get('amount', 0)) if pd.notna(row.get('amount')) else 0,
            currency=get_str(row.get('currency')) or 'EUR',
            document_type=get_str(row.get('document_type')) or 'INV',
            special_gl_ind=get_str(row.get('special_gl_ind')),
            due_year=get_int(row.get('due_year'))
        )
        invoices.append(inv)
    
    # Safeguard: Filter to unique canonical_ids before bulk insert (handles edge cases)
    unique_invoices = {}
    for inv in invoices:
        if inv.canonical_id not in unique_invoices:
            unique_invoices[inv.canonical_id] = inv
    invoices = list(unique_invoices.values())
    
    db.bulk_save_objects(invoices)
    db.commit()
    
    print(f"INGESTION COMPLETE: Saved {len(invoices)} invoices, skipped {skipped_duplicates} duplicates")
    
    # Run probabilistic forecast (non-blocking)
    forecast_error = None
    try:
        forecast_service = ProbabilisticForecastService(db)
        forecast_service.run_forecast(snapshot.id)
    except Exception as e:
        forecast_error = str(e)
        print(f"WARNING: Forecast model failed: {e}")
        # Fallback to old model
        try:
            run_forecast_model(db, snapshot.id)
        except Exception as e2:
            print(f"WARNING: Fallback forecast model also failed: {e2}")

    return {
        "snapshot_id": snapshot.id, 
        "health": health,
        "invoices_saved": len(invoices),
        "duplicates_skipped": skipped_duplicates,
        "forecast_error": forecast_error
    }

@app.post("/upload-ap")
async def upload_ap_file(file: UploadFile = File(...), entity_id: int = None, db: Session = Depends(get_db)):
    content = await file.read()
    try:
        df, health = parse_excel_to_df(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing AP Excel: {str(e)}")
    
    snapshot = models.Snapshot(
        name=f"AP Upload {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        data_health=health,
        entity_id=entity_id,
        total_rows=len(df),
        opening_bank_balance=2500000.0,
        min_cash_threshold=500000.0
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    bills = []
    
    # #region agent log
    debug_log("Starting AP bulk save", {"snapshot_id": snapshot.id, "row_count": len(df)}, "B", "main.py:upload_ap_file")
    # #endregion

    for _, row in df.iterrows():
        def get_str(val):
            if pd.isna(val): return ''
            return str(val).strip()
        
        def get_int(val):
            if pd.isna(val): return 0
            try:
                s = str(val).split('.')[0]
                s = "".join(c for c in s if c.isdigit())
                return int(s) if s else 0
            except:
                return 0

        cid = generate_canonical_id(row, source="AP_Excel", entity_id=entity_id)

        bill = models.VendorBill(
            snapshot_id=snapshot.id,
            entity_id=entity_id,
            canonical_id=cid,
            vendor_name=get_str(row.get('vendor_name')) or get_str(row.get('customer')),
            document_number=get_str(row.get('document_number')),
            amount=float(row.get('amount', 0)),
            currency=get_str(row.get('currency')) or 'EUR',
            due_date=row.get('expected_due_date') if pd.notna(row.get('expected_due_date')) else None,
            approval_date=row.get('document_date') if pd.notna(row.get('document_date')) else None,
            scheduled_payment_date=row.get('payment_date') if pd.notna(row.get('payment_date')) else None,
            hold_status=1 if get_str(row.get('hold_status')).lower() in ['yes', 'true', '1', 'hold'] else 0,
            is_discretionary=1 if get_str(row.get('discretionary')).lower() in ['yes', 'true', '1'] else 0,
            category=get_str(row.get('category')) or 'Vendor'
        )
        bills.append(bill)
    
    # Safeguard: Filter to unique canonical_ids before bulk insert
    unique_bills = {}
    for bill in bills:
        if bill.canonical_id not in unique_bills:
            unique_bills[bill.canonical_id] = bill
    bills = list(unique_bills.values())
    
    db.bulk_save_objects(bills)
    db.commit()
    
    return {"snapshot_id": snapshot.id, "bills_count": len(bills)}

@app.get("/snapshots")
def get_snapshots(db: Session = Depends(get_db)):
    return db.query(models.Snapshot).order_by(models.Snapshot.created_at.desc()).all()

@app.delete("/snapshots")
def reset_database(db: Session = Depends(get_db)):
    try:
        # Delete in order of dependencies
        db.query(models.AuditLog).delete()
        db.query(models.WeeklyFXRate).delete()
        db.query(models.VendorBill).delete()
        db.query(models.OutflowItem).delete()
        db.query(models.SegmentDelay).delete()
        db.query(models.ReconciliationTable).delete()
        db.query(models.Invoice).delete()
        db.query(models.Snapshot).delete()
        db.commit()
        return {"message": "All data cleared"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/snapshots/{snapshot_id}")
def delete_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    print(f"DEBUG: Attempting to delete snapshot {snapshot_id}")
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        print(f"DEBUG: Snapshot {snapshot_id} not found in DB")
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    try:
        record_audit_log(db, "System", "Delete", "Snapshot", snapshot_id, {"name": snapshot.name})
        
        # 1. Clear reconciliation links first (manual cleanup for many-to-many or complex links)
        invoice_ids = [inv.id for inv in snapshot.invoices]
        if invoice_ids:
            print(f"DEBUG: Deleting reconciliation records for {len(invoice_ids)} invoices")
            db.query(models.ReconciliationTable).filter(models.ReconciliationTable.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        
        # 2. Delete the snapshot (cascade will handle Invoices, Delays, and DisputeLogs)
        print(f"DEBUG: Deleting snapshot object {snapshot_id}")
        db.delete(snapshot)
        db.commit()
        print(f"DEBUG: Successfully deleted snapshot {snapshot_id}")
        return {"message": "Snapshot deleted"}
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error deleting snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/snapshots/{snapshot_id}/fx-rates")
def set_fx_rates(snapshot_id: int, rates: list[dict], db: Session = Depends(get_db)):
    # #region agent log
    debug_log("Setting FX Rates", {"snapshot_id": snapshot_id, "rates_count": len(rates)}, "C", "main.py:set_fx_rates")
    # #endregion
    """
    Rates: [{"from": "USD", "to": "EUR", "rate": 0.92}, ...]
    Locks the rates for this snapshot.
    """
    # Clear existing for this snapshot
    db.query(models.WeeklyFXRate).filter(models.WeeklyFXRate.snapshot_id == snapshot_id).delete()
    
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    week_start = snapshot.created_at - datetime.timedelta(days=snapshot.created_at.weekday())
    
    for r in rates:
        db_rate = models.WeeklyFXRate(
            snapshot_id=snapshot_id,
            from_currency=r['from'],
            to_currency=r['to'],
            rate=r['rate'],
            effective_week_start=week_start
        )
        db.add(db_rate)
    
    db.commit()
    return {"status": "success", "rates_count": len(rates)}

@app.get("/entities/{entity_id}/washes")
def get_washes(entity_id: int, db: Session = Depends(get_db)):
    from bank_service import detect_intercompany_washes
    return detect_intercompany_washes(db, entity_id)

@app.post("/bank/approve-wash")
def approve_wash(tx1_id: int, tx2_id: int, db: Session = Depends(get_db)):
    from bank_service import approve_wash_service
    return approve_wash_service(db, tx1_id, tx2_id)

@app.get("/snapshots/{snapshot_id}/kpis")
def get_snapshot_kpis(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Calculate adaptive next 4 weeks
    today = datetime.datetime.now()
    # If the snapshot is old, use its creation date as reference
    reference_date = snapshot.created_at if (today - snapshot.created_at).days > 7 else today
    four_weeks_later = reference_date + datetime.timedelta(weeks=4)
    
    invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id).all()
    open_invoices = [inv for inv in invoices if inv.payment_date is None]
    
    total_val = sum(inv.amount for inv in invoices)
    next_4w_inflow = sum(inv.amount for inv in open_invoices if inv.predicted_payment_date and inv.predicted_payment_date <= four_weeks_later)
    
    return {
        "total_portfolio_value": total_val,
        "total_invoices": snapshot.total_rows,
        "open_receivables": sum(inv.amount for inv in open_invoices),
        "next_4w_expected_inflow": next_4w_inflow,
        "data_health_score": snapshot.data_health.get('total_invoices', 0) if snapshot.data_health else 0
    }

@app.get("/snapshots/{snapshot_id}/stats")
def get_snapshot_stats(
    snapshot_id: int, 
    country: str = None, 
    customer: str = None, 
    project: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id)
    if country:
        query = query.filter(models.Invoice.country == country)
    if customer:
        query = query.filter(models.Invoice.customer == customer)
    if project:
        query = query.filter(models.Invoice.project == project)
    
    invoices = query.all()
    df = pd.DataFrame([inv.__dict__ for inv in invoices])
    
    if df.empty:
        return {
            "cash_flow_by_year": [],
            "overdue_chart_data": []
        }
    
    # 1. Cash Flow by Year
    df['year'] = pd.to_datetime(df['expected_due_date']).dt.year
    cash_by_year = df.groupby('year')['amount'].sum().reset_index()
    cash_by_year = cash_by_year.rename(columns={'amount': 'cash'})
    cash_flow_by_year = cash_by_year.to_dict('records')
    
    # 2. Overdue Chart Data
    today = datetime.datetime.now()
    open_df = df[df['payment_date'].isna()].copy()
    open_df['due_date'] = pd.to_datetime(open_df['expected_due_date'])
    open_df['days_overdue'] = (today - open_df['due_date']).dt.days
    
    buckets = [
        {"label": "Current", "min": -99999, "max": 0},
        {"label": "1-30", "min": 1, "max": 30},
        {"label": "31-60", "min": 31, "max": 60},
        {"label": "61-90", "min": 61, "max": 90},
        {"label": "90+", "min": 91, "max": 99999},
    ]
    
    overdue_chart_data = []
    for b in buckets:
        mask = (open_df['days_overdue'] >= b['min']) & (open_df['days_overdue'] <= b['max'])
        overdue_chart_data.append({
            "label": b['label'],
            "amount": float(open_df.loc[mask, 'amount'].sum())
        })
    
    return {
        "cash_flow_by_year": cash_flow_by_year,
        "overdue_chart_data": overdue_chart_data
    }

@app.post("/snapshots/{snapshot_id}/scenario")
def apply_scenario(snapshot_id: int, config: dict, db: Session = Depends(get_db)):
    from utils import apply_scenario_to_forecast
    return apply_scenario_to_forecast(db, snapshot_id, config)

@app.get("/snapshots/{snapshot_id}/accuracy")
def get_accuracy(snapshot_id: int, db: Session = Depends(get_db)):
    from backtesting_service import get_forecast_accuracy
    return get_forecast_accuracy(db, snapshot_id)

@app.get("/entities/{entity_id}/reconciliation-suggestions")
def get_recon_suggestions(entity_id: int, db: Session = Depends(get_db)):
    from bank_service import get_reconciliation_suggestions
    return get_reconciliation_suggestions(db, entity_id)

@app.post("/entities/{entity_id}/reconcile")
def run_reconciliation(
    entity_id: int, 
    db: Session = Depends(get_db),
    use_v2: bool = Query(False, description="Use new reconciliation service V2")
):
    """
    Reconcile all unreconciled transactions for an entity.
    
    Set use_v2=true to use the new reconciliation service with blocking indexes,
    embedding similarity, and constrained solver.
    """
    if use_v2:
        from reconciliation_service_v2 import ReconciliationServiceV2
        service = ReconciliationServiceV2(db)
        return service.reconcile_entity(entity_id)
    else:
        from bank_service import reconcile_transactions
        return reconcile_transactions(db, entity_id)

@app.get("/entities/{entity_id}/cash-ledger")
def get_cash_ledger(entity_id: int, db: Session = Depends(get_db)):
    from bank_service import get_cash_ledger_summary
    return get_cash_ledger_summary(db, entity_id)

@app.get("/snapshots/{snapshot_id}/forecast")
def get_snapshot_forecast(snapshot_id: int, group_by: str = "week", db: Session = Depends(get_db)):
    return get_forecast_aggregation(db, snapshot_id, group_by)

@app.get("/snapshots/{snapshot_id}/segments")
def get_snapshot_segments(snapshot_id: int, db: Session = Depends(get_db)):
    segments = db.query(models.SegmentDelay).filter(models.SegmentDelay.snapshot_id == snapshot_id).all()
    return segments

@app.get("/forecast/diagnostics")
def get_forecast_diagnostics(snapshot_id: int = Query(...), db: Session = Depends(get_db)):
    """
    Get forecast diagnostics including coverage, calibration error, segment sample sizes, drift warnings.
    
    Returns:
        - Coverage metrics (P25-P75 should be ~50%)
        - Calibration error
        - Sample size distribution
        - Drift warnings
        - Insufficient data segments
    """
    forecast_service = ProbabilisticForecastService(db)
    diagnostics = forecast_service.get_diagnostics(snapshot_id)
    return diagnostics

@app.get("/snapshots/{snapshot_id}/invoices")
def get_invoices(
    snapshot_id: int,
    customer: str = None,
    country: str = None,
    project: str = None,
    sort_by: str = "customer",
    sort_dir: str = "asc",
    skip: int = 0,
    limit: int = 100,
    only_open: bool = True,
    db: Session = Depends(get_db)
):
    query = db.query(models.Invoice).filter(models.Invoice.snapshot_id == snapshot_id)

    if only_open:
        query = query.filter(models.Invoice.payment_date == None)

    if customer:
        query = query.filter(models.Invoice.customer == customer)
    if country:
        query = query.filter(models.Invoice.country == country)
    if project:
        query = query.filter(models.Invoice.project == project)

    total = query.count()

    # Simple sortable fields whitelist to avoid SQL injection
    sortable = {
        "customer": models.Invoice.customer,
        "country": models.Invoice.country,
        "project": models.Invoice.project,
        "amount": models.Invoice.amount,
        "predicted_payment_date": models.Invoice.predicted_payment_date,
        "expected_due_date": models.Invoice.expected_due_date,
    }
    sort_field = sortable.get(sort_by, models.Invoice.customer)
    if sort_dir.lower() == "desc":
        sort_field = sort_field.desc()
    else:
        sort_field = sort_field.asc()

    items = query.order_by(sort_field).offset(skip).limit(limit).all()
    return {
        "items": items,
        "total": total
    }

@app.get("/snapshots/{snapshot_id}/filters")
def get_snapshot_filters(
    snapshot_id: int, 
    country: str = None, 
    customer: str = None, 
    project: str = None,
    db: Session = Depends(get_db)
):
    # 1. Countries
    all_countries = db.query(models.Invoice.country).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.country != None,
        models.Invoice.country != ''
    ).distinct().all()
    
    # 2. Customers
    customer_query = db.query(models.Invoice.customer).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.customer != None,
        models.Invoice.customer != ''
    )
    if country:
        customer_query = customer_query.filter(models.Invoice.country == country)
    all_customers = customer_query.distinct().all()
    
    # 3. Projects
    project_query = db.query(models.Invoice.project).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.project != None,
        models.Invoice.project != ''
    )
    if country:
        project_query = project_query.filter(models.Invoice.country == country)
    if customer:
        project_query = project_query.filter(models.Invoice.customer == customer)
    all_projects = project_query.distinct().all()
    
    return {
        "countries": sorted([c[0] for c in all_countries]),
        "customers": sorted([c[0] for c in all_customers]),
        "projects": sorted([p[0] for p in all_projects])
    }

@app.get("/snapshots/{snapshot_id}/top-movers")
def get_top_movers(snapshot_id: int, compare_id: int, db: Session = Depends(get_db)):
    from utils import get_top_movers_logic
    return get_top_movers_logic(db, snapshot_id, compare_id)

@app.get("/snapshots/{snapshot_id}/compare/{compare_id}")
def get_comparison(snapshot_id: int, compare_id: int, db: Session = Depends(get_db)):
    return compare_snapshots(db, snapshot_id, compare_id)

@app.get("/snapshots/{snapshot_id}/priorities")
def get_priorities(snapshot_id: int, db: Session = Depends(get_db)):
    return get_ar_prioritization(db, snapshot_id)

# 13-Week Workspace
@app.get("/snapshots/{snapshot_id}/workspace-13w")
def get_13w_workspace(snapshot_id: int, db: Session = Depends(get_db)):
    from cash_calendar_service import get_13_week_workspace
    data = get_13_week_workspace(db, snapshot_id)
    if not data:
        raise HTTPException(status_code=404, detail="Workspace data not found")
    return data

@app.get("/snapshots/{snapshot_id}/week-details/{week_index}")
def get_week_details(snapshot_id: int, week_index: int, type: str, db: Session = Depends(get_db)):
    from cash_calendar_service import get_week_drilldown_data
    return get_week_drilldown_data(db, snapshot_id, week_index, type)

@app.get("/entities")
def get_entities(db: Session = Depends(get_db)):
    entities = db.query(models.Entity).all()
    if not entities:
        # Create a default entity for demo
        default = models.Entity(name="Gitto Enterprise Group")
        db.add(default)
        db.commit()
        db.refresh(default)
        return [default]
    return entities

@app.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(100).all()

@app.post("/snapshots/{snapshot_id}/ask-insights")
def ask_insights(snapshot_id: int, entity_id: int, query: str, db: Session = Depends(get_db)):
    from bank_service import generate_cash_variance_narrative
    from utils import get_fx_exposure, predict_dispute_risk
    
    q = query.lower()
    
    # 1. Variance Analysis (RAG-Grounded)
    if any(k in q for k in ['why', 'variance', 'shortfall', 'surplus', 'difference', 'swing']):
        var_data = generate_cash_variance_narrative(db, entity_id, snapshot_id)
        
        # Retrieval: Find specific large late invoices (Context)
        today = datetime.datetime.now()
        late_invoices = db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.payment_date == None,
            models.Invoice.predicted_payment_date < today
        ).order_by(models.Invoice.amount.desc()).limit(5).all()
        
        # Context Augmentation
        context_snippets = [f"Inv #{inv.document_number} from {inv.customer}: €{inv.amount:,.0f} (Due: {inv.expected_due_date.date() if inv.expected_due_date else 'N/A'}, Predicted: {inv.predicted_payment_date.date() if inv.predicted_payment_date else 'N/A'})" for inv in late_invoices]
        
        # Narrative Generation (Grounded)
        main_answer = " ".join(var_data['narrative'])
        grounding = "\n\n**Retrieved Evidence:**\n" + "\n".join([f"- {s}" for s in context_snippets]) if context_snippets else "\n\nNo specific overdue invoices found for this period."
        
        return {
            "answer": f"Analysis of the last 7 days shows a €{abs(var_data['variance']):,.0f} variance. {main_answer}{grounding}",
            "citations": [inv.document_number for inv in late_invoices]
        }
    
    # 2. Risk Detection (RAG-Grounded)
    if any(k in q for k in ['risk', 'dispute', 'blockage', 'late', 'payment']):
        risks = predict_dispute_risk(db, snapshot_id)
        if not risks:
            return {"answer": "The retrieval engine found no significant blockage or dispute risks in the current snapshot context."}
        
        top_risks = risks[:3]
        grounding = "\n\n**Identified Risk Invoices:**\n" + "\n".join([f"- {r['customer']} (Inv #{r['invoice_number']}): €{r['amount']:,.0f} - {r['potential_blockage_reasons'][0]}" for r in top_risks])
        
        return {
            "answer": f"I've identified {len(risks)} risk items based on historical behavioral segments.{grounding}",
            "citations": [r['invoice_number'] for r in top_risks]
        }
        
    # 3. FX Exposure (RAG-Grounded)
    if any(k in q for k in ['fx', 'currency', 'eur', 'usd', 'exchange']):
        fx = get_fx_exposure(db, snapshot_id)
        non_eur = [f for f in fx if f['currency'] != 'EUR']
        if not non_eur:
            return {"answer": "Retrieval confirmed that 100% of the current portfolio is in EUR."}
        
        risk_sum = sum(f['implied_fx_risk'] for f in non_eur)
        grounding = "\n\n**Currency Breakdown:**\n" + "\n".join([f"- {f['currency']}: {f['invoice_count']} items, Total €{f['total_amount']:,.0f} (Implied Risk: €{f['implied_fx_risk']:,.0f})" for f in non_eur])
        
        return {
            "answer": f"Total FX-impacted value is €{sum(f['total_amount'] for f in non_eur):,.0f} across {len(non_eur)} currencies.{grounding}",
            "citations": [f['currency'] for f in non_eur]
        }

    return {"answer": "I can help you understand variances, predict dispute risks, or analyze your FX exposure. Try asking 'Why is there a shortfall?'"}

@app.post("/contact")
def handle_contact(data: dict):
    print(f"New Contact Request from {data.get('email')}: {data.get('message')}")
    return {"message": "Success! We'll be in touch soon."}

@app.post("/snowflake/config")
def save_snowflake_config(config: dict, db: Session = Depends(get_db)):
    db_config = db.query(models.SnowflakeConfig).first()
    if not db_config:
        db_config = models.SnowflakeConfig(**config)
        db.add(db_config)
    else:
        for k, v in config.items():
            setattr(db_config, k, v)
    db.commit()
    return {"status": "success"}

@app.get("/snowflake/config")
def get_snowflake_config(db: Session = Depends(get_db)):
    return db.query(models.SnowflakeConfig).first() or {}

@app.post("/snowflake/test")
def test_snowflake_connection(config: dict):
    # Mock success for now
    return {"status": "success"}

@app.post("/snowflake/sync")
def sync_snowflake(db: Session = Depends(get_db)):
    # Mock success for now
    return {"status": "success", "snapshot_id": 999}


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTOR SDK ENDPOINTS - Enterprise Data Integration
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/connectors/types")
def list_connector_types():
    """List all available connector types."""
    from connectors import ConnectorRegistry
    
    available = ConnectorRegistry.list_available()
    
    # Add metadata for each type
    connector_types = []
    for type_key, description in available.items():
        connector_types.append({
            "type": type_key,
            "description": description,
            "category": _get_connector_category(type_key),
            "requires_oauth": type_key in ["bank_plaid", "bank_nordigen", "erp_quickbooks", "erp_xero"],
            "supports_incremental": type_key not in ["bank_mt940"]
        })
    
    return connector_types


def _get_connector_category(type_key: str) -> str:
    """Get category for connector type."""
    if type_key.startswith("bank_"):
        return "Banks"
    elif type_key.startswith("erp_"):
        return "ERP/Accounting"
    elif type_key.startswith("payments_"):
        return "Payments"
    elif type_key.startswith("payroll_"):
        return "Payroll"
    elif type_key.startswith("warehouse_"):
        return "Data Warehouse"
    else:
        return "Other"


@app.post("/connectors/test-credentials")
def test_connector_credentials(data: dict):
    """
    Test connector credentials before saving.
    This validates the credentials by attempting to connect to the service.
    """
    from connectors import ConnectorRegistry
    
    connector_type = data.get("type")
    credentials = data.get("credentials", {})
    
    if not connector_type:
        raise HTTPException(status_code=400, detail="Connector type is required")
    
    # Get the connector class
    try:
        connector = ConnectorRegistry.get(connector_type, credentials)
        if not connector:
            return {
                "success": False,
                "message": f"Connector type '{connector_type}' is not supported. Available: bank_plaid, bank_nordigen, erp_quickbooks, erp_xero, payments_stripe, warehouse_snowflake, warehouse_bigquery, erp_netsuite, erp_sap, bank_mt940"
            }
        
        # Test the connection - returns a ConnectorResult object
        result = connector.test_connection()
        
        return {
            "success": result.success,
            "message": result.message
        }
        
    except ImportError as e:
        return {
            "success": False,
            "message": f"SDK not installed: {str(e)}"
        }
    except ValueError as e:
        return {
            "success": False,
            "message": f"Configuration error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Credential test failed for {connector_type}: {e}")
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }


@app.get("/connectors")
def list_connectors(db: Session = Depends(get_db)):
    """List all registered connectors."""
    connectors = db.query(models.Connector).all()
    return [{
        "id": c.id,
        "type": c.type,
        "name": c.name,
        "description": c.description,
        "entity_id": c.entity_id,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "connections_count": len(c.connections) if c.connections else 0
    } for c in connectors]


@app.post("/connectors")
def create_connector(data: dict, db: Session = Depends(get_db)):
    """Register a new connector."""
    connector = models.Connector(
        type=data.get("type"),
        name=data.get("name"),
        description=data.get("description"),
        entity_id=data.get("entity_id"),
        is_active=1
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    
    record_audit_log(db, "connector_created", {
        "connector_id": connector.id,
        "type": connector.type,
        "name": connector.name
    })
    
    return {"id": connector.id, "message": "Connector created successfully"}


@app.get("/connectors/{connector_id}")
def get_connector(connector_id: int, db: Session = Depends(get_db)):
    """Get connector details."""
    connector = db.query(models.Connector).filter(models.Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    return {
        "id": connector.id,
        "type": connector.type,
        "name": connector.name,
        "description": connector.description,
        "entity_id": connector.entity_id,
        "is_active": connector.is_active,
        "created_at": connector.created_at.isoformat() if connector.created_at else None,
        "connections": [{
            "id": conn.id,
            "name": conn.name,
            "sync_status": conn.sync_status,
            "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None
        } for conn in connector.connections],
        "source_profiles": [{
            "id": sp.id,
            "name": sp.name,
            "is_active": sp.is_active
        } for sp in connector.source_profiles]
    }


@app.post("/connectors/{connector_id}/connections")
def create_connection(connector_id: int, data: dict, db: Session = Depends(get_db)):
    """Create a new connection for a connector."""
    connector = db.query(models.Connector).filter(models.Connector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connection = models.Connection(
        connector_id=connector_id,
        name=data.get("name"),
        endpoint_url=data.get("endpoint_url"),
        credentials_ref=data.get("credentials_ref"),  # Reference only, not plaintext
        sync_status="idle"
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    record_audit_log(db, "connection_created", {
        "connection_id": connection.id,
        "connector_id": connector_id,
        "name": connection.name
    })
    
    return {"id": connection.id, "message": "Connection created successfully"}


@app.post("/connections/{connection_id}/test")
def test_connection(connection_id: int, db: Session = Depends(get_db)):
    """Test a connection's connectivity."""
    connection = db.query(models.Connection).filter(models.Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    connector = connection.connector
    if not connector:
        raise HTTPException(status_code=400, detail="Connector not found")
    
    # Get connector implementation
    from connectors import ConnectorRegistry
    connector_impl = ConnectorRegistry.get(connector.type, {
        'connection_id': connection.id,
        'endpoint_url': connection.endpoint_url
    })
    
    if not connector_impl:
        return {"success": True, "message": f"Connector type '{connector.type}' test skipped (no implementation)"}
    
    result = connector_impl.test_connection()
    return {
        "success": result.success,
        "message": result.message
    }


@app.post("/connections/{connection_id}/sync")
def trigger_sync(connection_id: int, db: Session = Depends(get_db)):
    """Trigger a sync for a connection."""
    connection = db.query(models.Connection).filter(models.Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Create sync run record
    sync_run = models.SyncRun(
        connection_id=connection_id,
        status="running"
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)
    
    # Update connection status
    connection.sync_status = "running"
    connection.last_sync_at = datetime.datetime.utcnow()
    db.commit()
    
    record_audit_log(db, "sync_triggered", {
        "connection_id": connection_id,
        "sync_run_id": sync_run.id
    })
    
    # TODO: In production, this would be a background job
    # For now, return immediately
    return {
        "sync_run_id": sync_run.id,
        "status": "running",
        "message": "Sync started"
    }


@app.get("/connections/{connection_id}/sync-runs")
def get_sync_runs(connection_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Get recent sync runs for a connection."""
    runs = db.query(models.SyncRun)\
        .filter(models.SyncRun.connection_id == connection_id)\
        .order_by(models.SyncRun.started_at.desc())\
        .limit(limit)\
        .all()
    
    return [{
        "id": r.id,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "status": r.status,
        "rows_extracted": r.rows_extracted,
        "rows_created": r.rows_created,
        "rows_updated": r.rows_updated,
        "rows_skipped": r.rows_skipped,
        "error_message": r.error_message
    } for r in runs]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FRESHNESS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/data-freshness")
def get_freshness_dashboard(db: Session = Depends(get_db)):
    """Get data freshness dashboard for all sources."""
    import freshness_service
    return freshness_service.get_data_freshness_dashboard(db)


@app.get("/data-freshness/snapshot/{snapshot_id}")
def get_snapshot_freshness(snapshot_id: int, db: Session = Depends(get_db)):
    """Check data freshness for a specific snapshot (for lock validation)."""
    import freshness_service
    return freshness_service.check_snapshot_data_freshness(db, snapshot_id)


@app.get("/data-freshness/alerts")
def get_freshness_alerts(db: Session = Depends(get_db)):
    """Get all unacknowledged data freshness alerts."""
    import freshness_service
    alerts = freshness_service.get_unacknowledged_alerts(db)
    return [{
        "id": a.id,
        "connection_id": a.connection_id,
        "alert_type": a.alert_type,
        "severity": a.severity,
        "message": a.message,
        "created_at": a.created_at.isoformat() if a.created_at else None
    } for a in alerts]


@app.post("/data-freshness/alerts/{alert_id}/acknowledge")
def acknowledge_freshness_alert(alert_id: int, data: dict, db: Session = Depends(get_db)):
    """Acknowledge a data freshness alert."""
    import freshness_service
    user = data.get("user", "unknown")
    success = freshness_service.acknowledge_alert(db, alert_id, user)
    if success:
        return {"message": "Alert acknowledged"}
    raise HTTPException(status_code=404, detail="Alert not found")


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE PROFILE ENDPOINTS (Field Mappings)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/connectors/{connector_id}/source-profiles")
def get_source_profiles(connector_id: int, db: Session = Depends(get_db)):
    """Get all source profiles for a connector."""
    profiles = db.query(models.SourceProfile)\
        .filter(models.SourceProfile.connector_id == connector_id)\
        .all()
    
    return [{
        "id": p.id,
        "name": p.name,
        "field_mappings": p.field_mappings,
        "transform_rules": p.transform_rules,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None
    } for p in profiles]


@app.post("/connectors/{connector_id}/source-profiles")
def create_source_profile(connector_id: int, data: dict, db: Session = Depends(get_db)):
    """Create a source profile (field mapping configuration)."""
    profile = models.SourceProfile(
        connector_id=connector_id,
        name=data.get("name"),
        field_mappings=data.get("field_mappings", {}),
        transform_rules=data.get("transform_rules", {}),
        is_active=1
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    record_audit_log(db, "source_profile_created", {
        "profile_id": profile.id,
        "connector_id": connector_id,
        "name": profile.name
    })
    
    return {"id": profile.id, "message": "Source profile created successfully"}


@app.put("/source-profiles/{profile_id}")
def update_source_profile(profile_id: int, data: dict, db: Session = Depends(get_db)):
    """Update a source profile."""
    profile = db.query(models.SourceProfile).filter(models.SourceProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Source profile not found")
    
    if "name" in data:
        profile.name = data["name"]
    if "field_mappings" in data:
        profile.field_mappings = data["field_mappings"]
    if "transform_rules" in data:
        profile.transform_rules = data["transform_rules"]
    if "is_active" in data:
        profile.is_active = 1 if data["is_active"] else 0
    
    profile.updated_at = datetime.datetime.utcnow()
    db.commit()
    
    return {"message": "Source profile updated successfully"}


# ═══════════════════════════════════════════════════════════════════════════════
# DATASETS & LINEAGE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/datasets")
def list_datasets(limit: int = 50, db: Session = Depends(get_db)):
    """List all datasets (import batches)."""
    datasets = db.query(models.Dataset)\
        .order_by(models.Dataset.created_at.desc())\
        .limit(limit)\
        .all()
    
    return [{
        "id": d.id,
        "source_type": d.source_type,
        "as_of_timestamp": d.as_of_timestamp.isoformat() if d.as_of_timestamp else None,
        "row_count": d.row_count,
        "checksum": d.checksum,
        "created_at": d.created_at.isoformat() if d.created_at else None
    } for d in datasets]


@app.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Get dataset details with lineage."""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get sync run that created this dataset
    sync_run = dataset.sync_run if dataset.sync_run else None
    
    return {
        "id": dataset.id,
        "source_type": dataset.source_type,
        "as_of_timestamp": dataset.as_of_timestamp.isoformat() if dataset.as_of_timestamp else None,
        "row_count": dataset.row_count,
        "checksum": dataset.checksum,
        "raw_payload_ref": dataset.raw_payload_ref,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "sync_run": {
            "id": sync_run.id,
            "connection_id": sync_run.connection_id,
            "status": sync_run.status,
            "started_at": sync_run.started_at.isoformat() if sync_run.started_at else None
        } if sync_run else None
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATA QUALITY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/data-quality/issues")
def get_data_quality_issues(
    snapshot_id: int = None, 
    status: str = "open",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get data quality issues."""
    query = db.query(models.DataQualityIssue)
    
    if snapshot_id:
        query = query.filter(models.DataQualityIssue.snapshot_id == snapshot_id)
    if status:
        query = query.filter(models.DataQualityIssue.status == status)
    
    issues = query.order_by(models.DataQualityIssue.created_at.desc()).limit(limit).all()
    
    return [{
        "id": i.id,
        "snapshot_id": i.snapshot_id,
        "issue_type": i.issue_type,
        "severity": i.severity,
        "description": i.description,
        "affected_amount": i.affected_amount,
        "status": i.status,
        "created_at": i.created_at.isoformat() if i.created_at else None
    } for i in issues]


@app.post("/data-quality/issues/{issue_id}/resolve")
def resolve_data_quality_issue(issue_id: int, data: dict, db: Session = Depends(get_db)):
    """Resolve a data quality issue."""
    issue = db.query(models.DataQualityIssue).filter(models.DataQualityIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    issue.status = "resolved"
    issue.resolution_notes = data.get("notes")
    issue.resolved_by = data.get("user", "unknown")
    issue.resolved_at = datetime.datetime.utcnow()
    db.commit()
    
    return {"message": "Issue resolved"}


# ═══════════════════════════════════════════════════════════════════════════════
# MATCHING ENGINE ENDPOINTS - Bank Reconciliation
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/snapshots/{snapshot_id}/matching/build-index")
def build_matching_index(snapshot_id: int, db: Session = Depends(get_db)):
    """Build matching index for a snapshot."""
    from matching_engine import MatchingEngine
    
    engine = MatchingEngine(db)
    count = engine.build_index(snapshot_id)
    
    return {
        "snapshot_id": snapshot_id,
        "invoices_indexed": count,
        "message": f"Indexed {count} unpaid invoices for matching"
    }


@app.post("/snapshots/{snapshot_id}/matching/find-matches")
def find_matches_for_transactions(snapshot_id: int, db: Session = Depends(get_db)):
    """Find matches for all unmatched bank transactions in a snapshot."""
    from matching_engine import MatchingEngine, get_cash_explained_percent
    
    engine = MatchingEngine(db)
    engine.load_policy_from_db()
    indexed_count = engine.build_index(snapshot_id)
    
    # Get unmatched bank transactions
    bank_txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.snapshot_id == snapshot_id,
        models.BankTransaction.match_status.in_(['Unmatched', None])
    ).all()
    
    results = []
    auto_matched = 0
    suggested = 0
    manual_required = 0
    
    for txn in bank_txns:
        result = engine.find_matches(txn)
        
        if result.status == 'auto_matched':
            auto_matched += 1
        elif result.status == 'suggested':
            suggested += 1
        elif result.status == 'manual_required':
            manual_required += 1
        
        results.append({
            'bank_txn_id': result.bank_txn_id,
            'amount': float(result.bank_txn_amount),
            'status': result.status,
            'best_tier': result.best_tier,
            'candidates_count': len(result.candidates),
            'top_candidates': [
                {
                    'invoice_id': c.invoice_id,
                    'invoice_number': c.invoice_number,
                    'customer_name': c.customer_name,
                    'amount': float(c.amount),
                    'tier': c.tier,
                    'confidence': round(c.confidence, 2),
                    'suggested_allocation': float(c.suggested_allocation) if c.suggested_allocation else None,
                    'reasons': c.match_reasons
                }
                for c in result.candidates[:5]
            ]
        })
    
    # Calculate Cash Explained %
    cash_explained = get_cash_explained_percent(db, snapshot_id)
    
    return {
        'snapshot_id': snapshot_id,
        'invoices_indexed': indexed_count,
        'transactions_processed': len(bank_txns),
        'summary': {
            'auto_matched': auto_matched,
            'suggested': suggested,
            'manual_required': manual_required,
            'no_match': len(bank_txns) - auto_matched - suggested - manual_required
        },
        'cash_explained': cash_explained,
        'results': results
    }


@app.post("/matching/allocations")
def create_allocation(data: dict, db: Session = Depends(get_db)):
    """Create a match allocation (with approval)."""
    from matching_engine import create_match_allocation
    
    allocation = create_match_allocation(
        db=db,
        bank_txn_id=data.get('bank_txn_id'),
        invoice_id=data.get('invoice_id'),
        allocated_amount=data.get('allocated_amount'),
        match_tier=data.get('tier', 4),
        confidence=data.get('confidence', 0.0),
        approved_by=data.get('approved_by')
    )
    db.commit()
    
    record_audit_log(db, "match_allocation_created", {
        "allocation_id": allocation.id,
        "bank_txn_id": data.get('bank_txn_id'),
        "invoice_id": data.get('invoice_id'),
        "amount": data.get('allocated_amount'),
        "approved_by": data.get('approved_by')
    })
    
    return {"allocation_id": allocation.id, "message": "Allocation created"}


@app.post("/matching/allocations/{allocation_id}/approve")
def approve_allocation(allocation_id: int, data: dict, db: Session = Depends(get_db)):
    """Approve a suggested match allocation."""
    allocation = db.query(models.MatchAllocation).filter(
        models.MatchAllocation.id == allocation_id
    ).first()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    
    allocation.status = "Approved"
    allocation.approved_by = data.get('user', 'unknown')
    allocation.approved_at = datetime.datetime.utcnow()
    db.commit()
    
    record_audit_log(db, "match_allocation_approved", {
        "allocation_id": allocation_id,
        "approved_by": data.get('user')
    })
    
    return {"message": "Allocation approved"}


@app.get("/snapshots/{snapshot_id}/cash-explained")
def get_cash_explained(snapshot_id: int, db: Session = Depends(get_db)):
    """Get Cash Explained % - the north-star trust KPI."""
    from matching_engine import get_cash_explained_percent
    return get_cash_explained_percent(db, snapshot_id)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION WORKFLOW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/snapshots/{snapshot_id}/exceptions")
def get_reconciliation_exceptions(
    snapshot_id: int,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get unmatched transaction exceptions."""
    query = db.query(models.ReconciliationException).filter(
        models.ReconciliationException.snapshot_id == snapshot_id
    )
    
    if status:
        query = query.filter(models.ReconciliationException.status == status)
    
    exceptions = query.order_by(models.ReconciliationException.created_at.desc()).all()
    
    return [{
        "id": e.id,
        "bank_transaction_id": e.bank_transaction_id,
        "status": e.status,
        "assignee_id": e.assignee_id,
        "days_unmatched": e.days_unmatched,
        "sla_due_at": e.sla_due_at.isoformat() if e.sla_due_at else None,
        "resolution_type": e.resolution_type,
        "created_at": e.created_at.isoformat() if e.created_at else None
    } for e in exceptions]


@app.post("/exceptions/{exception_id}/assign")
def assign_exception(exception_id: int, data: dict, db: Session = Depends(get_db)):
    """Assign an exception to a user."""
    exception = db.query(models.ReconciliationException).filter(
        models.ReconciliationException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    exception.assignee_id = data.get('assignee')
    exception.assigned_at = datetime.datetime.utcnow()
    exception.status = 'assigned'
    
    # Set SLA (default 3 business days)
    sla_days = data.get('sla_days', 3)
    exception.sla_due_at = datetime.datetime.utcnow() + datetime.timedelta(days=sla_days)
    
    db.commit()
    
    return {"message": f"Exception assigned to {data.get('assignee')}"}


@app.post("/exceptions/{exception_id}/resolve")
def resolve_exception(exception_id: int, data: dict, db: Session = Depends(get_db)):
    """Resolve an exception."""
    exception = db.query(models.ReconciliationException).filter(
        models.ReconciliationException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    exception.status = 'resolved'
    exception.resolution_type = data.get('resolution_type')  # 'matched', 'write_off', 'fee', 'chargeback'
    exception.resolution_notes = data.get('notes')
    exception.resolved_by = data.get('user', 'unknown')
    exception.resolved_at = datetime.datetime.utcnow()
    db.commit()
    
    record_audit_log(db, "exception_resolved", {
        "exception_id": exception_id,
        "resolution_type": data.get('resolution_type'),
        "resolved_by": data.get('user')
    })
    
    return {"message": "Exception resolved"}


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTESTING & CALIBRATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/snapshots/{snapshot_id}/backtesting/record-predictions")
def record_forecast_predictions(snapshot_id: int, db: Session = Depends(get_db)):
    """Record current forecast predictions for later backtesting."""
    from backtesting_service import BacktestingService
    
    service = BacktestingService(db)
    count = service.record_predictions(snapshot_id)
    
    return {
        "snapshot_id": snapshot_id,
        "predictions_recorded": count,
        "message": f"Recorded {count} predictions for backtesting"
    }


@app.post("/backtesting/update-actuals")
def update_backtest_actuals(snapshot_id: int = None, db: Session = Depends(get_db)):
    """Update backtest records with actual payment data."""
    from backtesting_service import BacktestingService
    
    service = BacktestingService(db)
    count = service.update_actuals(snapshot_id)
    
    return {
        "actuals_updated": count,
        "message": f"Updated {count} backtest records with actuals"
    }


@app.get("/backtesting/calibration-report")
def get_calibration_report(
    snapshot_id: int = None,
    days: int = 90,
    db: Session = Depends(get_db)
):
    """Get forecast calibration report."""
    from backtesting_service import BacktestingService
    
    since_date = datetime.datetime.utcnow() - datetime.timedelta(days=days) if days else None
    
    service = BacktestingService(db)
    report = service.get_calibration_report(snapshot_id, since_date)
    
    return report


@app.get("/backtesting/summary")
def get_backtesting_summary(db: Session = Depends(get_db)):
    """Get quick backtesting summary."""
    from sqlalchemy import func
    
    total = db.query(func.count(models.ForecastBacktest.id)).scalar() or 0
    completed = db.query(func.count(models.ForecastBacktest.id)).filter(
        models.ForecastBacktest.actual_date.isnot(None)
    ).scalar() or 0
    
    calibrated = db.query(func.count(models.ForecastBacktest.id)).filter(
        models.ForecastBacktest.in_p25_p75 == 1
    ).scalar() or 0
    
    return {
        "total_predictions": total,
        "completed": completed,
        "pending": total - completed,
        "in_p25_p75_range": calibrated,
        "calibration_pct": round(calibrated / completed * 100, 1) if completed > 0 else None
    }


# ═══════════════════════════════════════════════════════════════════════════════
# VARIANCE SERVICE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/snapshots/{snapshot_id}/variance")
def get_variance(snapshot_id: int, compare_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Calculate variance between current and previous snapshot."""
    from variance_service import calculate_variance
    
    if not compare_id:
        # Find the most recent locked snapshot before this one
        current_snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
        if not current_snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        previous = db.query(models.Snapshot).filter(
            models.Snapshot.id < snapshot_id,
            models.Snapshot.entity_id == current_snapshot.entity_id
        ).order_by(models.Snapshot.id.desc()).first()
        
        if not previous:
            return {"error": "No previous snapshot found for comparison"}
        
        compare_id = previous.id
    
    return calculate_variance(db, snapshot_id, compare_id)


@app.get("/snapshots/{snapshot_id}/variance-drilldown")
def get_variance_drilldown(
    snapshot_id: int,
    compare_id: int = Query(...),
    week_index: int = Query(...),
    variance_type: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get drilldown for specific variance type."""
    from variance_service import get_variance_drilldown
    
    return get_variance_drilldown(db, snapshot_id, compare_id, week_index, variance_type)


# ═══════════════════════════════════════════════════════════════════════════════
# RED WEEKS SERVICE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/snapshots/{snapshot_id}/red-weeks")
def get_red_weeks(snapshot_id: int, threshold: Optional[float] = Query(None), db: Session = Depends(get_db)):
    """Flag weeks where cash falls below threshold."""
    from red_weeks_service import flag_red_weeks
    
    return flag_red_weeks(db, snapshot_id, threshold)


@app.get("/snapshots/{snapshot_id}/red-weeks/{week_index}/drilldown")
def get_red_week_drilldown(snapshot_id: int, week_index: int, db: Session = Depends(get_db)):
    """Get drilldown for a specific red week."""
    from red_weeks_service import get_red_weeks_drilldown
    
    return get_red_weeks_drilldown(db, snapshot_id, week_index)


# ═══════════════════════════════════════════════════════════════════════════════
# TRUTH LABELING SERVICE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/snapshots/{snapshot_id}/truth-labels")
def get_truth_labels(snapshot_id: int, db: Session = Depends(get_db)):
    """Get truth label summary for a snapshot."""
    from truth_labeling_service import get_truth_label_summary
    
    return get_truth_label_summary(db, snapshot_id)


# ═══════════════════════════════════════════════════════════════════════════════
# UNMATCHED TRANSACTION LIFECYCLE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/entities/{entity_id}/unmatched-transactions")
def get_unmatched_transactions(
    entity_id: int,
    status: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get unmatched transactions with lifecycle status."""
    from unmatched_lifecycle_service import get_unmatched_transactions
    
    return get_unmatched_transactions(db, entity_id, status, assignee)


@app.get("/entities/{entity_id}/matching-policy")
def get_matching_policy(entity_id: int, currency: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Get unmatched transactions with lifecycle status."""
    from unmatched_lifecycle_service import get_unmatched_transactions
    
    return get_unmatched_transactions(db, entity_id, status, assignee)


@app.patch("/transactions/{transaction_id}/status")
def update_transaction_status(
    transaction_id: int,
    status: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Update transaction lifecycle status."""
    from unmatched_lifecycle_service import update_transaction_status
    
    return update_transaction_status(db, transaction_id, status)


@app.post("/transactions/{transaction_id}/assign")
def assign_transaction(
    transaction_id: int,
    assignee: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Assign transaction to a user."""
    from unmatched_lifecycle_service import assign_transaction
    
    return assign_transaction(db, transaction_id, assignee)


@app.get("/entities/{entity_id}/sla-aging")
def get_sla_aging(entity_id: int, db: Session = Depends(get_db)):
    """Get SLA aging report for unmatched transactions."""
    from unmatched_lifecycle_service import get_sla_aging_report
    
    return get_sla_aging_report(db, entity_id)


# ═══════════════════════════════════════════════════════════════════════════════
# MATCHING POLICY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/entities/{entity_id}/matching-policy")
def get_matching_policy(entity_id: int, currency: str = None, db: Session = Depends(get_db)):
    """Get matching policy for entity/currency."""
    from matching_policy_service import get_matching_policy
    
    return get_matching_policy(db, entity_id, currency)


@app.post("/entities/{entity_id}/matching-policy")
def set_matching_policy(
    entity_id: int,
    policy: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Set matching policy for entity/currency."""
    from matching_policy_service import set_matching_policy
    
    return set_matching_policy(
        db,
        entity_id,
        policy.get("currency"),
        policy.get("amount_tolerance"),
        policy.get("date_window_days"),
        policy.get("tier_enabled", {})
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/audit-trail")
def get_audit_trail(
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    since: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get audit trail with filters."""
    from audit_service import get_audit_trail
    
    since_date = None
    if since:
        from datetime import datetime
        since_date = datetime.fromisoformat(since)
    
    return get_audit_trail(db, resource_type, resource_id, action, user, since_date)


@app.get("/snapshots/{snapshot_id}/lineage")
def get_snapshot_lineage(snapshot_id: int, db: Session = Depends(get_db)):
    """Get lineage tracking info for a snapshot."""
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return {
        "snapshot_id": snapshot_id,
        "import_batch_id": getattr(snapshot, 'import_batch_id', None),
        "assumption_set_id": getattr(snapshot, 'assumption_set_id', None),
        "fx_table_version": getattr(snapshot, 'fx_table_version', None),
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "source": snapshot.source
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LIQUIDITY LEVERS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/treasury-actions/{action_id}/predict-impact")
def predict_lever_impact(action_id: int, db: Session = Depends(get_db)):
    """Predict impact of a treasury action."""
    from liquidity_levers_service import predict_lever_impact
    
    return predict_lever_impact(db, action_id)


@app.post("/treasury-actions/{action_id}/track-outcome")
def track_lever_outcome(action_id: int, outcome: dict = Body(...), db: Session = Depends(get_db)):
    """Track actual outcome of a treasury action."""
    from liquidity_levers_service import track_lever_outcome
    
    return track_lever_outcome(
        db,
        action_id,
        outcome.get("actual_amount"),
        outcome.get("actual_date"),
        outcome.get("notes")
    )


@app.get("/snapshots/{snapshot_id}/lever-performance")
def get_lever_performance(snapshot_id: int, db: Session = Depends(get_db)):
    """Get performance summary for liquidity levers."""
    from liquidity_levers_service import get_lever_performance_summary
    
    return get_lever_performance_summary(db, snapshot_id)


@app.patch("/snapshots/{snapshot_id}/unknown-bucket-kpi")
def set_unknown_bucket_kpi(snapshot_id: int, kpi_target: float = Body(..., embed=True), db: Session = Depends(get_db)):
    """Set KPI target for unknown bucket."""
    from unknown_bucket_service import set_unknown_bucket_kpi_target
    
    return set_unknown_bucket_kpi_target(db, snapshot_id, kpi_target)


@app.post("/snapshots/{snapshot_id}/upsert-mode")
def set_upsert_mode(snapshot_id: int, mode: dict = Body(...), db: Session = Depends(get_db)):
    """Set upsert semantics for snapshot."""
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Store upsert mode in snapshot metadata
    if not hasattr(snapshot, 'metadata') or snapshot.metadata is None:
        snapshot.metadata = {}
    
    snapshot.metadata['upsert_mode'] = mode.get('mode', 'replace')  # 'replace' or 'merge'
    snapshot.metadata['dedup_strategy'] = mode.get('dedup_strategy', 'canonical_id')
    db.commit()
    
    return {"snapshot_id": snapshot_id, "upsert_mode": snapshot.metadata['upsert_mode']}


@app.post("/snapshots/{snapshot_id}/meeting-mode")
def execute_meeting_mode(snapshot_id: int, db: Session = Depends(get_db)):
    """Execute meeting mode workflow."""
    from meeting_mode_service import execute_meeting_mode_workflow
    
    return execute_meeting_mode_workflow(db, snapshot_id)

# Snapshot state machine endpoints
@app.post("/snapshots/{snapshot_id}/ready-for-review")
def mark_snapshot_ready_for_review(
    snapshot_id: int,
    user_id: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Mark snapshot as ready for review (DRAFT -> READY_FOR_REVIEW)."""
    from snapshot_state_machine import SnapshotStateMachine
    state_machine = SnapshotStateMachine(db)
    return state_machine.mark_ready_for_review(snapshot_id, user_id)

@app.post("/snapshots/{snapshot_id}/lock")
def lock_snapshot_endpoint(
    snapshot_id: int,
    user_id: str = Body(..., embed=True),
    lock_type: str = Body("Meeting", embed=True),
    force: bool = Body(False, embed=True),
    db: Session = Depends(get_db)
):
    """Lock snapshot (READY_FOR_REVIEW -> LOCKED) with lock gates."""
    from snapshot_state_machine import SnapshotStateMachine
    state_machine = SnapshotStateMachine(db)
    return state_machine.lock_snapshot(snapshot_id, user_id, lock_type, force)

@app.get("/snapshots/{snapshot_id}/status")
def get_snapshot_status(snapshot_id: int, db: Session = Depends(get_db)):
    """Get snapshot status and lock gate checks."""
    from snapshot_state_machine import SnapshotStateMachine
    state_machine = SnapshotStateMachine(db)
    return state_machine.get_snapshot_status(snapshot_id)

# Workflow objects endpoints
@app.get("/snapshots/{snapshot_id}/exceptions")
def get_snapshot_exceptions(snapshot_id: int, status: str = None, db: Session = Depends(get_db)):
    """Get exceptions for a snapshot."""
    try:
        from workflow_models import WorkflowException
        query = db.query(WorkflowException).filter(WorkflowException.snapshot_id == snapshot_id)
        if status:
            query = query.filter(WorkflowException.status == status)
        exceptions = query.all()
        return [{
            "id": e.id,
            "exception_type": e.exception_type,
            "severity": e.severity,
            "amount": e.amount,
            "status": e.status,
            "assignee": e.assignee,
            "aging_days": e.aging_days,
            "resolution_note": e.resolution_note,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in exceptions]
    except ImportError:
        return []

@app.get("/snapshots/{snapshot_id}/scenarios")
def get_snapshot_scenarios(snapshot_id: int, db: Session = Depends(get_db)):
    """Get scenarios for a snapshot."""
    try:
        from workflow_models import WorkflowScenario
        scenarios = db.query(WorkflowScenario).filter(WorkflowScenario.base_snapshot_id == snapshot_id).all()
        return [{
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "status": s.status,
            "approval_required": bool(s.approval_required),
            "approved_by": s.approved_by,
            "actions_count": len(s.actions) if s.actions else 0
        } for s in scenarios]
    except ImportError:
        return []

@app.get("/snapshots/{snapshot_id}/actions")
def get_snapshot_actions(snapshot_id: int, status: str = None, db: Session = Depends(get_db)):
    """Get actions for a snapshot."""
    try:
        from workflow_models import WorkflowAction
        query = db.query(WorkflowAction).filter(WorkflowAction.snapshot_id == snapshot_id)
        if status:
            query = query.filter(WorkflowAction.status == status)
        actions = query.all()
        return [{
            "id": a.id,
            "action_type": a.action_type,
            "name": a.name,
            "owner": a.owner,
            "expected_impact": a.expected_impact,
            "status": a.status,
            "approvals": a.approvals or [],
            "status_transitions": a.status_transitions or []
        } for a in actions]
    except ImportError:
        return []

@app.get("/snapshots/{snapshot_id}/trust-report")
def get_trust_report(snapshot_id: int, db: Session = Depends(get_db)):
    """
    Generate CFO-facing Trust Certification report.
    
    Returns comprehensive trust metrics:
        - Cash Explained % (amount-weighted)
        - Unknown Exposure € (amount-weighted)
        - Missing FX Exposure € (amount-weighted)
        - Data Freshness Mismatch (hours)
        - Reconciliation Integrity % (amount-weighted)
        - Forecast Calibration Coverage (amount-weighted)
    
    Plus invariant checks:
        - Cash Math (totals balance)
        - Drilldown Sums (detail = summary)
        - Reconciliation Conservation (allocations valid)
        - Snapshot Immutability (locked = frozen)
        - Idempotency (re-import = same result)
        - No Silent FX (no rate=1.0 fallbacks)
    
    And lock gates with CFO override capability.
    """
    from trust_certification import TrustCertificationService
    service = TrustCertificationService(db)
    report = service.generate_trust_report(snapshot_id)
    return report.to_dict()


@app.post("/snapshots/{snapshot_id}/trust-certification/lock")
def attempt_trust_lock(
    snapshot_id: int,
    lock_request: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Attempt to lock a snapshot with trust certification.
    
    Request body:
        {
            "user": "string",
            "override_acknowledgments": {
                "Gate: Missing FX Exposure €": "I acknowledge missing FX rates...",
                ...
            }
        }
    
    Returns:
        - success: bool
        - message: string
        - missing_acknowledgments: list (if overrides needed)
        - trust_report: dict (if successful)
    """
    from trust_certification import TrustCertificationService
    
    user = lock_request.get("user", "anonymous")
    overrides = lock_request.get("override_acknowledgments", {})
    
    service = TrustCertificationService(db)
    result = service.attempt_lock(snapshot_id, user, overrides)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)
    
    return result


@app.get("/snapshots/{snapshot_id}/trust-certification/gates")
def get_trust_gates(snapshot_id: int, db: Session = Depends(get_db)):
    """
    Get current lock gate status for a snapshot.
    
    Returns list of gates with:
        - name
        - passed (bool)
        - can_override (bool)
        - requires_acknowledgment (bool)
        - acknowledgment_text_required (string, if needed)
    """
    from trust_certification import TrustCertificationService
    service = TrustCertificationService(db)
    report = service.generate_trust_report(snapshot_id)
    return {
        "snapshot_id": snapshot_id,
        "lock_eligible": report.lock_eligible,
        "lock_blocked_reasons": report.lock_blocked_reasons,
        "gates": [g.to_dict() for g in report.lock_gates]
    }


@app.get("/snapshots/{snapshot_id}/trust-certification/evidence/{gate_name}")
def get_gate_evidence(
    snapshot_id: int,
    gate_name: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get detailed evidence for a specific trust gate.
    
    Returns paginated list of evidence references with:
        - ref_type (invoice, bank_txn, reconciliation, fx_rate)
        - ref_id
        - ref_key (human-readable identifier)
        - amount
        - currency
        - description
    """
    from trust_certification import TrustCertificationService
    service = TrustCertificationService(db)
    report = service.generate_trust_report(snapshot_id)
    
    # Find the gate
    gate = next((g for g in report.lock_gates if g.name == gate_name), None)
    if not gate:
        raise HTTPException(status_code=404, detail=f"Gate '{gate_name}' not found")
    
    # Get evidence from metric or invariant
    evidence = []
    if gate.metric:
        evidence = gate.metric.evidence
    elif gate.invariant:
        evidence = gate.invariant.evidence
    
    # Paginate
    total = len(evidence)
    evidence_page = evidence[offset:offset + limit]
    
    return {
        "gate_name": gate_name,
        "total_evidence": total,
        "offset": offset,
        "limit": limit,
        "evidence": [e.to_dict() for e in evidence_page]
    }


@app.get("/snapshots/{snapshot_id}/trust-certification/history")
def get_trust_history(snapshot_id: int, db: Session = Depends(get_db)):
    """
    Get trust certification history for a snapshot.
    
    Returns:
        - Previous trust reports
        - Gate overrides with acknowledgments
        - Lock attempts
    """
    # Get trust report records
    reports = db.query(models.TrustReportRecord).filter(
        models.TrustReportRecord.snapshot_id == snapshot_id
    ).order_by(models.TrustReportRecord.generated_at.desc()).all()
    
    # Get gate overrides
    overrides = db.query(models.TrustGateOverride).filter(
        models.TrustGateOverride.snapshot_id == snapshot_id
    ).order_by(models.TrustGateOverride.overridden_at.desc()).all()
    
    return {
        "snapshot_id": snapshot_id,
        "trust_reports": [{
            "id": r.id,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "generated_by": r.generated_by,
            "overall_trust_score": r.overall_trust_score,
            "lock_eligible": bool(r.lock_eligible),
            "status": r.status
        } for r in reports],
        "gate_overrides": [{
            "id": o.id,
            "gate_name": o.gate_name,
            "gate_type": o.gate_type,
            "acknowledgment_text": o.acknowledgment_text,
            "overridden_by": o.overridden_by,
            "overridden_at": o.overridden_at.isoformat() if o.overridden_at else None,
            "gate_value_at_override": o.gate_value_at_override,
            "gate_threshold": o.gate_threshold
        } for o in overrides]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ASYNC OPERATIONS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/async/upload-parsing")
def start_async_upload_parsing(file: UploadFile = File(...), entity_id: int = None, mapping_config: str = Form(None), db: Session = Depends(get_db)):
    """Start async upload parsing task."""
    from async_operations import run_async_upload_parsing
    import json
    
    content = file.file.read()
    mapping = json.loads(mapping_config) if mapping_config else None
    
    task_id = run_async_upload_parsing(db, content, entity_id, mapping)
    return {"task_id": task_id, "status": "pending"}


@app.post("/async/reconciliation")
def start_async_reconciliation(entity_id: int = Body(..., embed=True), db: Session = Depends(get_db)):
    """Start async reconciliation task."""
    from async_operations import run_async_reconciliation
    
    task_id = run_async_reconciliation(db, entity_id)
    return {"task_id": task_id, "status": "pending"}


@app.post("/async/forecast")
def start_async_forecast(snapshot_id: int = Body(..., embed=True), db: Session = Depends(get_db)):
    """Start async forecast computation."""
    from async_operations import run_async_forecast
    
    task_id = run_async_forecast(db, snapshot_id)
    return {"task_id": task_id, "status": "pending"}


@app.get("/async/tasks/{task_id}")
def get_async_task_status(task_id: str, db: Session = Depends(get_db)):
    """Get status of async task."""
    from async_operations import get_task_status
    
    return get_task_status(task_id)
