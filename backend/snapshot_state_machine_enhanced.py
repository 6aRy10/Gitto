"""
Enhanced Snapshot State Machine

Fixes:
1. Amount-weighted gates (€ exposure, not row counts)
2. CFO override with explicit acknowledgment
3. Acknowledged exceptions state
"""

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
import models
from sqlalchemy import func, and_


class EnhancedSnapshotStateMachine:
    """Enhanced state machine with amount-weighted gates and CFO override."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def lock_snapshot(
        self,
        snapshot_id: int,
        user_id: str,
        lock_type: str = "Meeting",
        force: bool = False,
        cfo_override: bool = False,
        override_acknowledgment: str = None
    ) -> Dict[str, Any]:
        """
        Lock snapshot with amount-weighted gates and CFO override.
        
        Args:
            cfo_override: If True, CFO explicitly overrides gates
            override_acknowledgment: Required text acknowledgment if overriding
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
        
        # Check lock gates (amount-weighted)
        gate_checks = self._check_lock_gates_amount_weighted(snapshot)
        
        # Validate gates pass (unless forced or CFO override)
        if not force and not cfo_override:
            gate_errors = []
            
            if not gate_checks["missing_fx_rate"]["passed"]:
                gate_errors.append(
                    f"Missing FX rate exposure: €{gate_checks['missing_fx_rate']['exposure_amount']:,.0f} "
                    f"({gate_checks['missing_fx_rate']['exposure_pct']:.1f}% of forecasted cash) "
                    f"exceeds threshold: {snapshot.missing_fx_threshold}%"
                )
            
            if not gate_checks["unexplained_cash"]["passed"]:
                gate_errors.append(
                    f"Unexplained cash: €{gate_checks['unexplained_cash']['unexplained_amount']:,.0f} "
                    f"({gate_checks['unexplained_cash']['unexplained_pct']:.1f}% of bank movements) "
                    f"exceeds threshold: {snapshot.unexplained_cash_threshold}%"
                )
            
            if gate_errors:
                raise HTTPException(
                    status_code=400,
                    detail="Lock gates failed:\n" + "\n".join(gate_errors) + 
                    "\n\nUse cfo_override=true with override_acknowledgment to proceed."
                )
        
        # CFO override validation
        if cfo_override:
            if not override_acknowledgment or len(override_acknowledgment.strip()) < 20:
                raise HTTPException(
                    status_code=400,
                    detail="CFO override requires acknowledgment text (minimum 20 characters)"
                )
        
        # Transition to LOCKED
        snapshot.status = models.SnapshotStatus.LOCKED
        snapshot.is_locked = 1
        snapshot.lock_type = lock_type
        snapshot.locked_at = datetime.now(timezone.utc)
        snapshot.locked_by = user_id
        
        # Store gate checks and override info
        gate_checks['cfo_override'] = cfo_override
        gate_checks['override_acknowledgment'] = override_acknowledgment if cfo_override else None
        snapshot.lock_gate_checks = gate_checks
        
        self.db.commit()
        
        return {
            "snapshot_id": snapshot_id,
            "status": snapshot.status,
            "is_locked": True,
            "lock_type": lock_type,
            "locked_at": snapshot.locked_at.isoformat(),
            "locked_by": snapshot.locked_by,
            "lock_gate_checks": gate_checks,
            "cfo_override": cfo_override
        }
    
    def _check_lock_gates_amount_weighted(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """
        Check lock gates using amount-weighted metrics (€ exposure, not row counts).
        """
        checks = {
            "missing_fx_rate": self._check_missing_fx_rate_amount_weighted(snapshot),
            "unexplained_cash": self._check_unexplained_cash_amount_weighted(snapshot)
        }
        
        return checks
    
    def _check_missing_fx_rate_amount_weighted(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """
        Check missing FX rate gate using amount-weighted exposure.
        
        CFOs care about € exposure, not row counts.
        2 invoices missing FX could be 80% of cash impact.
        """
        # Get all invoices
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).all()
        
        if not invoices:
            return {
                "passed": True,
                "exposure_pct": 0.0,
                "exposure_amount": 0.0,
                "threshold": snapshot.missing_fx_threshold,
                "message": "No invoices to check"
            }
        
        entity = self.db.query(models.Entity).filter(
            models.Entity.id == snapshot.entity_id
        ).first()
        
        entity_currency = entity.currency if entity else "EUR"
        
        # Calculate total forecasted cash (sum of all invoice amounts)
        total_forecasted_cash = sum(inv.amount or 0.0 for inv in invoices)
        
        if total_forecasted_cash == 0:
            return {
                "passed": True,
                "exposure_pct": 0.0,
                "exposure_amount": 0.0,
                "threshold": snapshot.missing_fx_threshold,
                "message": "No forecasted cash to check"
            }
        
        # Get invoices with missing FX rates (amount-weighted)
        missing_fx_exposure = 0.0
        missing_fx_invoices = []
        
        for inv in invoices:
            if inv.currency == entity_currency:
                continue  # Same currency, no FX needed
            
            # Check if FX rate exists
            fx_rate = self.db.query(models.WeeklyFXRate).filter(
                and_(
                    models.WeeklyFXRate.snapshot_id == snapshot.id,
                    models.WeeklyFXRate.invoice_id == inv.id
                )
            ).first()
            
            if not fx_rate:
                missing_fx_exposure += abs(inv.amount or 0.0)
                missing_fx_invoices.append({
                    "invoice_id": inv.id,
                    "document_number": inv.document_number,
                    "amount": inv.amount,
                    "currency": inv.currency
                })
        
        exposure_pct = (missing_fx_exposure / total_forecasted_cash * 100.0) if total_forecasted_cash > 0 else 0.0
        passed = exposure_pct <= snapshot.missing_fx_threshold
        
        return {
            "passed": passed,
            "exposure_pct": exposure_pct,
            "exposure_amount": missing_fx_exposure,
            "threshold": snapshot.missing_fx_threshold,
            "total_forecasted_cash": total_forecasted_cash,
            "missing_fx_invoice_count": len(missing_fx_invoices),
            "missing_fx_invoices": missing_fx_invoices[:10],  # Top 10 for display
            "message": f"€{missing_fx_exposure:,.0f} ({exposure_pct:.1f}% of forecasted cash) missing FX rates"
        }
    
    def _check_unexplained_cash_amount_weighted(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """
        Check unexplained cash gate using amount-weighted bank movements.
        
        Unexplained bank movements < X% of bank movement value for the period.
        """
        from utils import get_unknown_bucket
        
        unknown_bucket = get_unknown_bucket(self.db, snapshot.id)
        unknown_amount = unknown_bucket.get("unknown_amount", 0.0)
        
        # Get total bank movements for the period
        # Sum of all bank transaction amounts (absolute values)
        bank_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        
        total_bank_movements = sum(abs(txn.amount or 0.0) for txn in bank_txns)
        
        if total_bank_movements == 0:
            return {
                "passed": True,
                "unexplained_pct": 0.0,
                "unexplained_amount": unknown_amount,
                "threshold": snapshot.unexplained_cash_threshold,
                "message": "No bank movements to check"
            }
        
        unexplained_pct = (unknown_amount / total_bank_movements * 100.0) if total_bank_movements > 0 else 0.0
        passed = unexplained_pct <= snapshot.unexplained_cash_threshold
        
        return {
            "passed": passed,
            "unexplained_pct": unexplained_pct,
            "unexplained_amount": unknown_amount,
            "total_bank_movements": total_bank_movements,
            "threshold": snapshot.unexplained_cash_threshold,
            "message": f"€{unknown_amount:,.0f} ({unexplained_pct:.1f}% of bank movements) unexplained"
        }
    
    def acknowledge_exceptions(
        self,
        snapshot_id: int,
        exception_ids: List[int],
        acknowledgment_note: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Acknowledge exceptions (mark as reviewed but unresolved).
        
        Allows locking snapshot with acknowledged exceptions.
        """
        try:
            from workflow_models import WorkflowException
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="Workflow models not available"
            )
        
        exceptions = self.db.query(WorkflowException).filter(
            and_(
                WorkflowException.snapshot_id == snapshot_id,
                WorkflowException.id.in_(exception_ids)
            )
        ).all()
        
        if len(exceptions) != len(exception_ids):
            raise HTTPException(
                status_code=404,
                detail="Some exceptions not found"
            )
        
        acknowledged = []
        for exc in exceptions:
            exc.status = "acknowledged"  # New status
            exc.resolution_note = f"ACKNOWLEDGED: {acknowledgment_note}"
            exc.resolved_by = user_id
            exc.resolved_at = datetime.now(timezone.utc)
            acknowledged.append(exc.id)
        
        self.db.commit()
        
        return {
            "acknowledged_count": len(acknowledged),
            "exception_ids": acknowledged,
            "acknowledgment_note": acknowledgment_note
        }


