"""
Trust Report Service

Generates CFO-facing "why you should trust this" artifact for every snapshot.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import models
from utils import get_unknown_bucket


class TrustReportService:
    """
    Generates trust report showing data quality and model confidence metrics.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_trust_report(self, snapshot_id: int) -> Dict[str, Any]:
        """
        Generate comprehensive trust report for snapshot.
        
        Returns:
            Dict with all trust metrics (amount-weighted where applicable)
        """
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            return {"error": "Snapshot not found"}
        
        # Get all metrics
        cash_explained = self._calculate_cash_explained(snapshot)
        unknown_exposure = self._calculate_unknown_exposure(snapshot)
        missing_fx_exposure = self._calculate_missing_fx_exposure(snapshot)
        data_freshness = self._calculate_data_freshness(snapshot)
        calibration_coverage = self._calculate_calibration_coverage(snapshot)
        suggested_matches_pending = self._count_suggested_matches_pending(snapshot)
        lock_eligibility = self._check_lock_eligibility(snapshot)
        
        return {
            "snapshot_id": snapshot_id,
            "snapshot_name": snapshot.name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cash_explained": cash_explained,
            "unknown_exposure": unknown_exposure,
            "missing_fx_exposure": missing_fx_exposure,
            "data_freshness": data_freshness,
            "calibration_coverage": calibration_coverage,
            "suggested_matches_pending": suggested_matches_pending,
            "lock_eligibility": lock_eligibility,
            "overall_trust_score": self._calculate_overall_trust_score(
                cash_explained, unknown_exposure, missing_fx_exposure,
                calibration_coverage, suggested_matches_pending
            )
        }
    
    def _calculate_cash_explained(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Calculate cash explained % (amount-weighted)."""
        unknown_bucket = get_unknown_bucket(self.db, snapshot.id)
        unknown_amount = unknown_bucket.get("unknown_amount", 0.0)
        
        # Get total bank movements
        bank_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        
        total_bank_movements = sum(abs(txn.amount or 0.0) for txn in bank_txns)
        
        if total_bank_movements == 0:
            return {
                "explained_pct": 100.0,
                "unknown_pct": 0.0,
                "explained_amount": 0.0,
                "unknown_amount": 0.0,
                "total_movements": 0.0
            }
        
        explained_amount = total_bank_movements - unknown_amount
        explained_pct = (explained_amount / total_bank_movements * 100.0) if total_bank_movements > 0 else 100.0
        unknown_pct = (unknown_amount / total_bank_movements * 100.0) if total_bank_movements > 0 else 0.0
        
        return {
            "explained_pct": explained_pct,
            "unknown_pct": unknown_pct,
            "explained_amount": explained_amount,
            "unknown_amount": unknown_amount,
            "total_movements": total_bank_movements
        }
    
    def _calculate_unknown_exposure(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Calculate unknown exposure € (amount-weighted)."""
        unknown_bucket = get_unknown_bucket(self.db, snapshot.id)
        unknown_amount = unknown_bucket.get("unknown_amount", 0.0)
        unknown_pct = unknown_bucket.get("unknown_pct", 0.0)
        
        return {
            "unknown_amount": unknown_amount,
            "unknown_pct": unknown_pct,
            "kpi_target": snapshot.unknown_bucket_kpi_target,
            "kpi_target_met": unknown_pct <= snapshot.unknown_bucket_kpi_target
        }
    
    def _calculate_missing_fx_exposure(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Calculate missing FX exposure € (amount-weighted)."""
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).all()
        
        if not invoices:
            return {
                "exposure_amount": 0.0,
                "exposure_pct": 0.0,
                "threshold": snapshot.missing_fx_threshold,
                "threshold_met": True
            }
        
        entity = self.db.query(models.Entity).filter(
            models.Entity.id == snapshot.entity_id
        ).first()
        
        entity_currency = entity.currency if entity else "EUR"
        total_invoice_amount = sum(abs(inv.amount or 0.0) for inv in invoices)
        
        missing_fx_exposure = 0.0
        missing_fx_invoices = []
        
        for inv in invoices:
            if inv.currency == entity_currency:
                continue
            
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
        
        exposure_pct = (missing_fx_exposure / total_invoice_amount * 100.0) if total_invoice_amount > 0 else 0.0
        threshold_met = exposure_pct <= snapshot.missing_fx_threshold
        
        return {
            "exposure_amount": missing_fx_exposure,
            "exposure_pct": exposure_pct,
            "threshold": snapshot.missing_fx_threshold,
            "threshold_met": threshold_met,
            "missing_fx_invoice_count": len(missing_fx_invoices),
            "top_missing_fx_invoices": missing_fx_invoices[:5]  # Top 5 for display
        }
    
    def _calculate_data_freshness(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Calculate data freshness mismatch (hours since last update)."""
        # Get most recent invoice date
        latest_invoice = self.db.query(func.max(models.Invoice.invoice_issue_date)).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).scalar()
        
        if not latest_invoice:
            return {
                "freshness_hours": None,
                "freshness_status": "unknown",
                "last_update": None
            }
        
        if isinstance(latest_invoice, str):
            latest_invoice = datetime.fromisoformat(latest_invoice)
        
        now = datetime.now(timezone.utc)
        if latest_invoice.tzinfo is None:
            latest_invoice = latest_invoice.replace(tzinfo=timezone.utc)
        
        freshness_hours = (now - latest_invoice).total_seconds() / 3600.0
        
        if freshness_hours < 24:
            status = "fresh"
        elif freshness_hours < 72:
            status = "stale"
        else:
            status = "very_stale"
        
        return {
            "freshness_hours": freshness_hours,
            "freshness_status": status,
            "last_update": latest_invoice.isoformat()
        }
    
    def _calculate_calibration_coverage(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Calculate calibration coverage (amount-weighted)."""
        try:
            from workflow_models import CalibrationStats
            calibrations = self.db.query(models.CalibrationStats).filter(
                models.CalibrationStats.snapshot_id == snapshot.id
            ).all()
        except:
            calibrations = []
        
        if not calibrations:
            return {
                "amount_weighted_coverage_p25_p75": None,
                "amount_weighted_calibration_error": None,
                "calibrated_segments": 0,
                "status": "not_calibrated"
            }
        
        # Calculate amount-weighted average
        total_coverage = sum(c.amount_weighted_coverage_p25 for c in calibrations if hasattr(c, 'amount_weighted_coverage_p25'))
        total_error = sum(c.amount_weighted_calibration_error for c in calibrations if hasattr(c, 'amount_weighted_calibration_error'))
        
        avg_coverage = total_coverage / len(calibrations) if calibrations else 0.0
        avg_error = total_error / len(calibrations) if calibrations else 0.0
        
        # Check if well-calibrated (coverage within 0.45-0.55)
        well_calibrated = 0.45 <= avg_coverage <= 0.55
        
        return {
            "amount_weighted_coverage_p25_p75": avg_coverage,
            "amount_weighted_calibration_error": avg_error,
            "calibrated_segments": len(calibrations),
            "well_calibrated": well_calibrated,
            "status": "well_calibrated" if well_calibrated else "needs_review"
        }
    
    def _count_suggested_matches_pending(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Count suggested matches pending approval."""
        # Get suggested matches that are pending
        suggested_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            and_(
                models.BankAccount.entity_id == snapshot.entity_id,
                models.BankTransaction.reconciliation_type == "Suggested",
                models.BankTransaction.is_reconciled == 0
            )
        ).all()
        
        total_pending_amount = sum(abs(txn.amount or 0.0) for txn in suggested_txns)
        
        return {
            "pending_count": len(suggested_txns),
            "pending_amount": total_pending_amount,
            "requires_approval": len(suggested_txns) > 0
        }
    
    def _check_lock_eligibility(self, snapshot: models.Snapshot) -> Dict[str, Any]:
        """Check if snapshot is eligible for locking and why/why not."""
        from snapshot_state_machine_enhanced import EnhancedSnapshotStateMachine
        
        state_machine = EnhancedSnapshotStateMachine(self.db)
        status = state_machine.get_snapshot_status(snapshot.id)
        
        gate_checks = status.get("lock_gate_checks", {})
        
        missing_fx_passed = gate_checks.get("missing_fx_rate", {}).get("passed", False)
        unexplained_cash_passed = gate_checks.get("unexplained_cash", {}).get("passed", False)
        
        eligible = missing_fx_passed and unexplained_cash_passed and status.get("can_transition_to_locked", False)
        
        reasons = []
        if not status.get("can_transition_to_locked", False):
            reasons.append("Snapshot must be READY_FOR_REVIEW before locking")
        if not missing_fx_passed:
            reasons.append(f"Missing FX exposure exceeds threshold: {gate_checks.get('missing_fx_rate', {}).get('exposure_pct', 0):.1f}%")
        if not unexplained_cash_passed:
            reasons.append(f"Unexplained cash exceeds threshold: {gate_checks.get('unexplained_cash', {}).get('unexplained_pct', 0):.1f}%")
        
        return {
            "eligible": eligible,
            "reasons": reasons,
            "can_override": True,  # CFO can always override
            "current_status": snapshot.status
        }
    
    def _calculate_overall_trust_score(
        self,
        cash_explained: Dict[str, Any],
        unknown_exposure: Dict[str, Any],
        missing_fx_exposure: Dict[str, Any],
        calibration_coverage: Dict[str, Any],
        suggested_matches_pending: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall trust score (0-100)."""
        score = 100.0
        
        # Deduct for cash explained
        if cash_explained.get("explained_pct", 100.0) < 95.0:
            score -= (100.0 - cash_explained.get("explained_pct", 100.0)) * 0.5
        
        # Deduct for unknown exposure
        if not unknown_exposure.get("kpi_target_met", True):
            score -= 10.0
        
        # Deduct for missing FX
        if not missing_fx_exposure.get("threshold_met", True):
            score -= 10.0
        
        # Deduct for poor calibration
        if calibration_coverage.get("status") == "needs_review":
            score -= 5.0
        
        # Deduct for pending suggestions
        if suggested_matches_pending.get("pending_count", 0) > 10:
            score -= 5.0
        
        score = max(0.0, min(100.0, score))
        
        if score >= 90:
            level = "high"
        elif score >= 75:
            level = "medium"
        else:
            level = "low"
        
        return {
            "score": score,
            "level": level,
            "interpretation": f"Trust score: {score:.1f}/100 ({level} confidence)"
        }


