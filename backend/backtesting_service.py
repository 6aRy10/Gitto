import models
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pandas as pd

def get_forecast_accuracy(db: Session, snapshot_id: int):
    """
    Measures accuracy by comparing predicted_payment_date from invoices
    with actual_receipt_date from reconciled bank transactions.
    """
    # Join Invoice -> ReconciliationTable -> BankTransaction
    # Filter by snapshot_id and where payment has actually happened
    data = db.query(
        models.Invoice.amount,
        models.Invoice.predicted_payment_date,
        models.BankTransaction.transaction_date
    ).join(
        models.ReconciliationTable, models.Invoice.id == models.ReconciliationTable.invoice_id
    ).join(
        models.BankTransaction, models.ReconciliationTable.bank_transaction_id == models.BankTransaction.id
    ).filter(
        models.Invoice.snapshot_id == snapshot_id
    ).all()

    if not data:
        return {"mae_days": 0, "accuracy_3d": 0, "accuracy_7d": 0, "n_count": 0}

    df = pd.DataFrame(data, columns=['amount', 'predicted', 'actual'])
    
    # Calculate error in days
    df['error_days'] = (df['actual'] - df['predicted']).dt.days.abs()
    
    mae = float(df['error_days'].mean())
    acc_3d = float((df['error_days'] <= 3).mean()) * 100
    acc_7d = float((df['error_days'] <= 7).mean()) * 100

    return {
        "mae_days": round(mae, 1),
        "accuracy_3d": round(acc_3d, 1),
        "accuracy_7d": round(acc_7d, 1),
        "n_count": len(df)
    }
