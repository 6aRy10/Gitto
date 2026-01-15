"""
Gitto Trust Certification (Treasury DataOps)

A reliability layer that sits above bank/ERP/warehouse ingestion and produces
a "Trust Report" for every Snapshot.

This module computes:
1. Amount-weighted trust metrics
2. Invariant checks (deterministic correctness)
3. Lock gates with CFO override
4. Evidence links for every metric and failure
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import hashlib
import json
import models


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class MetricStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


class InvariantSeverity(str, Enum):
    CRITICAL = "critical"  # Blocks lock, no override
    ERROR = "error"        # Blocks lock, CFO can override
    WARNING = "warning"    # Warns, doesn't block


@dataclass
class EvidenceRef:
    """Reference to specific data for audit trail."""
    ref_type: str  # "invoice", "bank_txn", "reconciliation", "fx_rate", "dataset"
    ref_id: int
    ref_key: Optional[str] = None  # Human-readable key (e.g., document_number)
    amount: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class TrustMetric:
    """Amount-weighted trust metric with evidence."""
    name: str
    value: float
    unit: str  # "percent", "currency", "hours", "count"
    status: MetricStatus
    threshold: Optional[float] = None
    threshold_type: Optional[str] = None  # "max", "min"
    amount_weighted: bool = True
    evidence: List[EvidenceRef] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "status": self.status.value,
            "threshold": self.threshold,
            "threshold_type": self.threshold_type,
            "amount_weighted": self.amount_weighted,
            "evidence_count": len(self.evidence),
            "evidence": [e.to_dict() for e in self.evidence[:10]],  # Top 10 for display
            "details": self.details
        }


@dataclass
class InvariantCheck:
    """Deterministic correctness check with evidence."""
    name: str
    passed: bool
    severity: InvariantSeverity
    message: str
    evidence: List[EvidenceRef] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity.value,
            "message": self.message,
            "evidence_count": len(self.evidence),
            "evidence": [e.to_dict() for e in self.evidence[:10]],
            "details": self.details
        }


@dataclass
class LockGate:
    """Gate that must pass (or be overridden) before snapshot lock."""
    name: str
    passed: bool
    can_override: bool
    requires_acknowledgment: bool
    metric: Optional[TrustMetric] = None
    invariant: Optional[InvariantCheck] = None
    acknowledgment_text_required: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "can_override": self.can_override,
            "requires_acknowledgment": self.requires_acknowledgment,
            "metric": self.metric.to_dict() if self.metric else None,
            "invariant": self.invariant.to_dict() if self.invariant else None,
            "acknowledgment_text_required": self.acknowledgment_text_required
        }


@dataclass
class TrustReport:
    """Complete trust report for a snapshot."""
    snapshot_id: int
    snapshot_name: str
    dataset_id: Optional[str]
    generated_at: datetime
    metrics: List[TrustMetric]
    invariants: List[InvariantCheck]
    lock_gates: List[LockGate]
    overall_trust_score: float
    lock_eligible: bool
    lock_blocked_reasons: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_name": self.snapshot_name,
            "dataset_id": self.dataset_id,
            "generated_at": self.generated_at.isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "invariants": [i.to_dict() for i in self.invariants],
            "lock_gates": [g.to_dict() for g in self.lock_gates],
            "overall_trust_score": self.overall_trust_score,
            "lock_eligible": self.lock_eligible,
            "lock_blocked_reasons": self.lock_blocked_reasons
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST CERTIFICATION SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class TrustCertificationService:
    """
    Main service for Gitto Trust Certification.
    
    Computes amount-weighted metrics, runs invariant checks,
    evaluates lock gates, and generates Trust Reports.
    """
    
    # Default thresholds (can be overridden per entity)
    DEFAULT_THRESHOLDS = {
        "cash_explained_min_pct": 95.0,
        "unknown_exposure_max_pct": 5.0,
        "missing_fx_exposure_max_pct": 5.0,
        "data_freshness_max_hours": 72.0,
        "reconciliation_integrity_min_pct": 98.0,
        "calibration_coverage_min_pct": 45.0,
        "calibration_coverage_max_pct": 55.0,
    }
    
    def __init__(self, db: Session, thresholds: Optional[Dict[str, float]] = None):
        self.db = db
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
    
    def generate_trust_report(self, snapshot_id: int) -> TrustReport:
        """Generate complete trust report for snapshot."""
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        # Compute all metrics
        metrics = [
            self._compute_cash_explained(snapshot),
            self._compute_unknown_exposure(snapshot),
            self._compute_missing_fx_exposure(snapshot),
            self._compute_data_freshness(snapshot),
            self._compute_reconciliation_integrity(snapshot),
            self._compute_forecast_calibration_coverage(snapshot),
        ]
        
        # Run all invariant checks
        invariants = [
            self._check_cash_math(snapshot),
            self._check_drilldown_sums(snapshot),
            self._check_reconciliation_conservation(snapshot),
            self._check_snapshot_immutability(snapshot),
            self._check_idempotency(snapshot),
            self._check_no_silent_fx(snapshot),
        ]
        
        # Build lock gates
        lock_gates = self._build_lock_gates(metrics, invariants)
        
        # Calculate overall trust score
        overall_score = self._calculate_trust_score(metrics, invariants)
        
        # Determine lock eligibility
        lock_eligible, blocked_reasons = self._evaluate_lock_eligibility(lock_gates)
        
        return TrustReport(
            snapshot_id=snapshot_id,
            snapshot_name=snapshot.name or f"Snapshot #{snapshot_id}",
            dataset_id=snapshot.dataset_id,
            generated_at=datetime.now(timezone.utc),
            metrics=metrics,
            invariants=invariants,
            lock_gates=lock_gates,
            overall_trust_score=overall_score,
            lock_eligible=lock_eligible,
            lock_blocked_reasons=blocked_reasons
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TRUST METRICS (Amount-Weighted)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _compute_cash_explained(self, snapshot: models.Snapshot) -> TrustMetric:
        """
        Cash Explained % (amount-weighted)
        = (Total Bank Movements - Unknown Amount) / Total Bank Movements
        """
        # Get bank transactions for this entity
        bank_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        
        total_movements = sum(abs(txn.amount or 0.0) for txn in bank_txns)
        
        # Get reconciled amount
        reconciled_txns = [t for t in bank_txns if t.is_reconciled == 1]
        reconciled_amount = sum(abs(txn.amount or 0.0) for txn in reconciled_txns)
        
        # Unknown = Total - Reconciled
        unknown_amount = total_movements - reconciled_amount
        
        if total_movements == 0:
            explained_pct = 100.0
        else:
            explained_pct = (reconciled_amount / total_movements) * 100.0
        
        threshold = self.thresholds["cash_explained_min_pct"]
        status = MetricStatus.PASS if explained_pct >= threshold else MetricStatus.FAIL
        
        # Collect evidence for unreconciled transactions
        unreconciled_txns = [t for t in bank_txns if t.is_reconciled == 0]
        evidence = [
            EvidenceRef(
                ref_type="bank_txn",
                ref_id=txn.id,
                ref_key=txn.reference,
                amount=txn.amount,
                currency=txn.currency,
                description=f"Unreconciled: {txn.counterparty}"
            )
            for txn in sorted(unreconciled_txns, key=lambda x: abs(x.amount or 0), reverse=True)[:50]
        ]
        
        return TrustMetric(
            name="Cash Explained %",
            value=explained_pct,
            unit="percent",
            status=status,
            threshold=threshold,
            threshold_type="min",
            amount_weighted=True,
            evidence=evidence,
            details={
                "total_movements": total_movements,
                "reconciled_amount": reconciled_amount,
                "unknown_amount": unknown_amount,
                "total_txn_count": len(bank_txns),
                "reconciled_txn_count": len(reconciled_txns),
                "unreconciled_txn_count": len(unreconciled_txns)
            }
        )
    
    def _compute_unknown_exposure(self, snapshot: models.Snapshot) -> TrustMetric:
        """
        Unknown Exposure € (amount-weighted)
        = Sum of unreconciled bank transaction amounts
        """
        bank_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            and_(
                models.BankAccount.entity_id == snapshot.entity_id,
                models.BankTransaction.is_reconciled == 0
            )
        ).all()
        
        unknown_amount = sum(abs(txn.amount or 0.0) for txn in bank_txns)
        
        # Get total for percentage
        all_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        total_amount = sum(abs(txn.amount or 0.0) for txn in all_txns)
        
        unknown_pct = (unknown_amount / total_amount * 100.0) if total_amount > 0 else 0.0
        threshold = self.thresholds["unknown_exposure_max_pct"]
        status = MetricStatus.PASS if unknown_pct <= threshold else MetricStatus.FAIL
        
        evidence = [
            EvidenceRef(
                ref_type="bank_txn",
                ref_id=txn.id,
                ref_key=txn.reference,
                amount=txn.amount,
                currency=txn.currency,
                description=f"Unknown: {txn.counterparty}"
            )
            for txn in sorted(bank_txns, key=lambda x: abs(x.amount or 0), reverse=True)[:50]
        ]
        
        return TrustMetric(
            name="Unknown Exposure €",
            value=unknown_amount,
            unit="currency",
            status=status,
            threshold=threshold,
            threshold_type="max",
            amount_weighted=True,
            evidence=evidence,
            details={
                "unknown_pct": unknown_pct,
                "total_amount": total_amount,
                "unknown_txn_count": len(bank_txns)
            }
        )
    
    def _compute_missing_fx_exposure(self, snapshot: models.Snapshot) -> TrustMetric:
        """
        Missing FX Exposure € (amount-weighted)
        = Sum of invoice amounts with foreign currency but no FX rate
        """
        entity = self.db.query(models.Entity).filter(
            models.Entity.id == snapshot.entity_id
        ).first()
        base_currency = entity.currency if entity else "EUR"
        
        # Get all foreign currency invoices
        foreign_invoices = self.db.query(models.Invoice).filter(
            and_(
                models.Invoice.snapshot_id == snapshot.id,
                models.Invoice.currency != base_currency,
                models.Invoice.currency.isnot(None)
            )
        ).all()
        
        # Get available FX rates
        fx_rates = self.db.query(models.WeeklyFXRate).filter(
            models.WeeklyFXRate.snapshot_id == snapshot.id
        ).all()
        
        available_currencies = {
            (r.from_currency, r.to_currency) for r in fx_rates
        }
        
        missing_fx_invoices = []
        missing_fx_amount = 0.0
        
        for inv in foreign_invoices:
            # Check if we have a rate for this currency
            has_rate = (
                (inv.currency, base_currency) in available_currencies or
                (base_currency, inv.currency) in available_currencies
            )
            if not has_rate:
                missing_fx_invoices.append(inv)
                missing_fx_amount += abs(inv.amount or 0.0)
        
        # Get total invoice amount for percentage
        total_invoice_amount = self.db.query(func.sum(func.abs(models.Invoice.amount))).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).scalar() or 0.0
        
        exposure_pct = (missing_fx_amount / total_invoice_amount * 100.0) if total_invoice_amount > 0 else 0.0
        threshold = self.thresholds["missing_fx_exposure_max_pct"]
        status = MetricStatus.PASS if exposure_pct <= threshold else MetricStatus.FAIL
        
        evidence = [
            EvidenceRef(
                ref_type="invoice",
                ref_id=inv.id,
                ref_key=inv.document_number,
                amount=inv.amount,
                currency=inv.currency,
                description=f"Missing FX rate: {inv.currency} → {base_currency}"
            )
            for inv in sorted(missing_fx_invoices, key=lambda x: abs(x.amount or 0), reverse=True)[:50]
        ]
        
        return TrustMetric(
            name="Missing FX Exposure €",
            value=missing_fx_amount,
            unit="currency",
            status=status,
            threshold=threshold,
            threshold_type="max",
            amount_weighted=True,
            evidence=evidence,
            details={
                "exposure_pct": exposure_pct,
                "total_invoice_amount": total_invoice_amount,
                "missing_fx_invoice_count": len(missing_fx_invoices),
                "base_currency": base_currency,
                "foreign_currencies_found": list({inv.currency for inv in foreign_invoices}),
                "available_fx_pairs": list(available_currencies)[:20]
            }
        )
    
    def _compute_data_freshness(self, snapshot: models.Snapshot) -> TrustMetric:
        """
        Data Freshness Mismatch (hours)
        = Max of (now - bank_as_of, now - erp_as_of, now - latest_invoice)
        """
        now = datetime.now(timezone.utc)
        
        # Check snapshot created_at as baseline
        snapshot_age_hours = 0.0
        if snapshot.created_at:
            created_at = snapshot.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            snapshot_age_hours = (now - created_at).total_seconds() / 3600.0
        
        # Check latest invoice date
        latest_invoice_date = self.db.query(func.max(models.Invoice.document_date)).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).scalar()
        
        invoice_lag_hours = 0.0
        if latest_invoice_date:
            if isinstance(latest_invoice_date, str):
                latest_invoice_date = datetime.fromisoformat(latest_invoice_date)
            if latest_invoice_date.tzinfo is None:
                latest_invoice_date = latest_invoice_date.replace(tzinfo=timezone.utc)
            invoice_lag_hours = (now - latest_invoice_date).total_seconds() / 3600.0
        
        # Check latest bank transaction
        latest_bank_date = self.db.query(func.max(models.BankTransaction.transaction_date)).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).scalar()
        
        bank_lag_hours = 0.0
        if latest_bank_date:
            if isinstance(latest_bank_date, str):
                latest_bank_date = datetime.fromisoformat(latest_bank_date)
            if latest_bank_date.tzinfo is None:
                latest_bank_date = latest_bank_date.replace(tzinfo=timezone.utc)
            bank_lag_hours = (now - latest_bank_date).total_seconds() / 3600.0
        
        # Use maximum lag
        max_lag_hours = max(snapshot_age_hours, invoice_lag_hours, bank_lag_hours)
        
        threshold = self.thresholds["data_freshness_max_hours"]
        status = MetricStatus.PASS if max_lag_hours <= threshold else (
            MetricStatus.WARN if max_lag_hours <= threshold * 2 else MetricStatus.FAIL
        )
        
        return TrustMetric(
            name="Data Freshness Mismatch",
            value=max_lag_hours,
            unit="hours",
            status=status,
            threshold=threshold,
            threshold_type="max",
            amount_weighted=False,
            evidence=[],
            details={
                "snapshot_age_hours": snapshot_age_hours,
                "invoice_lag_hours": invoice_lag_hours,
                "bank_lag_hours": bank_lag_hours,
                "latest_invoice_date": latest_invoice_date.isoformat() if latest_invoice_date else None,
                "latest_bank_date": latest_bank_date.isoformat() if latest_bank_date else None
            }
        )
    
    def _compute_reconciliation_integrity(self, snapshot: models.Snapshot) -> TrustMetric:
        """
        Reconciliation Integrity % (amount-weighted)
        = Sum of valid reconciliation allocations / Total allocated
        
        Valid = allocations that don't exceed invoice open_amount
        """
        # Get all reconciliation records
        recon_records = self.db.query(models.ReconciliationTable).all()
        
        if not recon_records:
            return TrustMetric(
                name="Reconciliation Integrity %",
                value=100.0,
                unit="percent",
                status=MetricStatus.PASS,
                threshold=self.thresholds["reconciliation_integrity_min_pct"],
                threshold_type="min",
                amount_weighted=True,
                evidence=[],
                details={"reconciliation_count": 0}
            )
        
        total_allocated = 0.0
        valid_allocated = 0.0
        invalid_records = []
        
        # Group allocations by invoice
        invoice_allocations: Dict[int, float] = {}
        for rec in recon_records:
            if rec.invoice_id:
                invoice_allocations[rec.invoice_id] = invoice_allocations.get(rec.invoice_id, 0.0) + (rec.amount_allocated or 0.0)
        
        # Check each invoice's total allocation vs open amount
        for invoice_id, total_alloc in invoice_allocations.items():
            invoice = self.db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
            if invoice:
                invoice_amount = abs(invoice.amount or 0.0)
                total_allocated += total_alloc
                
                if total_alloc <= invoice_amount * 1.001:  # 0.1% tolerance for rounding
                    valid_allocated += total_alloc
                else:
                    invalid_records.append({
                        "invoice_id": invoice_id,
                        "invoice_amount": invoice_amount,
                        "total_allocated": total_alloc,
                        "over_allocation": total_alloc - invoice_amount
                    })
        
        integrity_pct = (valid_allocated / total_allocated * 100.0) if total_allocated > 0 else 100.0
        threshold = self.thresholds["reconciliation_integrity_min_pct"]
        status = MetricStatus.PASS if integrity_pct >= threshold else MetricStatus.FAIL
        
        evidence = [
            EvidenceRef(
                ref_type="reconciliation",
                ref_id=rec["invoice_id"],
                ref_key=f"Invoice #{rec['invoice_id']}",
                amount=rec["over_allocation"],
                description=f"Over-allocated by {rec['over_allocation']:.2f}"
            )
            for rec in invalid_records[:50]
        ]
        
        return TrustMetric(
            name="Reconciliation Integrity %",
            value=integrity_pct,
            unit="percent",
            status=status,
            threshold=threshold,
            threshold_type="min",
            amount_weighted=True,
            evidence=evidence,
            details={
                "total_allocated": total_allocated,
                "valid_allocated": valid_allocated,
                "invalid_record_count": len(invalid_records),
                "reconciliation_count": len(recon_records)
            }
        )
    
    def _compute_forecast_calibration_coverage(self, snapshot: models.Snapshot) -> TrustMetric:
        """
        Forecast Calibration Coverage % (amount-weighted)
        = Percentage of invoice amounts covered by calibrated forecasts
        """
        calibration_stats = self.db.query(models.CalibrationStats).filter(
            models.CalibrationStats.snapshot_id == snapshot.id
        ).all()
        
        if not calibration_stats:
            return TrustMetric(
                name="Forecast Calibration Coverage",
                value=0.0,
                unit="percent",
                status=MetricStatus.SKIP,
                threshold=self.thresholds["calibration_coverage_min_pct"],
                threshold_type="min",
                amount_weighted=True,
                evidence=[],
                details={"calibrated_segments": 0, "status": "not_calibrated"}
            )
        
        # Calculate average coverage across segments
        avg_coverage_p50 = sum(s.coverage_p50 or 0.0 for s in calibration_stats) / len(calibration_stats)
        avg_error = sum(s.calibration_error or 0.0 for s in calibration_stats) / len(calibration_stats)
        total_samples = sum(s.sample_size or 0 for s in calibration_stats)
        
        # Check if coverage is in expected range (45-55% for P50)
        min_threshold = self.thresholds["calibration_coverage_min_pct"]
        max_threshold = self.thresholds["calibration_coverage_max_pct"]
        
        is_well_calibrated = min_threshold <= avg_coverage_p50 * 100 <= max_threshold
        status = MetricStatus.PASS if is_well_calibrated else MetricStatus.WARN
        
        return TrustMetric(
            name="Forecast Calibration Coverage",
            value=avg_coverage_p50 * 100,
            unit="percent",
            status=status,
            threshold=min_threshold,
            threshold_type="min",
            amount_weighted=True,
            evidence=[],
            details={
                "calibrated_segments": len(calibration_stats),
                "average_calibration_error": avg_error,
                "total_sample_size": total_samples,
                "expected_range": f"{min_threshold}%-{max_threshold}%",
                "is_well_calibrated": is_well_calibrated
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INVARIANT CHECKS (Deterministic Correctness)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_cash_math(self, snapshot: models.Snapshot) -> InvariantCheck:
        """
        Cash Math Invariant:
        Sum of individual cash components = Total cash position
        """
        # Get opening balance
        opening_balance = snapshot.opening_bank_balance or 0.0
        
        # Get all bank transactions
        bank_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        
        total_inflows = sum(txn.amount for txn in bank_txns if (txn.amount or 0) > 0)
        total_outflows = sum(txn.amount for txn in bank_txns if (txn.amount or 0) < 0)
        
        # Get bank account balances
        bank_accounts = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        reported_balance = sum(acc.balance or 0.0 for acc in bank_accounts)
        
        # Calculate expected balance
        calculated_balance = opening_balance + total_inflows + total_outflows
        
        # Check if they match (within rounding tolerance)
        tolerance = 0.01  # 1 cent
        difference = abs(calculated_balance - reported_balance)
        passed = difference <= tolerance or reported_balance == 0.0  # Skip if no balance reported
        
        evidence = []
        if not passed:
            evidence.append(EvidenceRef(
                ref_type="calculation",
                ref_id=snapshot.id,
                description=f"Opening {opening_balance} + Inflows {total_inflows} + Outflows {total_outflows} = {calculated_balance}, but reported {reported_balance}"
            ))
        
        return InvariantCheck(
            name="Cash Math",
            passed=passed,
            severity=InvariantSeverity.CRITICAL,
            message="Calculated balance matches reported balance" if passed else f"Balance mismatch: {difference:.2f}",
            evidence=evidence,
            details={
                "opening_balance": opening_balance,
                "total_inflows": total_inflows,
                "total_outflows": total_outflows,
                "calculated_balance": calculated_balance,
                "reported_balance": reported_balance,
                "difference": difference
            }
        )
    
    def _check_drilldown_sums(self, snapshot: models.Snapshot) -> InvariantCheck:
        """
        Drilldown Sums Invariant:
        Sum of detail rows = Summary total for each category
        """
        # Check invoice totals by customer
        invoice_total = self.db.query(func.sum(models.Invoice.amount)).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).scalar() or 0.0
        
        customer_totals = self.db.query(
            models.Invoice.customer,
            func.sum(models.Invoice.amount).label('total')
        ).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).group_by(models.Invoice.customer).all()
        
        sum_of_customer_totals = sum(ct.total or 0.0 for ct in customer_totals)
        
        # Check country totals
        country_totals = self.db.query(
            models.Invoice.country,
            func.sum(models.Invoice.amount).label('total')
        ).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).group_by(models.Invoice.country).all()
        
        sum_of_country_totals = sum(ct.total or 0.0 for ct in country_totals)
        
        tolerance = 0.01
        customer_match = abs(invoice_total - sum_of_customer_totals) <= tolerance
        country_match = abs(invoice_total - sum_of_country_totals) <= tolerance
        
        passed = customer_match and country_match
        
        evidence = []
        if not customer_match:
            evidence.append(EvidenceRef(
                ref_type="drilldown",
                ref_id=snapshot.id,
                description=f"Customer drilldown mismatch: {invoice_total} vs {sum_of_customer_totals}"
            ))
        if not country_match:
            evidence.append(EvidenceRef(
                ref_type="drilldown",
                ref_id=snapshot.id,
                description=f"Country drilldown mismatch: {invoice_total} vs {sum_of_country_totals}"
            ))
        
        return InvariantCheck(
            name="Drilldown Sums",
            passed=passed,
            severity=InvariantSeverity.ERROR,
            message="All drilldowns sum correctly" if passed else "Drilldown sum mismatches found",
            evidence=evidence,
            details={
                "invoice_total": invoice_total,
                "sum_of_customer_totals": sum_of_customer_totals,
                "sum_of_country_totals": sum_of_country_totals,
                "customer_count": len(customer_totals),
                "country_count": len(country_totals)
            }
        )
    
    def _check_reconciliation_conservation(self, snapshot: models.Snapshot) -> InvariantCheck:
        """
        Reconciliation Conservation Invariant:
        - Allocations per transaction sum to transaction amount
        - Allocations to invoice do not exceed open amount
        """
        recon_records = self.db.query(models.ReconciliationTable).all()
        
        if not recon_records:
            return InvariantCheck(
                name="Reconciliation Conservation",
                passed=True,
                severity=InvariantSeverity.CRITICAL,
                message="No reconciliation records to check",
                evidence=[],
                details={"reconciliation_count": 0}
            )
        
        violations = []
        
        # Check: allocations per transaction sum to transaction amount
        txn_allocations: Dict[int, float] = {}
        for rec in recon_records:
            if rec.bank_transaction_id:
                txn_allocations[rec.bank_transaction_id] = txn_allocations.get(rec.bank_transaction_id, 0.0) + (rec.amount_allocated or 0.0)
        
        for txn_id, total_alloc in txn_allocations.items():
            txn = self.db.query(models.BankTransaction).filter(models.BankTransaction.id == txn_id).first()
            if txn:
                txn_amount = abs(txn.amount or 0.0)
                if abs(total_alloc - txn_amount) > 0.01:  # 1 cent tolerance
                    violations.append({
                        "type": "txn_sum_mismatch",
                        "txn_id": txn_id,
                        "txn_amount": txn_amount,
                        "total_allocated": total_alloc
                    })
        
        # Check: allocations to invoice don't exceed open amount
        invoice_allocations: Dict[int, float] = {}
        for rec in recon_records:
            if rec.invoice_id:
                invoice_allocations[rec.invoice_id] = invoice_allocations.get(rec.invoice_id, 0.0) + (rec.amount_allocated or 0.0)
        
        for inv_id, total_alloc in invoice_allocations.items():
            inv = self.db.query(models.Invoice).filter(models.Invoice.id == inv_id).first()
            if inv:
                inv_amount = abs(inv.amount or 0.0)
                if total_alloc > inv_amount * 1.001:  # 0.1% tolerance
                    violations.append({
                        "type": "invoice_over_allocation",
                        "invoice_id": inv_id,
                        "invoice_amount": inv_amount,
                        "total_allocated": total_alloc,
                        "over_amount": total_alloc - inv_amount
                    })
        
        passed = len(violations) == 0
        
        evidence = [
            EvidenceRef(
                ref_type="reconciliation",
                ref_id=v.get("txn_id") or v.get("invoice_id"),
                description=f"{v['type']}: expected {v.get('txn_amount') or v.get('invoice_amount')}, got {v['total_allocated']}"
            )
            for v in violations[:50]
        ]
        
        return InvariantCheck(
            name="Reconciliation Conservation",
            passed=passed,
            severity=InvariantSeverity.CRITICAL,
            message="All reconciliation allocations are valid" if passed else f"{len(violations)} conservation violations found",
            evidence=evidence,
            details={
                "violation_count": len(violations),
                "violations": violations[:10]
            }
        )
    
    def _check_snapshot_immutability(self, snapshot: models.Snapshot) -> InvariantCheck:
        """
        Snapshot Immutability Invariant:
        Locked snapshots cannot have child records modified
        """
        if snapshot.status != models.SnapshotStatus.LOCKED and snapshot.is_locked != 1:
            return InvariantCheck(
                name="Snapshot Immutability",
                passed=True,
                severity=InvariantSeverity.CRITICAL,
                message="Snapshot is not locked - immutability check not applicable",
                evidence=[],
                details={"is_locked": False, "status": snapshot.status}
            )
        
        # For locked snapshots, we verify the lock_gate_checks are present
        # and that the locked_at timestamp is set
        passed = (
            snapshot.locked_at is not None and
            snapshot.locked_by is not None
        )
        
        evidence = []
        if not passed:
            if not snapshot.locked_at:
                evidence.append(EvidenceRef(
                    ref_type="snapshot",
                    ref_id=snapshot.id,
                    description="Locked snapshot missing locked_at timestamp"
                ))
            if not snapshot.locked_by:
                evidence.append(EvidenceRef(
                    ref_type="snapshot",
                    ref_id=snapshot.id,
                    description="Locked snapshot missing locked_by user"
                ))
        
        return InvariantCheck(
            name="Snapshot Immutability",
            passed=passed,
            severity=InvariantSeverity.CRITICAL,
            message="Locked snapshot has proper audit trail" if passed else "Locked snapshot missing audit metadata",
            evidence=evidence,
            details={
                "is_locked": True,
                "locked_at": snapshot.locked_at.isoformat() if snapshot.locked_at else None,
                "locked_by": snapshot.locked_by
            }
        )
    
    def _check_idempotency(self, snapshot: models.Snapshot) -> InvariantCheck:
        """
        Idempotency Invariant:
        Re-importing same data produces same canonical IDs
        """
        # Check for duplicate canonical_ids (which would indicate idempotency failure)
        duplicate_ids = self.db.query(
            models.Invoice.canonical_id,
            func.count(models.Invoice.id).label('count')
        ).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).group_by(models.Invoice.canonical_id).having(
            func.count(models.Invoice.id) > 1
        ).all()
        
        passed = len(duplicate_ids) == 0
        
        evidence = [
            EvidenceRef(
                ref_type="invoice",
                ref_id=0,
                ref_key=dup.canonical_id,
                description=f"Duplicate canonical_id found {dup.count} times"
            )
            for dup in duplicate_ids[:50]
        ]
        
        return InvariantCheck(
            name="Idempotency",
            passed=passed,
            severity=InvariantSeverity.ERROR,
            message="No duplicate canonical IDs found" if passed else f"{len(duplicate_ids)} duplicate canonical IDs found",
            evidence=evidence,
            details={
                "duplicate_count": len(duplicate_ids),
                "duplicate_ids": [d.canonical_id for d in duplicate_ids[:10]]
            }
        )
    
    def _check_no_silent_fx(self, snapshot: models.Snapshot) -> InvariantCheck:
        """
        No Silent FX Invariant:
        No FX rate = 1.0 fallback anywhere (must be explicit or missing)
        """
        # Check for suspicious 1.0 rates between different currencies
        suspicious_fx = self.db.query(models.WeeklyFXRate).filter(
            and_(
                models.WeeklyFXRate.snapshot_id == snapshot.id,
                models.WeeklyFXRate.rate == 1.0,
                models.WeeklyFXRate.from_currency != models.WeeklyFXRate.to_currency
            )
        ).all()
        
        passed = len(suspicious_fx) == 0
        
        evidence = [
            EvidenceRef(
                ref_type="fx_rate",
                ref_id=fx.id,
                description=f"Suspicious rate=1.0 for {fx.from_currency}/{fx.to_currency}"
            )
            for fx in suspicious_fx[:50]
        ]
        
        return InvariantCheck(
            name="No Silent FX",
            passed=passed,
            severity=InvariantSeverity.ERROR,
            message="No suspicious FX rate=1.0 fallbacks found" if passed else f"{len(suspicious_fx)} suspicious FX fallbacks found",
            evidence=evidence,
            details={
                "suspicious_fx_count": len(suspicious_fx),
                "suspicious_pairs": [(fx.from_currency, fx.to_currency) for fx in suspicious_fx[:10]]
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOCK GATES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _build_lock_gates(
        self,
        metrics: List[TrustMetric],
        invariants: List[InvariantCheck]
    ) -> List[LockGate]:
        """Build lock gates from metrics and invariants."""
        gates = []
        
        # Metric-based gates
        metric_gate_configs = [
            ("Cash Explained %", True, "I acknowledge that cash explained is below the target threshold."),
            ("Unknown Exposure €", True, "I acknowledge the unknown exposure and accept responsibility for unexplained cash."),
            ("Missing FX Exposure €", True, "I acknowledge missing FX rates and accept currency conversion risk."),
            ("Reconciliation Integrity %", True, "I acknowledge reconciliation integrity issues."),
        ]
        
        for metric_name, can_override, ack_text in metric_gate_configs:
            metric = next((m for m in metrics if m.name == metric_name), None)
            if metric:
                gates.append(LockGate(
                    name=f"Gate: {metric_name}",
                    passed=metric.status == MetricStatus.PASS,
                    can_override=can_override,
                    requires_acknowledgment=True,
                    metric=metric,
                    acknowledgment_text_required=ack_text if metric.status != MetricStatus.PASS else None
                ))
        
        # Invariant-based gates
        for inv in invariants:
            can_override = inv.severity != InvariantSeverity.CRITICAL
            ack_text = f"I acknowledge the {inv.name} check failed and accept the associated risk."
            
            gates.append(LockGate(
                name=f"Gate: {inv.name}",
                passed=inv.passed,
                can_override=can_override,
                requires_acknowledgment=not inv.passed and can_override,
                invariant=inv,
                acknowledgment_text_required=ack_text if not inv.passed and can_override else None
            ))
        
        return gates
    
    def _evaluate_lock_eligibility(
        self,
        lock_gates: List[LockGate]
    ) -> Tuple[bool, List[str]]:
        """Evaluate if snapshot can be locked."""
        blocked_reasons = []
        
        for gate in lock_gates:
            if not gate.passed and not gate.can_override:
                blocked_reasons.append(f"{gate.name}: Cannot be overridden")
        
        # Lock is eligible if no non-overridable gates failed
        lock_eligible = len(blocked_reasons) == 0
        
        return lock_eligible, blocked_reasons
    
    def _calculate_trust_score(
        self,
        metrics: List[TrustMetric],
        invariants: List[InvariantCheck]
    ) -> float:
        """Calculate overall trust score (0-100)."""
        score = 100.0
        
        # Deduct for failed metrics
        for metric in metrics:
            if metric.status == MetricStatus.FAIL:
                score -= 15.0
            elif metric.status == MetricStatus.WARN:
                score -= 5.0
        
        # Deduct for failed invariants
        for inv in invariants:
            if not inv.passed:
                if inv.severity == InvariantSeverity.CRITICAL:
                    score -= 25.0
                elif inv.severity == InvariantSeverity.ERROR:
                    score -= 15.0
                else:
                    score -= 5.0
        
        return max(0.0, min(100.0, score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOCK WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    
    def attempt_lock(
        self,
        snapshot_id: int,
        user: str,
        override_acknowledgments: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Attempt to lock a snapshot.
        
        Args:
            snapshot_id: Snapshot to lock
            user: User requesting the lock
            override_acknowledgments: Dict of gate_name -> acknowledgment text for overrides
        
        Returns:
            Dict with success status, message, and any required acknowledgments
        """
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            return {"success": False, "message": "Snapshot not found"}
        
        if snapshot.status == models.SnapshotStatus.LOCKED:
            return {"success": False, "message": "Snapshot is already locked"}
        
        # Generate trust report
        report = self.generate_trust_report(snapshot_id)
        
        # Check for blocking gates
        override_acknowledgments = override_acknowledgments or {}
        missing_acknowledgments = []
        audit_entries = []
        
        for gate in report.lock_gates:
            if not gate.passed:
                if not gate.can_override:
                    return {
                        "success": False,
                        "message": f"Lock blocked by non-overridable gate: {gate.name}",
                        "gate": gate.to_dict()
                    }
                
                # Check for acknowledgment
                ack_text = override_acknowledgments.get(gate.name)
                if not ack_text or ack_text != gate.acknowledgment_text_required:
                    missing_acknowledgments.append({
                        "gate_name": gate.name,
                        "required_text": gate.acknowledgment_text_required
                    })
                else:
                    # Record the override
                    audit_entries.append({
                        "gate_name": gate.name,
                        "acknowledgment": ack_text,
                        "user": user,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
        
        if missing_acknowledgments:
            return {
                "success": False,
                "message": "Override acknowledgments required for failed gates",
                "missing_acknowledgments": missing_acknowledgments
            }
        
        # All gates passed or overridden - lock the snapshot
        snapshot.status = models.SnapshotStatus.LOCKED
        snapshot.is_locked = 1
        snapshot.locked_at = datetime.now(timezone.utc)
        snapshot.locked_by = user
        snapshot.lock_gate_checks = {
            "trust_report": report.to_dict(),
            "overrides": audit_entries
        }
        
        # Record audit log
        from utils import record_audit_log
        record_audit_log(
            self.db,
            user=user,
            action="Lock",
            resource_type="Snapshot",
            resource_id=snapshot_id,
            changes={
                "status": {"old": "ready_for_review", "new": "locked"},
                "trust_score": report.overall_trust_score,
                "overrides": audit_entries
            },
            snapshot_id=snapshot_id
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "Snapshot locked successfully",
            "trust_report": report.to_dict()
        }
