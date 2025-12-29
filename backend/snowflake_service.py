import pandas as pd
from sqlalchemy import create_engine
from snowflake.sqlalchemy import URL
import models
from datetime import datetime
from utils import run_forecast_model

def get_snowflake_engine(config: models.SnowflakeConfig):
    return create_engine(URL(
        account=config.account,
        user=config.user,
        password=config.password,
        database=config.database,
        schema=config.schema_name,
        warehouse=config.warehouse,
        role=config.role
    ))

def fetch_snowflake_data(config: models.SnowflakeConfig):
    engine = get_snowflake_engine(config)
    
    mapping_info = config.invoice_mapping
    table_name = mapping_info.get("table")
    mapping = mapping_info.get("mapping")
    
    # Build query selecting only mapped columns
    columns = [f'"{v}" as {k}' for k, v in mapping.items()]
    query = f"SELECT {', '.join(columns)} FROM {table_name}"
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
        
    return df

def sync_snowflake_to_snapshot(db, config_id: int):
    config = db.query(models.SnowflakeConfig).filter(models.SnowflakeConfig.id == config_id).first()
    if not config:
        return None
    
    df = fetch_snowflake_data(config)
    
    # Data Health check (similar to utils.py)
    health = {
        "total_invoices": len(df),
        "paid_invoices": int(df['payment_date'].notna().sum()) if 'payment_date' in df.columns else 0,
        "open_invoices": int(df['payment_date'].isna().sum()) if 'payment_date' in df.columns else len(df),
        "missing_due_dates": int(df['expected_due_date'].isna().sum()) if 'expected_due_date' in df.columns else 0,
        "source": "Snowflake"
    }
    
    # Create Snapshot
    snapshot = models.Snapshot(
        name=f"Snowflake Sync {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        data_health=health
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    # Convert dates to datetime objects
    date_cols = ['document_date', 'invoice_issue_date', 'expected_due_date', 'payment_date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Save Invoices
    invoices = []
    for _, row in df.iterrows():
        inv = models.Invoice(
            snapshot_id=snapshot.id,
            project_desc=str(row.get('project_desc', '')),
            project=str(row.get('project', '')),
            country=str(row.get('country', '')),
            customer=str(row.get('customer', '')),
            document_number=str(row.get('document_number', '')),
            terms_of_payment=str(row.get('terms_of_payment', '')),
            payment_terms_days=int(row.get('payment_terms_days', 0)) if pd.notna(row.get('payment_terms_days')) else 0,
            document_date=row.get('document_date') if pd.notna(row.get('document_date')) else None,
            invoice_issue_date=row.get('invoice_issue_date') if pd.notna(row.get('invoice_issue_date')) else None,
            expected_due_date=row.get('expected_due_date') if pd.notna(row.get('expected_due_date')) else None,
            payment_date=row.get('payment_date') if pd.notna(row.get('payment_date')) else None,
            amount=float(row.get('amount', 0)) if pd.notna(row.get('amount')) else 0,
            currency=str(row.get('currency', 'EUR')),
            due_year=int(pd.to_datetime(row.get('expected_due_date')).year) if pd.notna(row.get('expected_due_date')) else 0
        )
        invoices.append(inv)
    
    db.bulk_save_objects(invoices)
    db.commit()
    
    # Update config sync time
    config.last_sync_at = datetime.now()
    db.commit()
    
    # Run Forecast Model
    run_forecast_model(db, snapshot.id)
    
    return snapshot.id








