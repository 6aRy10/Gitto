"""
Comprehensive Audit Logging Service
Ensures all critical operations are logged for CFO trust and compliance.
"""

from sqlalchemy.orm import Session
from datetime import datetime
import models
from typing import Optional, Dict, Any


def log_snapshot_action(
    db: Session,
    user: str,
    action: str,
    snapshot_id: int,
    changes: Optional[Dict[str, Any]] = None
):
    """Log snapshot create/lock/unlock/delete actions"""
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="Snapshot",
        resource_id=snapshot_id,
        changes=changes
    )
    db.add(log)
    db.commit()


def log_reconciliation_action(
    db: Session,
    user: str,
    action: str,
    transaction_id: int,
    invoice_id: Optional[int] = None,
    match_type: Optional[str] = None,
    confidence: Optional[float] = None,
    changes: Optional[Dict[str, Any]] = None
):
    """Log reconciliation matches, especially manual overrides"""
    log_data = {
        "transaction_id": transaction_id,
        "invoice_id": invoice_id,
        "match_type": match_type,
        "confidence": confidence
    }
    if changes:
        log_data.update(changes)
    
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="Reconciliation",
        resource_id=transaction_id,
        changes=log_data
    )
    db.add(log)
    db.commit()


def log_forecast_action(
    db: Session,
    user: str,
    action: str,
    snapshot_id: int,
    changes: Optional[Dict[str, Any]] = None
):
    """Log forecast recomputations"""
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="Forecast",
        resource_id=snapshot_id,
        changes=changes
    )
    db.add(log)
    db.commit()


def log_fx_action(
    db: Session,
    user: str,
    action: str,
    snapshot_id: int,
    from_currency: str,
    to_currency: str,
    old_rate: Optional[float] = None,
    new_rate: Optional[float] = None
):
    """Log FX rate changes"""
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="FXRate",
        resource_id=snapshot_id,
        changes={
            "from_currency": from_currency,
            "to_currency": to_currency,
            "old_rate": old_rate,
            "new_rate": new_rate
        }
    )
    db.add(log)
    db.commit()


def log_bill_action(
    db: Session,
    user: str,
    action: str,
    bill_id: int,
    field: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None
):
    """Log vendor bill hold status, discretionary flag changes"""
    changes = {}
    if field:
        changes[field] = {"old": old_value, "new": new_value}
    
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="VendorBill",
        resource_id=bill_id,
        changes=changes
    )
    db.add(log)
    db.commit()


def log_lever_action(
    db: Session,
    user: str,
    action: str,
    lever_id: int,
    expected_impact: Optional[float] = None,
    realized_impact: Optional[float] = None,
    changes: Optional[Dict[str, Any]] = None
):
    """Log liquidity lever executions"""
    log_data = {
        "expected_impact": expected_impact,
        "realized_impact": realized_impact
    }
    if changes:
        log_data.update(changes)
    
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="Lever",
        resource_id=lever_id,
        changes=log_data
    )
    db.add(log)
    db.commit()


def log_policy_action(
    db: Session,
    user: str,
    action: str,
    entity_id: int,
    policy_type: str,
    changes: Optional[Dict[str, Any]] = None
):
    """Log matching policy, payment run, tolerance changes"""
    log_data = {"policy_type": policy_type}
    if changes:
        log_data.update(changes)
    
    log = models.AuditLog(
        timestamp=datetime.utcnow(),
        user=user,
        action=action,
        resource_type="Policy",
        resource_id=entity_id,
        changes=log_data
    )
    db.add(log)
    db.commit()


def get_audit_trail(
    db: Session,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """Retrieve audit trail with filters"""
    query = db.query(models.AuditLog)
    
    if resource_type:
        query = query.filter(models.AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(models.AuditLog.resource_id == resource_id)
    if action:
        query = query.filter(models.AuditLog.action == action)
    
    return query.order_by(models.AuditLog.timestamp.desc()).limit(limit).all()





