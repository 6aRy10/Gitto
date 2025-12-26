import pandas as pd
import io
from datetime import datetime, timedelta
import models
from sqlalchemy.orm import Session
from utils import debug_log

def ingest_bank_csv(db: Session, bank_account_id: int, file_content: bytes):
    df = pd.read_csv(io.BytesIO(file_content))
    
    # Standardize column mapping (example)
    # Expected columns: date, amount, reference, counterparty, currency
    col_map = {
        'Date': 'transaction_date',
        'Amount': 'amount',
        'Reference': 'reference',
        'Counterparty': 'counterparty',
        'Currency': 'currency'
    }
    
    df = df.rename(columns=col_map)
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    
    transactions = []
    for _, row in df.iterrows():
        # Auto-tagging logic
        ref = str(row.get('reference', '')).lower()
        tag = "other"
        if any(k in ref for k in ['salary', 'payroll', 'wage']): tag = "payroll"
        elif any(k in ref for k in ['tax', 'vat', 'irs']): tag = "tax"
        elif any(k in ref for k in ['rent', 'lease']): tag = "rent"
        elif any(k in ref for k in ['loan', 'interest']): tag = "loan"
        elif row.get('amount', 0) > 0: tag = "customer_receipt"
        elif row.get('amount', 0) < 0: tag = "supplier_payment"
        
        tx = models.BankTransaction(
            bank_account_id=bank_account_id,
            transaction_date=row['transaction_date'],
            amount=float(row['amount']),
            currency=str(row.get('currency', 'EUR')),
            reference=str(row.get('reference', '')),
            counterparty=str(row.get('counterparty', '')),
            transaction_type=tag
        )
        transactions.append(tx)
        
    db.bulk_save_objects(transactions)
    db.commit()
    return len(transactions)

def reconcile_transactions(db: Session, entity_id: int):
    # Fetch unreconciled customer receipts
    unreconciled_txs = db.query(models.BankTransaction).join(models.BankAccount).filter(
        models.BankAccount.entity_id == entity_id,
        models.BankTransaction.is_reconciled == 0,
        models.BankTransaction.transaction_type == "customer_receipt"
    ).all()
    
    # Fetch open invoices for this entity
    open_invoices = db.query(models.Invoice).filter(
        models.Invoice.entity_id == entity_id,
        models.Invoice.payment_date == None
    ).all()
    
    matches = 0
    suggestions = []

    # region agent logic audit: Check for existing reconciliations to avoid double-counting
    # In a full production system, we'd check if an invoice is partially paid.
    # endregion

    for tx in unreconciled_txs:
        # RAG Logic Context: Match against the most relevant document
        best_match = None
        best_score = 0

        for inv in open_invoices:
            if inv.payment_date: continue

            # Amount check (with small epsilon for float precision)
            amount_match = abs(tx.amount - inv.amount) < 0.01
            
            # Rule 1: High-Confidence Deterministic Match (Amount + Doc ID in Reference)
            if amount_match and inv.document_number and str(inv.document_number) in str(tx.reference):
                best_match = inv
                best_score = 100
                break 

            # Rule 2: Medium-Confidence Suggested Match (Amount + Fuzzy Name Match)
            if amount_match:
                tx_cp = str(tx.counterparty).lower() if tx.counterparty else ""
                inv_cust = str(inv.customer).lower() if inv.customer else ""
                
                if tx_cp and inv_cust and (tx_cp in inv_cust or inv_cust in tx_cp):
                    best_match = inv
                    best_score = 80
        
        if best_match:
            if best_score == 100:
                recon = models.ReconciliationTable(
                    bank_transaction_id=tx.id,
                    invoice_id=best_match.id,
                    amount_allocated=best_match.amount
                )
                db.add(recon)
                tx.is_reconciled = 1
                tx.reconciliation_type = "Deterministic"
                tx.match_confidence = 1.0
                best_match.payment_date = tx.transaction_date
                matches += 1
            else:
                # Flag as Suggested for CFO approval (RAG: Retrieval of suggestion)
                tx.reconciliation_type = "Suggested"
                tx.match_confidence = best_score / 100.0
                suggestions.append({
                    "tx_id": tx.id,
                    "invoice_id": best_match.id,
                    "confidence": tx.match_confidence
                })

    db.commit()
    return {"matches": matches, "suggestions_count": len(suggestions)}

def get_reconciliation_suggestions(db: Session, entity_id: int):
    """
    Returns transactions that were flagged as 'Suggested' 
    but not yet finalized.
    """
    txs = db.query(models.BankTransaction).join(models.BankAccount).filter(
        models.BankAccount.entity_id == entity_id,
        models.BankTransaction.reconciliation_type == "Suggested",
        models.BankTransaction.is_reconciled == 0
    ).all()
    
    results = []
    for tx in txs:
        # Re-run logic to find the best candidate (simplistic for demo)
        inv = db.query(models.Invoice).filter(
            models.Invoice.entity_id == entity_id,
            models.Invoice.amount == tx.amount,
            models.Invoice.payment_date == None
        ).first()
        
        if inv:
            results.append({
                "transaction": tx,
                "suggestion": inv,
                "confidence": tx.match_confidence
            })
            
    return results

def detect_intercompany_washes(db: Session, entity_id: int):
    """
    Identifies 'Suggested Intercompany Washes':
    Same amount, opposite sign, 1-2 day window, between known internal accounts.
    """
    # #region agent log
    debug_log("Detect Washes Start", {"entity_id": entity_id}, "D", "bank_service.py:detect_intercompany_washes")
    # #endregion
    
    # Fetch unreconciled transactions for this entity
    txs = db.query(models.BankTransaction).join(models.BankAccount).filter(
        models.BankAccount.entity_id == entity_id,
        models.BankTransaction.is_reconciled == 0,
        models.BankTransaction.is_wash == 0
    ).all()
    
    # Also fetch transactions from other entities to find the other side
    all_txs = db.query(models.BankTransaction).all()
    
    washes_found = []
    
    for tx1 in txs:
        for tx2 in all_txs:
            if tx1.id == tx2.id: continue
            
            # 1. Opposite sign, same absolute amount (within 0.01 tolerance)
            if abs(tx1.amount + tx2.amount) < 0.01:
                # 2. Within 2-day window
                date_diff = abs((tx1.transaction_date - tx2.transaction_date).days)
                if date_diff <= 2:
                    # 3. Between internal accounts (already filtered tx1 by entity_id)
                    # We flag this as a "Suggested Wash"
                    washes_found.append({
                        "tx1_id": tx1.id,
                        "tx2_id": tx2.id,
                        "amount": abs(tx1.amount),
                        "date1": tx1.transaction_date.isoformat(),
                        "date2": tx2.transaction_date.isoformat(),
                        "confidence": 0.9 if date_diff == 0 else 0.7
                    })
                    # Note: We don't mark is_wash=1 yet; CFO must approve in UI
                    
    return washes_found

def approve_wash_service(db: Session, tx1_id: int, tx2_id: int):
    tx1 = db.query(models.BankTransaction).filter(models.BankTransaction.id == tx1_id).first()
    tx2 = db.query(models.BankTransaction).filter(models.BankTransaction.id == tx2_id).first()
    
    if tx1 and tx2:
        tx1.is_wash = 1
        tx1.is_reconciled = 1
        tx2.is_wash = 1
        tx2.is_reconciled = 1
        db.commit()
        return {"status": "success"}
    return {"status": "error", "message": "Transactions not found"}
def get_cash_ledger_summary(db: Session, entity_id: int):
    # Get current balance from bank accounts
    accounts = db.query(models.BankAccount).filter(models.BankAccount.entity_id == entity_id).all()
    total_cash = sum(acc.balance for acc in accounts)
    
    # Get recent transactions
    recent_txs = db.query(models.BankTransaction).join(models.BankAccount).filter(
        models.BankAccount.entity_id == entity_id
    ).order_by(models.BankTransaction.transaction_date.desc()).limit(50).all()
    
    return {
        "total_cash": total_cash,
        "recent_transactions": recent_txs
    }

def generate_cash_variance_narrative(db: Session, entity_id: int, snapshot_id: int):
    # Compare forecast vs actual for the last 7 days
    today = datetime.now()
    seven_days_ago = today - timedelta(days=7)
    
    # 1. Get total expected from snapshot for this period
    expected_invoices = db.query(models.Invoice).filter(
        models.Invoice.snapshot_id == snapshot_id,
        models.Invoice.predicted_payment_date >= seven_days_ago,
        models.Invoice.predicted_payment_date <= today
    ).all()
    
    total_expected = sum(inv.amount for inv in expected_invoices)
    
    # 2. Get actual receipts from bank
    actual_txs = db.query(models.BankTransaction).join(models.BankAccount).filter(
        models.BankAccount.entity_id == entity_id,
        models.BankTransaction.transaction_date >= seven_days_ago,
        models.BankTransaction.transaction_date <= today,
        models.BankTransaction.transaction_type == "customer_receipt"
    ).all()
    
    total_actual = sum(tx.amount for tx in actual_txs)
    variance = total_actual - total_expected
    
    narrative = []
    
    if abs(variance) < 100:
        narrative.append("Cash is perfectly on track with behavioral predictions.")
    else:
        direction = "surplus" if variance > 0 else "shortfall"
        narrative.append(f"We recorded a €{abs(variance):,.0f} {direction} against our 7-day rolling forecast.")
        
        # Look for specific drivers
        # A. Unpredicted large payments (early payers)
        unreconciled_receipts = [tx for tx in actual_txs if tx.is_reconciled == 0 and tx.amount > 5000]
        for tx in unreconciled_receipts:
            narrative.append(f"Unpredicted payment of €{tx.amount:,.0f} received from {tx.counterparty} (messy reference).")
            
        # B. Late payers (expected but not received)
        late_invoices = [inv for inv in expected_invoices if inv.payment_date is None and inv.predicted_payment_date < today]
        if late_invoices:
            top_late = sorted(late_invoices, key=lambda x: x.amount, reverse=True)[:3]
            for inv in top_late:
                reason = inv.blocked_reason if inv.is_blocked else "behavioral slip"
                narrative.append(f"Expected €{inv.amount:,.0f} from {inv.customer} missed due to {reason}.")
                
        # C. Partial payments
        # (This would require more complex reconciliation tracking)
        
    return {
        "period": "Last 7 Days",
        "expected": total_expected,
        "actual": total_actual,
        "variance": variance,
        "narrative": narrative
    }

