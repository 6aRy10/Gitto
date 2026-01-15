"""
Trust Report Service

Computes amount-weighted trust metrics and evaluates lock gates.
Provides evidence links for UI drilldowns.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import json

from trust_report_models import (
    TrustReport, TrustMetric, LockGateOverrideLog, LockGateConfig,
    MetricUnit, LockGateStatus
)
import models


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetricResult:
    """Result of computing a single metric."""
    key: str
    description: str
    value: float
    unit: str
    exposure_amount_base: float = 0.0
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    breakdown: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GateResult:
    """Result of evaluating a lock gate."""
    gate: str
    description: str
    threshold: float
    actual: float
    exposure: float
    status: LockGateStatus
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LockGateThresholds:
    """Configurable thresholds for lock gates."""
    missing_fx_threshold_pct: float = 0.01  # 1%
    unexplained_cash_threshold_pct: float = 0.05  # 5%
    duplicate_exposure_threshold: float = 0.0
    freshness_mismatch_hours: float = 72.0
    require_critical_findings_resolved: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST REPORT SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class TrustReportService:
    """
    Service for generating trust reports and evaluating lock eligibility.
    """
    
    def __init__(self, db: Session, base_currency: str = "EUR"):
        self.db = db
        self.base_currency = base_currency
    
    def generate_trust_report(
        self,
        snapshot_id: int,
        thresholds: Optional[LockGateThresholds] = None
    ) -> TrustReport:
        """
        Generate a complete trust report for a snapshot.
        
        Args:
            snapshot_id: Snapshot to analyze
            thresholds: Custom thresholds (or load from config)
        
        Returns:
            TrustReport with all metrics and gate evaluations
        """
        # Get snapshot
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        # Load thresholds from config or use defaults
        if thresholds is None:
            thresholds = self._load_thresholds(snapshot.entity_id)
        
        # Compute all metrics
        metrics: List[MetricResult] = []
        
        metrics.append(self._compute_cash_explained_pct(snapshot))
        metrics.append(self._compute_unknown_exposure(snapshot))
        metrics.append(self._compute_missing_fx_exposure(snapshot))
        metrics.append(self._compute_freshness_mismatch(snapshot))
        metrics.append(self._compute_duplicate_exposure(snapshot))
        metrics.append(self._compute_suggested_matches_pending(snapshot))
        metrics.append(self._compute_forecast_calibration_coverage(snapshot))
        metrics.append(self._compute_drift_warning(snapshot))
        
        # Evaluate lock gates
        gates = self._evaluate_lock_gates(snapshot, metrics, thresholds)
        
        # Calculate trust score
        trust_score = self._calculate_trust_score(metrics, gates)
        
        # Determine lock eligibility
        lock_eligible = all(g.status != LockGateStatus.FAILED for g in gates)
        
        # Create report
        report = TrustReport(
            snapshot_id=snapshot_id,
            trust_score=trust_score,
            lock_eligible=lock_eligible,
            gate_failures_json=[
                {
                    "gate": g.gate,
                    "description": g.description,
                    "threshold": g.threshold,
                    "actual": g.actual,
                    "exposure": g.exposure,
                    "status": g.status.value
                }
                for g in gates if g.status == LockGateStatus.FAILED
            ],
            metrics_json={m.key: m.value for m in metrics},
            config_json={
                "base_currency": self.base_currency,
                "missing_fx_threshold_pct": thresholds.missing_fx_threshold_pct,
                "unexplained_cash_threshold_pct": thresholds.unexplained_cash_threshold_pct,
                "duplicate_exposure_threshold": thresholds.duplicate_exposure_threshold,
                "freshness_mismatch_hours": thresholds.freshness_mismatch_hours
            }
        )
        
        self.db.add(report)
        self.db.flush()
        
        # Get previous report for trend calculation
        prev_report = self._get_previous_report(snapshot_id)
        
        # Store individual metrics
        for metric in metrics:
            trend_delta = None
            trend_direction = None
            
            if prev_report:
                prev_metric = self.db.query(TrustMetric).filter(
                    TrustMetric.report_id == prev_report.id,
                    TrustMetric.key == metric.key
                ).first()
                if prev_metric:
                    trend_delta = metric.value - prev_metric.value
                    if abs(trend_delta) < 0.01:
                        trend_direction = "stable"
                    elif trend_delta > 0:
                        trend_direction = "up"
                    else:
                        trend_direction = "down"
            
            db_metric = TrustMetric(
                report_id=report.id,
                key=metric.key,
                description=metric.description,
                value=metric.value,
                unit=metric.unit,
                exposure_amount_base=metric.exposure_amount_base,
                trend_delta=trend_delta,
                trend_direction=trend_direction,
                evidence_refs_json=metric.evidence_refs[:50],  # Limit evidence
                breakdown_json=metric.breakdown
            )
            self.db.add(db_metric)
        
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_latest_report(self, snapshot_id: int) -> Optional[TrustReport]:
        """Get the latest trust report for a snapshot."""
        return self.db.query(TrustReport).filter(
            TrustReport.snapshot_id == snapshot_id
        ).order_by(TrustReport.created_at.desc()).first()
    
    def _get_previous_report(self, snapshot_id: int) -> Optional[TrustReport]:
        """Get the previous trust report (for trend calculation)."""
        reports = self.db.query(TrustReport).filter(
            TrustReport.snapshot_id == snapshot_id
        ).order_by(TrustReport.created_at.desc()).limit(2).all()
        
        if len(reports) >= 2:
            return reports[1]
        return None
    
    def _load_thresholds(self, entity_id: int) -> LockGateThresholds:
        """Load thresholds from config or return defaults."""
        config = self.db.query(LockGateConfig).filter(
            LockGateConfig.entity_id == entity_id
        ).first()
        
        if config:
            return LockGateThresholds(
                missing_fx_threshold_pct=config.missing_fx_threshold_pct,
                unexplained_cash_threshold_pct=config.unexplained_cash_threshold_pct,
                duplicate_exposure_threshold=config.duplicate_exposure_threshold,
                freshness_mismatch_hours=config.freshness_mismatch_hours,
                require_critical_findings_resolved=config.require_critical_findings_resolved
            )
        
        return LockGateThresholds()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # METRIC COMPUTATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _compute_cash_explained_pct(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute cash explained percentage by reconciliation tier.
        
        Amount-weighted: (reconciled_amount / total_bank_amount) * 100
        """
        # Get bank transactions
        bank_accounts = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        
        if not bank_accounts:
            return MetricResult(
                key="cash_explained_pct",
                description="Percentage of bank cash reconciled to invoices/bills",
                value=100.0,
                unit=MetricUnit.PERCENT.value,
                evidence_refs=[]
            )
        
        transactions = self.db.query(models.BankTransaction).filter(
            models.BankTransaction.bank_account_id.in_([a.id for a in bank_accounts])
        ).all()
        
        total_amount = sum(abs(t.amount or 0) for t in transactions)
        
        if total_amount == 0:
            return MetricResult(
                key="cash_explained_pct",
                description="Percentage of bank cash reconciled to invoices/bills",
                value=100.0,
                unit=MetricUnit.PERCENT.value,
                evidence_refs=[]
            )
        
        # Get reconciled amounts
        recon_records = self.db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.bank_transaction_id.in_([t.id for t in transactions])
        ).all()
        
        reconciled_amount = sum(r.amount_allocated or 0 for r in recon_records)
        unexplained_amount = total_amount - reconciled_amount
        
        # Build evidence for unexplained transactions
        reconciled_txn_ids = {r.bank_transaction_id for r in recon_records}
        unexplained_txns = [
            t for t in transactions 
            if t.id not in reconciled_txn_ids
        ]
        
        evidence = [
            {
                "type": "bank_txn",
                "id": t.id,
                "amount": t.amount,
                "date": t.transaction_date.isoformat() if t.transaction_date else None,
                "reference": t.reference,
                "counterparty": t.counterparty
            }
            for t in unexplained_txns[:20]
        ]
        
        # Breakdown by tier
        breakdown = {
            "by_tier": {
                "exact_match": sum(r.amount_allocated or 0 for r in recon_records if r.match_type == "exact"),
                "partial_match": sum(r.amount_allocated or 0 for r in recon_records if r.match_type == "partial"),
                "suggested": sum(r.amount_allocated or 0 for r in recon_records if r.match_type == "suggested"),
                "manual": sum(r.amount_allocated or 0 for r in recon_records if r.match_type == "manual")
            },
            "unexplained_count": len(unexplained_txns),
            "total_txn_count": len(transactions)
        }
        
        explained_pct = (reconciled_amount / total_amount * 100) if total_amount > 0 else 100.0
        
        return MetricResult(
            key="cash_explained_pct",
            description="Percentage of bank cash reconciled to invoices/bills",
            value=round(explained_pct, 2),
            unit=MetricUnit.PERCENT.value,
            exposure_amount_base=unexplained_amount,
            evidence_refs=evidence,
            breakdown=breakdown
        )
    
    def _compute_unknown_exposure(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute total unknown/unreconciled exposure in base currency.
        """
        # Get invoices with "Unknown" truth label
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id,
            models.Invoice.truth_label == "Unknown"
        ).all()
        
        total_exposure = sum(abs(inv.amount or 0) for inv in invoices)
        
        # Breakdown by customer
        from collections import defaultdict
        by_customer = defaultdict(float)
        for inv in invoices:
            by_customer[inv.customer or "UNKNOWN"] += abs(inv.amount or 0)
        
        evidence = [
            {
                "type": "invoice",
                "id": inv.id,
                "document_number": inv.document_number,
                "amount": inv.amount,
                "customer": inv.customer,
                "currency": inv.currency
            }
            for inv in invoices[:20]
        ]
        
        return MetricResult(
            key="unknown_exposure_base",
            description=f"Total unreconciled exposure in {self.base_currency}",
            value=total_exposure,
            unit=MetricUnit.CURRENCY.value,
            exposure_amount_base=total_exposure,
            evidence_refs=evidence,
            breakdown={
                "by_customer": dict(sorted(by_customer.items(), key=lambda x: -x[1])[:10]),
                "invoice_count": len(invoices)
            }
        )
    
    def _compute_missing_fx_exposure(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute exposure from foreign currency items missing FX rates.
        """
        # Get invoices with foreign currency
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id,
            models.Invoice.currency != self.base_currency,
            models.Invoice.currency.isnot(None)
        ).all()
        
        if not invoices:
            return MetricResult(
                key="missing_fx_exposure_base",
                description=f"Exposure from foreign currency items missing FX rates",
                value=0.0,
                unit=MetricUnit.CURRENCY.value,
                evidence_refs=[]
            )
        
        # Get available FX rates
        fx_rates = self.db.query(models.WeeklyFXRate).filter(
            models.WeeklyFXRate.snapshot_id == snapshot.id
        ).all()
        
        rate_pairs = set()
        for fx in fx_rates:
            rate_pairs.add((fx.from_currency, fx.to_currency))
            rate_pairs.add((fx.to_currency, fx.from_currency))  # Inverse
        
        # Find invoices missing rates
        missing_fx_invoices = []
        total_exposure = 0.0
        
        for inv in invoices:
            has_rate = (
                (inv.currency, self.base_currency) in rate_pairs or
                (self.base_currency, inv.currency) in rate_pairs
            )
            
            if not has_rate:
                missing_fx_invoices.append(inv)
                total_exposure += abs(inv.amount or 0)
        
        # Breakdown by currency
        from collections import defaultdict
        by_currency = defaultdict(float)
        for inv in missing_fx_invoices:
            by_currency[inv.currency] += abs(inv.amount or 0)
        
        evidence = [
            {
                "type": "invoice",
                "id": inv.id,
                "document_number": inv.document_number,
                "amount": inv.amount,
                "currency": inv.currency,
                "customer": inv.customer
            }
            for inv in missing_fx_invoices[:20]
        ]
        
        return MetricResult(
            key="missing_fx_exposure_base",
            description=f"Exposure from foreign currency items missing FX rates",
            value=total_exposure,
            unit=MetricUnit.CURRENCY.value,
            exposure_amount_base=total_exposure,
            evidence_refs=evidence,
            breakdown={
                "by_currency": dict(by_currency),
                "invoice_count": len(missing_fx_invoices)
            }
        )
    
    def _compute_freshness_mismatch(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute data freshness mismatch between bank and ERP.
        """
        # In a full implementation, we'd compare bank_as_of vs erp_as_of
        # For now, calculate based on snapshot age and last sync
        
        bank_freshness_hours = None
        erp_freshness_hours = None
        
        # Check for bank sync metadata
        if hasattr(snapshot, 'bank_sync_at') and snapshot.bank_sync_at:
            delta = datetime.now(timezone.utc) - snapshot.bank_sync_at
            bank_freshness_hours = delta.total_seconds() / 3600
        
        # Check for ERP sync metadata
        if hasattr(snapshot, 'erp_sync_at') and snapshot.erp_sync_at:
            delta = datetime.now(timezone.utc) - snapshot.erp_sync_at
            erp_freshness_hours = delta.total_seconds() / 3600
        
        # Calculate mismatch
        mismatch_hours = 0.0
        if bank_freshness_hours is not None and erp_freshness_hours is not None:
            mismatch_hours = abs(bank_freshness_hours - erp_freshness_hours)
        
        return MetricResult(
            key="freshness_mismatch_hours",
            description="Hours difference between bank and ERP data freshness",
            value=mismatch_hours,
            unit=MetricUnit.HOURS.value,
            breakdown={
                "bank_freshness_hours": bank_freshness_hours,
                "erp_freshness_hours": erp_freshness_hours
            }
        )
    
    def _compute_duplicate_exposure(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute exposure from duplicate canonical IDs.
        """
        # Find duplicate canonical_ids
        duplicates = self.db.query(
            models.Invoice.canonical_id,
            func.count(models.Invoice.id).label('count'),
            func.sum(models.Invoice.amount).label('total_amount')
        ).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).group_by(models.Invoice.canonical_id).having(
            func.count(models.Invoice.id) > 1
        ).all()
        
        if not duplicates:
            return MetricResult(
                key="duplicate_exposure_base",
                description="Exposure from duplicate records",
                value=0.0,
                unit=MetricUnit.CURRENCY.value,
                evidence_refs=[]
            )
        
        # Calculate exposure (duplicate amount = (count - 1) * avg_amount)
        total_exposure = 0.0
        evidence = []
        
        for dup in duplicates[:20]:
            # Get sample records
            records = self.db.query(models.Invoice).filter(
                models.Invoice.snapshot_id == snapshot.id,
                models.Invoice.canonical_id == dup.canonical_id
            ).limit(5).all()
            
            dup_amount = sum(abs(r.amount or 0) for r in records[1:])  # Exclude first
            total_exposure += dup_amount
            
            evidence.append({
                "type": "duplicate_group",
                "canonical_id": dup.canonical_id[:30] if dup.canonical_id else None,
                "count": dup.count,
                "total_amount": float(dup.total_amount or 0),
                "sample_doc_numbers": [r.document_number for r in records[:3]]
            })
        
        return MetricResult(
            key="duplicate_exposure_base",
            description="Exposure from duplicate records",
            value=total_exposure,
            unit=MetricUnit.CURRENCY.value,
            exposure_amount_base=total_exposure,
            evidence_refs=evidence,
            breakdown={
                "duplicate_groups": len(duplicates),
                "total_duplicate_records": sum(d.count - 1 for d in duplicates)
            }
        )
    
    def _compute_suggested_matches_pending(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute exposure from suggested matches pending approval.
        """
        # Get pending suggested matches (match_type == "Suggested" or "suggested")
        # These are matches that have been suggested but not converted to "Manual" or "Deterministic"
        pending_matches = self.db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.match_type.in_(["suggested", "Suggested"])
        ).all()
        
        total_exposure = sum(abs(m.amount_allocated or 0) for m in pending_matches)
        
        evidence = [
            {
                "type": "reconciliation",
                "id": m.id,
                "bank_txn_id": m.bank_transaction_id,
                "invoice_id": m.invoice_id,
                "amount": m.amount_allocated,
                "confidence": m.confidence_score
            }
            for m in pending_matches[:20]
        ]
        
        return MetricResult(
            key="suggested_matches_pending_exposure",
            description="Exposure from suggested matches awaiting approval",
            value=total_exposure,
            unit=MetricUnit.CURRENCY.value,
            exposure_amount_base=total_exposure,
            evidence_refs=evidence,
            breakdown={
                "pending_count": len(pending_matches)
            }
        )
    
    def _compute_forecast_calibration_coverage(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute forecast calibration coverage if forecast distributions exist.
        """
        # Check for calibration stats
        calibration = self.db.query(models.CalibrationStats).filter(
            models.CalibrationStats.snapshot_id == snapshot.id
        ).first()
        
        if not calibration:
            return MetricResult(
                key="forecast_calibration_coverage",
                description="Forecast calibration coverage percentage",
                value=0.0,
                unit=MetricUnit.PERCENT.value,
                evidence_refs=[{
                    "type": "note",
                    "message": "No forecast calibration data available"
                }]
            )
        
        # Calculate average coverage
        coverage_values = []
        breakdown = {}
        
        if calibration.p25_coverage is not None:
            coverage_values.append(calibration.p25_coverage)
            breakdown["p25_coverage"] = calibration.p25_coverage
        
        if calibration.p50_coverage is not None:
            coverage_values.append(calibration.p50_coverage)
            breakdown["p50_coverage"] = calibration.p50_coverage
        
        if calibration.p75_coverage is not None:
            coverage_values.append(calibration.p75_coverage)
            breakdown["p75_coverage"] = calibration.p75_coverage
        
        if calibration.p90_coverage is not None:
            coverage_values.append(calibration.p90_coverage)
            breakdown["p90_coverage"] = calibration.p90_coverage
        
        avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
        
        return MetricResult(
            key="forecast_calibration_coverage",
            description="Forecast calibration coverage percentage",
            value=round(avg_coverage * 100, 2),
            unit=MetricUnit.PERCENT.value,
            breakdown=breakdown,
            evidence_refs=[{
                "type": "calibration_stats",
                "id": calibration.id,
                "sample_size": calibration.sample_size
            }]
        )
    
    def _compute_drift_warning(self, snapshot: models.Snapshot) -> MetricResult:
        """
        Compute schema drift warning based on recent datasets.
        """
        # Check for schema drift events
        try:
            from lineage_models import SchemaDriftEvent, LineageDataset
            
            # Get recent datasets for the entity
            recent_datasets = self.db.query(LineageDataset).filter(
                LineageDataset.entity_id == snapshot.entity_id
            ).order_by(LineageDataset.created_at.desc()).limit(10).all()
            
            if len(recent_datasets) < 2:
                return MetricResult(
                    key="drift_warning",
                    description="Schema drift warning (0=no drift, 1=drift detected)",
                    value=0.0,
                    unit=MetricUnit.BOOLEAN.value,
                    evidence_refs=[]
                )
            
            # Check fingerprints
            fingerprints = [d.schema_fingerprint for d in recent_datasets if d.schema_fingerprint]
            unique_fingerprints = set(fingerprints)
            
            has_drift = len(unique_fingerprints) > 1
            
            evidence = []
            if has_drift:
                for i, ds in enumerate(recent_datasets[:5]):
                    evidence.append({
                        "type": "dataset",
                        "id": ds.id,
                        "dataset_id": ds.dataset_id,
                        "schema_fingerprint": ds.schema_fingerprint[:16] if ds.schema_fingerprint else None,
                        "created_at": ds.created_at.isoformat() if ds.created_at else None
                    })
            
            return MetricResult(
                key="drift_warning",
                description="Schema drift warning (0=no drift, 1=drift detected)",
                value=1.0 if has_drift else 0.0,
                unit=MetricUnit.BOOLEAN.value,
                evidence_refs=evidence,
                breakdown={
                    "unique_fingerprints": len(unique_fingerprints),
                    "datasets_checked": len(recent_datasets)
                }
            )
        except ImportError:
            return MetricResult(
                key="drift_warning",
                description="Schema drift warning (0=no drift, 1=drift detected)",
                value=0.0,
                unit=MetricUnit.BOOLEAN.value,
                evidence_refs=[{
                    "type": "note",
                    "message": "Lineage module not available"
                }]
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOCK GATE EVALUATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _evaluate_lock_gates(
        self,
        snapshot: models.Snapshot,
        metrics: List[MetricResult],
        thresholds: LockGateThresholds
    ) -> List[GateResult]:
        """
        Evaluate all lock gates against computed metrics.
        """
        gates = []
        metrics_dict = {m.key: m for m in metrics}
        
        # Get total forecasted amount for percentage calculations
        total_amount = self._get_total_forecasted_amount(snapshot)
        
        # Gate 1: Missing FX exposure
        missing_fx = metrics_dict.get("missing_fx_exposure_base")
        if missing_fx and total_amount > 0:
            missing_fx_pct = missing_fx.value / total_amount
            threshold = thresholds.missing_fx_threshold_pct
            
            gates.append(GateResult(
                gate="missing_fx_exposure",
                description=f"Missing FX exposure must be <= {threshold*100:.1f}% of forecasted amount",
                threshold=threshold,
                actual=missing_fx_pct,
                exposure=missing_fx.value,
                status=LockGateStatus.PASSED if missing_fx_pct <= threshold else LockGateStatus.FAILED,
                evidence_refs=missing_fx.evidence_refs[:10]
            ))
        
        # Gate 2: Unexplained cash exposure
        cash_explained = metrics_dict.get("cash_explained_pct")
        if cash_explained:
            unexplained_pct = (100 - cash_explained.value) / 100
            threshold = thresholds.unexplained_cash_threshold_pct
            
            gates.append(GateResult(
                gate="unexplained_cash_exposure",
                description=f"Unexplained cash must be <= {threshold*100:.1f}% of total",
                threshold=threshold,
                actual=unexplained_pct,
                exposure=cash_explained.exposure_amount_base,
                status=LockGateStatus.PASSED if unexplained_pct <= threshold else LockGateStatus.FAILED,
                evidence_refs=cash_explained.evidence_refs[:10]
            ))
        
        # Gate 3: No duplicates
        duplicates = metrics_dict.get("duplicate_exposure_base")
        if duplicates:
            threshold = thresholds.duplicate_exposure_threshold
            
            gates.append(GateResult(
                gate="duplicate_exposure",
                description=f"Duplicate exposure must be <= {threshold}",
                threshold=threshold,
                actual=duplicates.value,
                exposure=duplicates.value,
                status=LockGateStatus.PASSED if duplicates.value <= threshold else LockGateStatus.FAILED,
                evidence_refs=duplicates.evidence_refs[:10]
            ))
        
        # Gate 4: Freshness
        freshness = metrics_dict.get("freshness_mismatch_hours")
        if freshness:
            threshold = thresholds.freshness_mismatch_hours
            
            gates.append(GateResult(
                gate="freshness_mismatch",
                description=f"Data freshness mismatch must be <= {threshold} hours",
                threshold=threshold,
                actual=freshness.value,
                exposure=0.0,  # No monetary exposure
                status=LockGateStatus.PASSED if freshness.value <= threshold else LockGateStatus.FAILED,
                evidence_refs=[]
            ))
        
        # Gate 5: Critical health findings (check from health report if available)
        if thresholds.require_critical_findings_resolved:
            critical_findings = self._check_critical_health_findings(snapshot)
            if critical_findings:
                gates.append(GateResult(
                    gate="critical_findings_resolved",
                    description="All critical health findings must be resolved or acknowledged",
                    threshold=0,
                    actual=len(critical_findings),
                    exposure=sum(f.get("exposure", 0) for f in critical_findings),
                    status=LockGateStatus.FAILED,
                    evidence_refs=critical_findings[:10]
                ))
        
        return gates
    
    def _get_total_forecasted_amount(self, snapshot: models.Snapshot) -> float:
        """Get total forecasted amount for threshold calculations."""
        # Sum of all invoices + bills
        invoices_total = self.db.query(func.sum(models.Invoice.amount)).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).scalar() or 0.0
        
        return float(invoices_total)
    
    def _check_critical_health_findings(self, snapshot: models.Snapshot) -> List[Dict]:
        """Check for unresolved critical health findings."""
        try:
            from health_report_models import DataHealthReport, HealthFinding
            
            # Get latest health report
            report = self.db.query(DataHealthReport).filter(
                DataHealthReport.dataset_id == snapshot.dataset_id
            ).order_by(DataHealthReport.created_at.desc()).first()
            
            if not report:
                return []
            
            # Get critical findings
            critical = self.db.query(HealthFinding).filter(
                HealthFinding.report_id == report.id,
                HealthFinding.severity == "critical"
            ).all()
            
            return [
                {
                    "type": "health_finding",
                    "id": f.id,
                    "category": f.category,
                    "metric_key": f.metric_key,
                    "exposure": f.exposure_amount_base
                }
                for f in critical
            ]
        except ImportError:
            return []
    
    def _calculate_trust_score(
        self,
        metrics: List[MetricResult],
        gates: List[GateResult]
    ) -> float:
        """
        Calculate overall trust score (0-100).
        
        Weighted by importance:
        - Cash explained: 30%
        - No missing FX: 20%
        - No duplicates: 15%
        - Freshness: 10%
        - Calibration: 15%
        - Gates passed: 10%
        """
        score = 0.0
        metrics_dict = {m.key: m for m in metrics}
        
        # Cash explained (30%)
        cash = metrics_dict.get("cash_explained_pct")
        if cash:
            score += (cash.value / 100) * 30
        
        # Missing FX (20%) - inverse: lower is better
        fx = metrics_dict.get("missing_fx_exposure_base")
        if fx:
            # Score 20 if no missing FX, 0 if > 100k missing
            fx_score = max(0, 20 - (fx.value / 5000))
            score += fx_score
        else:
            score += 20
        
        # Duplicates (15%) - inverse
        dups = metrics_dict.get("duplicate_exposure_base")
        if dups:
            dup_score = 15 if dups.value == 0 else max(0, 15 - (dups.value / 10000))
            score += dup_score
        else:
            score += 15
        
        # Freshness (10%)
        fresh = metrics_dict.get("freshness_mismatch_hours")
        if fresh:
            fresh_score = max(0, 10 - (fresh.value / 7.2))  # Lose 1 point per 7.2 hours
            score += fresh_score
        else:
            score += 10
        
        # Calibration (15%)
        calib = metrics_dict.get("forecast_calibration_coverage")
        if calib:
            score += (calib.value / 100) * 15
        
        # Gates passed (10%)
        passed_gates = sum(1 for g in gates if g.status == LockGateStatus.PASSED)
        total_gates = len(gates)
        if total_gates > 0:
            score += (passed_gates / total_gates) * 10
        else:
            score += 10
        
        return round(min(100, max(0, score)), 1)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LOCK WITH CFO OVERRIDE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def attempt_lock(
        self,
        snapshot_id: int,
        user_id: str,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        override_acknowledgment: Optional[str] = None,
        override_reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[TrustReport]]:
        """
        Attempt to lock a snapshot.
        
        If lock gates fail and override provided, requires:
        - Acknowledgment text >= 20 characters
        - Audit log entry
        
        Returns:
            (success, message, trust_report)
        """
        # Generate fresh trust report
        report = self.generate_trust_report(snapshot_id)
        
        # Get snapshot
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            return False, f"Snapshot {snapshot_id} not found", None
        
        # Already locked?
        if snapshot.status == models.SnapshotStatus.LOCKED or snapshot.is_locked == 1:
            return False, "Snapshot is already locked", report
        
        # Check if lock eligible
        if report.lock_eligible:
            # Direct lock - no override needed
            snapshot.status = models.SnapshotStatus.LOCKED
            snapshot.is_locked = 1
            snapshot.locked_at = datetime.now(timezone.utc)
            snapshot.locked_by = user_email or user_id
            
            self.db.commit()
            return True, "Snapshot locked successfully", report
        
        # Lock not eligible - check for override
        if not override_acknowledgment:
            failed_gates = report.gate_failures_json or []
            gate_names = [g["gate"] for g in failed_gates]
            return False, f"Lock gates failed: {', '.join(gate_names)}. Provide override acknowledgment to proceed.", report
        
        # Validate override acknowledgment
        if len(override_acknowledgment) < 20:
            return False, "Override acknowledgment must be at least 20 characters", report
        
        # Check if override is allowed
        config = self._load_thresholds(snapshot.entity_id)
        if not config.require_critical_findings_resolved:
            # Override not allowed by config
            return False, "CFO override is not allowed for this entity", report
        
        # Log the override
        override_log = LockGateOverrideLog(
            snapshot_id=snapshot_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            acknowledgment_text=override_acknowledgment,
            failed_gates_json=report.gate_failures_json,
            override_reason=override_reason,
            ip_address=ip_address
        )
        self.db.add(override_log)
        
        # Lock the snapshot
        snapshot.status = models.SnapshotStatus.LOCKED
        snapshot.is_locked = 1
        snapshot.locked_at = datetime.now(timezone.utc)
        snapshot.locked_by = user_email or user_id
        
        # Store override reference
        if hasattr(snapshot, 'lock_override_id'):
            snapshot.lock_override_id = override_log.id
        
        self.db.commit()
        
        return True, f"Snapshot locked with CFO override. {len(report.gate_failures_json or [])} gate(s) were overridden.", report
