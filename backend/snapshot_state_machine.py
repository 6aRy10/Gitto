"""
Snapshot State Machine Service

State transitions: DRAFT -> READY_FOR_REVIEW -> LOCKED

Lock gates:
- Missing FX threshold: % of invoices missing FX rates must be below threshold
- Unexplained cash threshold: % of cash unexplained must be below threshold
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
import models
from sqlalchemy import func, and_


class SnapshotStateMachine:
    """Manages snapshot state transitions with lock gates."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def mark_ready_for_review(
        self,
        snapshot_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Transition snapshot from DRAFT to READY_FOR_REVIEW.
        
        Returns:
            Dict with snapshot status and gate check results
        """
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        if snapshot.status != models.SnapshotStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot mark ready for review: snapshot is in {snapshot.status} status"
            )
        
        # Check lock gates (warnings only, don't block)
        gate_checks = self._check_lock_gates(snapshot)
        
        # Transition to READY_FOR_REVIEW
        snapshot.status = models.SnapshotStatus.READY_FOR_REVIEW
        snapshot.ready_for_review_at = datetime.now(timezone.utc)
        snapshot.ready_for_review_by = user_id
        snapshot.lock_gate_checks = gate_checks
        
        self.db.commit()
        
        return {
            "snapshot_id": snapshot_id,
            "status": snapshot.status,
            "ready_for_review_at": snapshot.ready_for_review_at.isoformat(),
            "ready_for_review_by": snapshot.ready_for_review_by,
            "lock_gate_checks": gate_checks
        }
    
    def lock_snapshot(
        self,
        snapshot_id: int,
        user_id: str,
        lock_type: str = "Meeting",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Transition snapshot from READY_FOR_REVIEW to LOCKED.
        
        Lock gates must pass unless force=True.
        
        Args:
            snapshot_id: Snapshot ID
            user_id: User locking the snapshot
            lock_type: Type of lock (Meeting, Fiscal, Scenario)
            force: If True, bypass lock gates
        
        Returns:
            Dict with snapshot status and gate check results
        
        Raises:
            HTTPException: If lock gates fail and force=False
        """
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        if snapshot.status != models.SnapshotStatus.READY_FOR_REVIEW:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot lock: snapshot must be READY_FOR_REVIEW (currently {snapshot.status})"
            )
        
        # Check lock gates
        gate_checks = self._check_lock_gates(snapshot)
        
        # Validate gates pass (unless forced)
        if not force:
            gate_errors = []
            
            if not gate_checks["missing_fx_rate"]["passed"]:
                gate_errors.append(
                    f"Missing FX rate threshold exceeded: {gate_checks['missing_fx_rate']['actual_pct']:.1f}% "
                    f"(threshold: {snapshot.missing_fx_threshold}%)"
                )
            
            if not gate_checks["unexplained_cash"]["passed"]:
                gate_errors.append(
                    f"Unexplained cash threshold exceeded: {gate_checks['unexplained_cash']['actual_pct']:.1f}% "
                    f"(threshold: {snapshot.unexplained_cash_threshold}%)"
                )
            
            if gate_errors:
                raise HTTPException(
                    status_code=400,
                    detail="Lock gates failed:\n" + "\n".join(gate_errors)
                )
        
        # Transition to LOCKED
        snapshot.status = models.SnapshotStatus.LOCKED
        snapshot.is_locked = 1
        snapshot.lock_type = lock_type
        snapshot.locked_at = datetime.now(timezone.utc)
        snapshot.locked_by = user_id
        snapshot.lock_gate_checks = gate_checks
        
        self.db.commit()
        
        return {
            "snapshot_id": snapshot_id,
            "status": snapshot.status,
            "is_locked": True,
            "lock_type": lock_type,
            "locked_at": snapshot.locked_at.isoformat(),
            "locked_by": snapshot.locked_by,
            "lock_gate_checks": gate_checks
        }
    
    def _check_lock_gates(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """
        Check lock gates for snapshot.
        
        Returns:
            Dict with gate check results
        """
        checks = {
            "missing_fx_rate": self._check_missing_fx_rate(snapshot),
            "unexplained_cash": self._check_unexplained_cash(snapshot)
        }
        
        return checks
    
    def _check_missing_fx_rate(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Check missing FX rate gate."""
        # Count invoices with missing FX rates
        total_invoices = self.db.query(func.count(models.Invoice.id)).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).scalar() or 0
        
        if total_invoices == 0:
            return {
                "passed": True,
                "actual_pct": 0.0,
                "threshold": snapshot.missing_fx_threshold,
                "message": "No invoices to check"
            }
        
        # Count invoices with currency != entity currency and missing FX rate
        entity = self.db.query(models.Entity).filter(
            models.Entity.id == snapshot.entity_id
        ).first()
        
        entity_currency = entity.currency if entity else "EUR"
        
        missing_fx_count = self.db.query(func.count(models.Invoice.id)).filter(
            and_(
                models.Invoice.snapshot_id == snapshot.id,
                models.Invoice.currency != entity_currency,
                ~models.Invoice.id.in_(
                    self.db.query(models.WeeklyFXRate.invoice_id).filter(
                        models.WeeklyFXRate.snapshot_id == snapshot.id
                    )
                )
            )
        ).scalar() or 0
        
        actual_pct = (missing_fx_count / total_invoices) * 100.0
        passed = actual_pct <= snapshot.missing_fx_threshold
        
        return {
            "passed": passed,
            "actual_pct": actual_pct,
            "threshold": snapshot.missing_fx_threshold,
            "missing_count": missing_fx_count,
            "total_count": total_invoices,
            "message": f"{actual_pct:.1f}% of invoices missing FX rates"
        }
    
    def _check_unexplained_cash(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Check unexplained cash gate."""
        from utils import get_unknown_bucket
        
        unknown_bucket = get_unknown_bucket(self.db, snapshot.id)
        
        # Get total cash position
        total_cash = snapshot.opening_bank_balance or 0.0
        
        # Calculate unexplained cash percentage
        unknown_amount = unknown_bucket.get("unknown_amount", 0.0)
        actual_pct = (unknown_amount / total_cash * 100.0) if total_cash > 0 else 0.0
        passed = actual_pct <= snapshot.unexplained_cash_threshold
        
        return {
            "passed": passed,
            "actual_pct": actual_pct,
            "threshold": snapshot.unexplained_cash_threshold,
            "unknown_amount": unknown_amount,
            "total_cash": total_cash,
            "message": f"{actual_pct:.1f}% of cash unexplained"
        }
    
    def get_snapshot_status(self, snapshot_id: int) -> Dict[str, Any]:
        """Get current snapshot status and gate checks."""
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        gate_checks = self._check_lock_gates(snapshot) if snapshot.status != models.SnapshotStatus.LOCKED else snapshot.lock_gate_checks
        
        return {
            "snapshot_id": snapshot_id,
            "status": snapshot.status,
            "is_locked": bool(snapshot.is_locked),
            "lock_type": snapshot.lock_type,
            "lock_gate_checks": gate_checks,
            "can_transition_to_ready": snapshot.status == models.SnapshotStatus.DRAFT,
            "can_transition_to_locked": snapshot.status == models.SnapshotStatus.READY_FOR_REVIEW
        }


