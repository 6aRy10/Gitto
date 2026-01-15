"""
Unmatched Transaction Lifecycle Service
Tracks status, assignee, SLA aging for unmatched transactions.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import models


def get_unmatched_transactions(
    db: Session,
    entity_id: int,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    days_unmatched_min: Optional[int] = None
) -> List[models.BankTransaction]:
    """Get unmatched transactions with filters"""
    query = db.query(models.BankTransaction).join(
        models.BankAccount
    ).filter(
        models.BankAccount.entity_id == entity_id,
        models.BankTransaction.is_reconciled == 0
    )
    
    if status:
        query = query.filter(models.BankTransaction.reconciliation_type == status)
    if assignee:
        query = query.filter(models.BankTransaction.assignee == assignee)
    
    transactions = query.all()
    
    # Filter by days unmatched if specified
    if days_unmatched_min is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=days_unmatched_min)
        transactions = [
            txn for txn in transactions
            if txn.transaction_date and txn.transaction_date < cutoff_date
        ]
    
    return transactions


def update_transaction_status(
    db: Session,
    transaction_id: int,
    status: str,
    assignee: Optional[str] = None,
    notes: Optional[str] = None
):
    """Update unmatched transaction status"""
    txn = db.query(models.BankTransaction).filter(models.BankTransaction.id == transaction_id).first()
    
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    
    old_status = txn.reconciliation_type
    old_assignee = txn.assignee
    
    txn.reconciliation_type = status
    if assignee:
        txn.assignee = assignee
    
    # Update resolution status
    if status in ["Resolved", "Escalated"]:
        txn.resolution_status = status
    elif status == "In_Review":
        txn.resolution_status = "Match Suggested"
    
    db.commit()
    
    # Log status change
    from audit_service import log_reconciliation_action
    log_reconciliation_action(
        db, "system", "StatusChange", transaction_id,
        changes={
            "old_status": old_status,
            "new_status": status,
            "old_assignee": old_assignee,
            "new_assignee": assignee,
            "notes": notes
        }
    )


def assign_transaction(
    db: Session,
    transaction_id: int,
    assignee: str
):
    """Assign unmatched transaction to user"""
    txn = db.query(models.BankTransaction).filter(models.BankTransaction.id == transaction_id).first()
    
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    
    old_assignee = txn.assignee
    txn.assignee = assignee
    
    # Auto-update status if not already assigned
    if txn.reconciliation_type == "Manual" or not txn.reconciliation_type:
        txn.reconciliation_type = "Assigned"
    
    db.commit()
    
    # Log assignment
    from audit_service import log_reconciliation_action
    log_reconciliation_action(
        db, assignee, "Assign", transaction_id,
        changes={
            "old_assignee": old_assignee,
            "new_assignee": assignee
        }
    )


def get_sla_aging_report(
    db: Session,
    entity_id: int
) -> Dict[str, Any]:
    """Get SLA aging report for unmatched transactions"""
    unmatched = get_unmatched_transactions(db, entity_id)
    
    now = datetime.utcnow()
    aging_buckets = {
        "0-7_days": [],
        "8-14_days": [],
        "15-30_days": [],
        "30+_days": []
    }
    
    for txn in unmatched:
        if not txn.transaction_date:
            continue
        
        days_unmatched = (now - txn.transaction_date).days
        
        if days_unmatched <= 7:
            aging_buckets["0-7_days"].append(txn)
        elif days_unmatched <= 14:
            aging_buckets["8-14_days"].append(txn)
        elif days_unmatched <= 30:
            aging_buckets["15-30_days"].append(txn)
        else:
            aging_buckets["30+_days"].append(txn)
    
    return {
        "total_unmatched": len(unmatched),
        "by_aging": {
            bucket: {
                "count": len(txns),
                "amount": sum(txn.amount for txn in txns),
                "transaction_ids": [txn.id for txn in txns]
            }
            for bucket, txns in aging_buckets.items()
        },
        "by_status": _group_by_status(unmatched),
        "by_assignee": _group_by_assignee(unmatched)
    }


def _group_by_status(transactions: List[models.BankTransaction]) -> Dict[str, Any]:
    """Group transactions by status"""
    by_status = {}
    for txn in transactions:
        status = txn.reconciliation_type or "New"
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(txn)
    
    return {
        status: {
            "count": len(txns),
            "amount": sum(txn.amount for txn in txns)
        }
        for status, txns in by_status.items()
    }


def _group_by_assignee(transactions: List[models.BankTransaction]) -> Dict[str, Any]:
    """Group transactions by assignee"""
    by_assignee = {}
    for txn in transactions:
        assignee = txn.assignee or "Unassigned"
        if assignee not in by_assignee:
            by_assignee[assignee] = []
        by_assignee[assignee].append(txn)
    
    return {
        assignee: {
            "count": len(txns),
            "amount": sum(txn.amount for txn in txns)
        }
        for assignee, txns in by_assignee.items()
    }





