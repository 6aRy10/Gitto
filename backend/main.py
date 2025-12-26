from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
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

import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs connect_args, Postgres does not
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="CFO Cash Command Center API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "CFO Cash Command Center API is running"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), entity_id: int = None, db: Session = Depends(get_db)):
    content = await file.read()
    try:
        df, health = parse_excel_to_df(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing Excel: {str(e)}")
    
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
    
    # #region agent log
    debug_log("Starting bulk save", {"snapshot_id": snapshot.id, "row_count": len(df)}, "A", "main.py:upload_file")
    # #endregion

    for _, row in df.iterrows():
        def get_str(val):
            if pd.isna(val): return ''
            return str(val).strip()

        cid = generate_canonical_id(row, source="Excel", entity_id=entity_id)

        def get_int(val):
            if pd.isna(val): return 0
            try:
                # Handle cases like "30.0" or "30 days"
                s = str(val).split('.')[0]
                s = "".join(c for c in s if c.isdigit())
                return int(s) if s else 0
            except:
                return 0

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
    
    db.bulk_save_objects(invoices)
    db.commit()
    
    # Run behavioral forecast
    run_forecast_model(db, snapshot.id)

    return {"snapshot_id": snapshot.id, "health": health}

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
def run_reconciliation(entity_id: int, db: Session = Depends(get_db)):
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
