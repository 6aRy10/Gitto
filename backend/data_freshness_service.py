"""
Data Freshness Service
Detects and warns about age conflicts between bank and ERP data.
"""

from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import models


def check_data_freshness(db: Session, entity_id: int) -> Dict[str, Any]:
    """
    Check data freshness for an entity.
    Detects conflicts between bank statement age and ERP snapshot age.
    """
    entity = db.query(models.Entity).filter(models.Entity.id == entity_id).first()
    if not entity:
        return {"has_conflict": False, "error": "Entity not found"}
    
    # Get latest snapshot (ERP data)
    latest_snapshot = db.query(models.Snapshot).filter(
        models.Snapshot.entity_id == entity_id
    ).order_by(models.Snapshot.created_at.desc()).first()
    
    if not latest_snapshot:
        return {"has_conflict": False, "erp_age_hours": None, "bank_age_hours": None}
    
    erp_age_hours = (datetime.utcnow() - latest_snapshot.created_at).total_seconds() / 3600
    
    # Get latest bank statement
    bank_accounts = db.query(models.BankAccount).filter(
        models.BankAccount.entity_id == entity_id
    ).all()
    
    bank_age_hours = None
    if bank_accounts:
        # Get most recent sync date
        sync_dates = [
            acct.last_sync_at for acct in bank_accounts
            if hasattr(acct, 'last_sync_at') and acct.last_sync_at
        ]
        if sync_dates:
            latest_sync = max(sync_dates)
            bank_age_hours = (datetime.utcnow() - latest_sync).total_seconds() / 3600
    
    # Check for conflict (threshold: 24 hours difference)
    threshold_hours = 24.0
    has_conflict = False
    
    if erp_age_hours is not None and bank_age_hours is not None:
        age_diff = abs(erp_age_hours - bank_age_hours)
        has_conflict = age_diff > threshold_hours
    
    return {
        "has_conflict": has_conflict,
        "erp_age_hours": erp_age_hours,
        "bank_age_hours": bank_age_hours,
        "age_diff_hours": abs(erp_age_hours - bank_age_hours) if (erp_age_hours and bank_age_hours) else None,
        "threshold_hours": threshold_hours
    }


def get_data_freshness_summary(db: Session, entity_id: int) -> Dict[str, Any]:
    """
    Get detailed freshness summary with warnings.
    """
    freshness = check_data_freshness(db, entity_id)
    
    warnings = []
    if freshness.get('has_conflict'):
        warnings.append({
            "type": "age_mismatch",
            "message": f"Bank and ERP data age mismatch: {freshness.get('age_diff_hours', 0):.1f} hours",
            "severity": "high"
        })
    
    if freshness.get('bank_age_hours', 0) > 48:
        warnings.append({
            "type": "stale_bank_data",
            "message": f"Bank data is {freshness.get('bank_age_hours', 0):.1f} hours old",
            "severity": "medium"
        })
    
    if freshness.get('erp_age_hours', 0) > 48:
        warnings.append({
            "type": "stale_erp_data",
            "message": f"ERP data is {freshness.get('erp_age_hours', 0):.1f} hours old",
            "severity": "medium"
        })
    
    return {
        **freshness,
        "warnings": warnings,
        "should_block_lock": freshness.get('has_conflict', False) or freshness.get('bank_age_hours', 0) > 48
    }
