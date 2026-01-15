import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current dir to path to import models and utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import models

def run_all_diagnostics():
    engine = create_engine('sqlite:///sql_app.db')
    Session = sessionmaker(bind=engine)
    db = Session()

    snapshots = db.query(models.Snapshot).all()
    print(f"--- Gitto Data Health Audit ---\n")
    print(f"Total Snapshots Found: {len(snapshots)}\n")

    for s in snapshots:
        print(f"Analyzing Snapshot {s.id}: {s.name}")
        
        invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == s.id).all()
        if not invoices:
            print(f"  [!] No invoices found for this snapshot. Skipping.\n")
            continue
            
        # Convert to DataFrame for easier analysis
        data = []
        for inv in invoices:
            data.append({
                'id': inv.id,
                'customer': inv.customer,
                'amount': inv.amount,
                'currency': inv.currency,
                'document_date': inv.document_date,
                'expected_due_date': inv.expected_due_date,
                'document_number': inv.document_number,
                'due_year': inv.due_year
            })
        df = pd.DataFrame(data)
        
        total_rows = len(df)
        
        # CFO-Grade Health Diagnostics (Same logic as utils.py)
        health = {
            "total_invoices": total_rows,
            "completeness": {
                "missing_due_dates": int(df['expected_due_date'].isna().sum()),
                "missing_customers": int(df['customer'].isna().sum()) if 'customer' in df.columns else total_rows,
                "missing_amounts": int((df['amount'] == 0).sum()) if 'amount' in df.columns else total_rows,
                "currency_mix": df['currency'].value_counts().to_dict() if 'currency' in df.columns else {}
            },
            "behavioral_blind_spots": {
                "no_history_customers": 0, # Requires historical context
                "regime_shift_risk": int((pd.to_numeric(df['due_year'], errors='coerce') > (datetime.now().year + 1)).sum()) if 'due_year' in df.columns else 0,
                "future_anomaly_dates": int((df['expected_due_date'] > (datetime.now() + timedelta(days=365*2))).sum()) if 'expected_due_date' in df.columns else 0
            },
            "integrity": {
                "duplicate_keys": int(df.duplicated(subset=['document_number', 'customer']).sum()) if 'document_number' in df.columns and 'customer' in df.columns else 0,
                "backdated_invoices": int((df['document_date'] < (datetime.now() - timedelta(days=365))).sum()) if 'document_date' in df.columns else 0
            }
        }
        
        # Update DB
        s.data_health = health
        db.commit()
        
        # Print Results
        print(f"  - Total Invoices: {total_rows}")
        print(f"  - Completeness:")
        print(f"    * Missing Due Dates: {health['completeness']['missing_due_dates']}")
        print(f"    * Missing Customers: {health['completeness']['missing_customers']}")
        print(f"    * Missing Amounts: {health['completeness']['missing_amounts']}")
        print(f"    * Currency Mix: {health['completeness']['currency_mix']}")
        print(f"  - Integrity:")
        print(f"    * Duplicate Keys: {health['integrity']['duplicate_keys']}")
        print(f"    * Backdated Invoices (>1yr): {health['integrity']['backdated_invoices']}")
        print(f"  - Blind Spots:")
        print(f"    * Regime Shift Risk (Future Years): {health['behavioral_blind_spots']['regime_shift_risk']}")
        print(f"    * Future Anomaly Dates (>2yrs): {health['behavioral_blind_spots']['future_anomaly_dates']}")
        print(f"  [DONE] Health record updated in database.\n")

    db.close()
    print(f"--- Audit Complete ---")

if __name__ == "__main__":
    run_all_diagnostics()


import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current dir to path to import models and utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import models

def run_all_diagnostics():
    engine = create_engine('sqlite:///sql_app.db')
    Session = sessionmaker(bind=engine)
    db = Session()

    snapshots = db.query(models.Snapshot).all()
    print(f"--- Gitto Data Health Audit ---\n")
    print(f"Total Snapshots Found: {len(snapshots)}\n")

    for s in snapshots:
        print(f"Analyzing Snapshot {s.id}: {s.name}")
        
        invoices = db.query(models.Invoice).filter(models.Invoice.snapshot_id == s.id).all()
        if not invoices:
            print(f"  [!] No invoices found for this snapshot. Skipping.\n")
            continue
            
        # Convert to DataFrame for easier analysis
        data = []
        for inv in invoices:
            data.append({
                'id': inv.id,
                'customer': inv.customer,
                'amount': inv.amount,
                'currency': inv.currency,
                'document_date': inv.document_date,
                'expected_due_date': inv.expected_due_date,
                'document_number': inv.document_number,
                'due_year': inv.due_year
            })
        df = pd.DataFrame(data)
        
        total_rows = len(df)
        
        # CFO-Grade Health Diagnostics (Same logic as utils.py)
        health = {
            "total_invoices": total_rows,
            "completeness": {
                "missing_due_dates": int(df['expected_due_date'].isna().sum()),
                "missing_customers": int(df['customer'].isna().sum()) if 'customer' in df.columns else total_rows,
                "missing_amounts": int((df['amount'] == 0).sum()) if 'amount' in df.columns else total_rows,
                "currency_mix": df['currency'].value_counts().to_dict() if 'currency' in df.columns else {}
            },
            "behavioral_blind_spots": {
                "no_history_customers": 0, # Requires historical context
                "regime_shift_risk": int((pd.to_numeric(df['due_year'], errors='coerce') > (datetime.now().year + 1)).sum()) if 'due_year' in df.columns else 0,
                "future_anomaly_dates": int((df['expected_due_date'] > (datetime.now() + timedelta(days=365*2))).sum()) if 'expected_due_date' in df.columns else 0
            },
            "integrity": {
                "duplicate_keys": int(df.duplicated(subset=['document_number', 'customer']).sum()) if 'document_number' in df.columns and 'customer' in df.columns else 0,
                "backdated_invoices": int((df['document_date'] < (datetime.now() - timedelta(days=365))).sum()) if 'document_date' in df.columns else 0
            }
        }
        
        # Update DB
        s.data_health = health
        db.commit()
        
        # Print Results
        print(f"  - Total Invoices: {total_rows}")
        print(f"  - Completeness:")
        print(f"    * Missing Due Dates: {health['completeness']['missing_due_dates']}")
        print(f"    * Missing Customers: {health['completeness']['missing_customers']}")
        print(f"    * Missing Amounts: {health['completeness']['missing_amounts']}")
        print(f"    * Currency Mix: {health['completeness']['currency_mix']}")
        print(f"  - Integrity:")
        print(f"    * Duplicate Keys: {health['integrity']['duplicate_keys']}")
        print(f"    * Backdated Invoices (>1yr): {health['integrity']['backdated_invoices']}")
        print(f"  - Blind Spots:")
        print(f"    * Regime Shift Risk (Future Years): {health['behavioral_blind_spots']['regime_shift_risk']}")
        print(f"    * Future Anomaly Dates (>2yrs): {health['behavioral_blind_spots']['future_anomaly_dates']}")
        print(f"  [DONE] Health record updated in database.\n")

    db.close()
    print(f"--- Audit Complete ---")

if __name__ == "__main__":
    run_all_diagnostics()

