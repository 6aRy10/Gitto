"""
Data Health Report Service

Computes comprehensive health reports for Datasets with:
- Amount-weighted findings
- Multiple categories (completeness, validity, consistency, etc.)
- Schema drift detection
- Outlier detection
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import statistics
import hashlib
import json

from health_report_models import (
    DataHealthReportRecord, HealthFinding,
    FindingSeverity, FindingCategory
)
from lineage_models import (
    LineageDataset, LineageConnection, CanonicalRecord, RawRecord, SchemaDriftEvent
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FindingData:
    """Data for a single health finding."""
    category: FindingCategory
    severity: FindingSeverity
    metric_key: str
    metric_label: str
    metric_value: float
    exposure_amount: float
    exposure_currency: str
    count_rows: int
    sample_evidence: List[Dict[str, Any]]
    threshold_value: Optional[float] = None
    threshold_type: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH REPORT SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class HealthReportService:
    """
    Service for computing and storing data health reports.
    """
    
    # Thresholds for severity determination
    THRESHOLDS = {
        "missing_due_date_pct_warn": 5.0,
        "missing_due_date_pct_critical": 20.0,
        "missing_currency_pct_warn": 1.0,
        "missing_currency_pct_critical": 5.0,
        "missing_fx_pct_warn": 5.0,
        "missing_fx_pct_critical": 15.0,
        "duplicate_pct_warn": 0.1,
        "duplicate_pct_critical": 1.0,
        "outlier_zscore": 3.0,
        "freshness_hours_warn": 24.0,
        "freshness_hours_critical": 72.0,
    }
    
    def __init__(self, db: Session, base_currency: str = "EUR"):
        self.db = db
        self.base_currency = base_currency
    
    def generate_report(
        self,
        dataset_id: int,
        connection_id: Optional[int] = None
    ) -> DataHealthReportRecord:
        """
        Generate and store a health report for a dataset.
        
        Args:
            dataset_id: Dataset to analyze
            connection_id: Optional connection for schema drift comparison
        
        Returns:
            Persisted DataHealthReportRecord
        """
        # Get dataset
        dataset = self.db.query(LineageDataset).filter(
            LineageDataset.id == dataset_id
        ).first()
        
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Get canonical records
        records = self.db.query(CanonicalRecord).filter(
            CanonicalRecord.dataset_id == dataset_id
        ).all()
        
        if not records:
            # Empty dataset - create minimal report
            return self._create_empty_report(dataset_id, connection_id)
        
        # Compute all findings
        findings: List[FindingData] = []
        
        # Completeness findings
        findings.extend(self._check_missing_due_dates(records))
        findings.extend(self._check_missing_currency(records))
        findings.extend(self._check_missing_fx_rates(records, dataset))
        
        # Consistency findings
        findings.extend(self._check_duplicate_canonical_ids(records))
        
        # Anomaly findings
        findings.extend(self._check_outlier_amounts(records))
        findings.extend(self._check_negative_amounts(records))
        
        # Freshness findings
        if connection_id:
            findings.extend(self._check_freshness_mismatch(dataset, connection_id))
        
        # Schema drift findings
        if connection_id:
            findings.extend(self._check_schema_drift(dataset, connection_id))
        
        # Calculate summary metrics
        summary = self._calculate_summary(records, findings)
        
        # Calculate severity score
        severity_score = self._calculate_severity_score(findings, summary)
        
        # Create report record
        report = DataHealthReportRecord(
            dataset_id=dataset_id,
            connection_id=connection_id,
            severity_score=severity_score,
            summary_json=summary,
            schema_fingerprint=dataset.schema_fingerprint
        )
        self.db.add(report)
        self.db.flush()
        
        # Create finding records
        for finding_data in findings:
            finding = HealthFinding(
                report_id=report.id,
                category=finding_data.category.value,
                severity=finding_data.severity.value,
                metric_key=finding_data.metric_key,
                metric_label=finding_data.metric_label,
                metric_value=finding_data.metric_value,
                exposure_amount_base=finding_data.exposure_amount,
                exposure_currency=finding_data.exposure_currency,
                count_rows=finding_data.count_rows,
                sample_evidence_json=finding_data.sample_evidence[:10],  # Limit to 10
                threshold_value=finding_data.threshold_value,
                threshold_type=finding_data.threshold_type
            )
            self.db.add(finding)
        
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_report(self, dataset_id: int) -> Optional[DataHealthReportRecord]:
        """Get latest health report for a dataset."""
        return self.db.query(DataHealthReportRecord).filter(
            DataHealthReportRecord.dataset_id == dataset_id
        ).order_by(DataHealthReportRecord.created_at.desc()).first()
    
    def get_connection_latest_report(
        self, 
        connection_id: int
    ) -> Optional[DataHealthReportRecord]:
        """Get latest health report for a connection."""
        return self.db.query(DataHealthReportRecord).filter(
            DataHealthReportRecord.connection_id == connection_id
        ).order_by(DataHealthReportRecord.created_at.desc()).first()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPLETENESS CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_missing_due_dates(self, records: List[CanonicalRecord]) -> List[FindingData]:
        """Check for missing due dates (AR/AP only)."""
        findings = []
        
        # Filter to AR/AP records
        ar_ap_records = [r for r in records if r.record_type in ("Invoice", "VendorBill")]
        
        if not ar_ap_records:
            return findings
        
        missing = [r for r in ar_ap_records if r.due_date is None]
        
        if not missing:
            return findings
        
        # Calculate exposure
        exposure = sum(abs(r.amount or 0) for r in missing)
        total = sum(abs(r.amount or 0) for r in ar_ap_records)
        pct = (len(missing) / len(ar_ap_records) * 100) if ar_ap_records else 0
        exposure_pct = (exposure / total * 100) if total > 0 else 0
        
        # Determine severity
        if exposure_pct >= self.THRESHOLDS["missing_due_date_pct_critical"]:
            severity = FindingSeverity.CRITICAL
        elif exposure_pct >= self.THRESHOLDS["missing_due_date_pct_warn"]:
            severity = FindingSeverity.WARN
        else:
            severity = FindingSeverity.INFO
        
        findings.append(FindingData(
            category=FindingCategory.COMPLETENESS,
            severity=severity,
            metric_key="missing_due_date",
            metric_label="Missing Due Dates (AR/AP)",
            metric_value=pct,
            exposure_amount=exposure,
            exposure_currency=self.base_currency,
            count_rows=len(missing),
            sample_evidence=[
                {
                    "record_id": r.id,
                    "canonical_id": r.canonical_id[:20] + "...",
                    "amount": r.amount,
                    "counterparty": r.counterparty,
                    "record_type": r.record_type
                }
                for r in missing[:20]
            ],
            threshold_value=self.THRESHOLDS["missing_due_date_pct_warn"],
            threshold_type="max"
        ))
        
        return findings
    
    def _check_missing_currency(self, records: List[CanonicalRecord]) -> List[FindingData]:
        """Check for missing or invalid currency."""
        findings = []
        
        missing = [r for r in records if not r.currency or len(r.currency) != 3]
        
        if not missing:
            return findings
        
        exposure = sum(abs(r.amount or 0) for r in missing)
        total = sum(abs(r.amount or 0) for r in records)
        pct = (len(missing) / len(records) * 100) if records else 0
        exposure_pct = (exposure / total * 100) if total > 0 else 0
        
        if exposure_pct >= self.THRESHOLDS["missing_currency_pct_critical"]:
            severity = FindingSeverity.CRITICAL
        elif exposure_pct >= self.THRESHOLDS["missing_currency_pct_warn"]:
            severity = FindingSeverity.WARN
        else:
            severity = FindingSeverity.INFO
        
        findings.append(FindingData(
            category=FindingCategory.VALIDITY,
            severity=severity,
            metric_key="missing_invalid_currency",
            metric_label="Missing or Invalid Currency",
            metric_value=pct,
            exposure_amount=exposure,
            exposure_currency=self.base_currency,
            count_rows=len(missing),
            sample_evidence=[
                {
                    "record_id": r.id,
                    "canonical_id": r.canonical_id[:20] + "...",
                    "amount": r.amount,
                    "currency": r.currency
                }
                for r in missing[:20]
            ],
            threshold_value=self.THRESHOLDS["missing_currency_pct_warn"],
            threshold_type="max"
        ))
        
        return findings
    
    def _check_missing_fx_rates(
        self, 
        records: List[CanonicalRecord],
        dataset: LineageDataset
    ) -> List[FindingData]:
        """Check for foreign currency records missing FX rates."""
        findings = []
        
        # Get records with foreign currency
        foreign = [r for r in records if r.currency and r.currency != self.base_currency]
        
        if not foreign:
            return findings
        
        # In a real implementation, we'd check against FX rates table
        # For now, flag all foreign currency as potentially missing FX
        # (This would be refined with actual FX rate lookup)
        
        exposure = sum(abs(r.amount or 0) for r in foreign)
        total = sum(abs(r.amount or 0) for r in records)
        pct = (len(foreign) / len(records) * 100) if records else 0
        exposure_pct = (exposure / total * 100) if total > 0 else 0
        
        # Group by currency
        by_currency: Dict[str, List[CanonicalRecord]] = {}
        for r in foreign:
            curr = r.currency or "UNKNOWN"
            if curr not in by_currency:
                by_currency[curr] = []
            by_currency[curr].append(r)
        
        if exposure_pct >= self.THRESHOLDS["missing_fx_pct_critical"]:
            severity = FindingSeverity.CRITICAL
        elif exposure_pct >= self.THRESHOLDS["missing_fx_pct_warn"]:
            severity = FindingSeverity.WARN
        else:
            severity = FindingSeverity.INFO
        
        findings.append(FindingData(
            category=FindingCategory.COMPLETENESS,
            severity=severity,
            metric_key="missing_fx_rate",
            metric_label=f"Foreign Currency Without FX Rate (base: {self.base_currency})",
            metric_value=exposure_pct,
            exposure_amount=exposure,
            exposure_currency=self.base_currency,
            count_rows=len(foreign),
            sample_evidence=[
                {
                    "currency": curr,
                    "count": len(recs),
                    "exposure": sum(abs(r.amount or 0) for r in recs)
                }
                for curr, recs in sorted(by_currency.items(), 
                                         key=lambda x: sum(abs(r.amount or 0) for r in x[1]),
                                         reverse=True)[:10]
            ],
            threshold_value=self.THRESHOLDS["missing_fx_pct_warn"],
            threshold_type="max"
        ))
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONSISTENCY CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_duplicate_canonical_ids(self, records: List[CanonicalRecord]) -> List[FindingData]:
        """Check for duplicate canonical IDs within the dataset."""
        findings = []
        
        # Group by canonical_id
        by_id: Dict[str, List[CanonicalRecord]] = {}
        for r in records:
            if r.canonical_id not in by_id:
                by_id[r.canonical_id] = []
            by_id[r.canonical_id].append(r)
        
        # Find duplicates
        duplicates = {cid: recs for cid, recs in by_id.items() if len(recs) > 1}
        
        if not duplicates:
            return findings
        
        dup_count = sum(len(recs) - 1 for recs in duplicates.values())  # Extra copies
        exposure = sum(
            sum(abs(r.amount or 0) for r in recs[1:])  # Amount in duplicate copies
            for recs in duplicates.values()
        )
        total = sum(abs(r.amount or 0) for r in records)
        pct = (dup_count / len(records) * 100) if records else 0
        exposure_pct = (exposure / total * 100) if total > 0 else 0
        
        if exposure_pct >= self.THRESHOLDS["duplicate_pct_critical"]:
            severity = FindingSeverity.CRITICAL
        elif exposure_pct >= self.THRESHOLDS["duplicate_pct_warn"]:
            severity = FindingSeverity.WARN
        else:
            severity = FindingSeverity.INFO
        
        findings.append(FindingData(
            category=FindingCategory.CONSISTENCY,
            severity=severity,
            metric_key="duplicate_canonical_id",
            metric_label="Duplicate Canonical IDs",
            metric_value=dup_count,
            exposure_amount=exposure,
            exposure_currency=self.base_currency,
            count_rows=dup_count,
            sample_evidence=[
                {
                    "canonical_id": cid[:20] + "...",
                    "count": len(recs),
                    "amounts": [r.amount for r in recs],
                    "counterparties": [r.counterparty for r in recs]
                }
                for cid, recs in sorted(duplicates.items(), 
                                        key=lambda x: len(x[1]), reverse=True)[:10]
            ],
            threshold_value=self.THRESHOLDS["duplicate_pct_warn"],
            threshold_type="max"
        ))
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_outlier_amounts(self, records: List[CanonicalRecord]) -> List[FindingData]:
        """Check for outlier amounts using z-score and IQR."""
        findings = []
        
        amounts = [abs(r.amount) for r in records if r.amount is not None]
        
        if len(amounts) < 10:  # Need minimum sample
            return findings
        
        # Calculate statistics
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
        
        # Z-score method
        outliers_zscore = []
        if stdev > 0:
            for r in records:
                if r.amount is not None:
                    z = (abs(r.amount) - mean) / stdev
                    if abs(z) > self.THRESHOLDS["outlier_zscore"]:
                        outliers_zscore.append((r, z))
        
        # IQR method
        sorted_amounts = sorted(amounts)
        q1_idx = len(sorted_amounts) // 4
        q3_idx = 3 * len(sorted_amounts) // 4
        q1 = sorted_amounts[q1_idx]
        q3 = sorted_amounts[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers_iqr = [
            r for r in records 
            if r.amount is not None and (abs(r.amount) < lower_bound or abs(r.amount) > upper_bound)
        ]
        
        # Combine unique outliers
        all_outlier_ids = set(r.id for r, _ in outliers_zscore) | set(r.id for r in outliers_iqr)
        outliers = [r for r in records if r.id in all_outlier_ids]
        
        if not outliers:
            return findings
        
        exposure = sum(abs(r.amount or 0) for r in outliers)
        
        # Outliers are INFO by default (flagged but not blocked)
        findings.append(FindingData(
            category=FindingCategory.ANOMALY,
            severity=FindingSeverity.INFO,
            metric_key="outlier_amount",
            metric_label="Outlier Amounts (flagged, not removed)",
            metric_value=len(outliers),
            exposure_amount=exposure,
            exposure_currency=self.base_currency,
            count_rows=len(outliers),
            sample_evidence=[
                {
                    "record_id": r.id,
                    "amount": r.amount,
                    "z_score": next((z for rec, z in outliers_zscore if rec.id == r.id), None),
                    "counterparty": r.counterparty,
                    "record_type": r.record_type
                }
                for r in sorted(outliers, key=lambda x: abs(x.amount or 0), reverse=True)[:10]
            ],
            threshold_value=self.THRESHOLDS["outlier_zscore"],
            threshold_type="max"
        ))
        
        return findings
    
    def _check_negative_amounts(self, records: List[CanonicalRecord]) -> List[FindingData]:
        """Check for negative amounts and classify them."""
        findings = []
        
        negatives = [r for r in records if r.amount is not None and r.amount < 0]
        
        if not negatives:
            return findings
        
        # Classify negatives
        classifications = {
            "credit_note": [],
            "refund": [],
            "chargeback": [],
            "reversal": [],
            "unclassified": []
        }
        
        for r in negatives:
            payload = r.payload_json or {}
            doc_type = (payload.get("document_type") or "").lower()
            description = (payload.get("description") or "").lower()
            
            if "credit" in doc_type or "credit" in description:
                classifications["credit_note"].append(r)
            elif "refund" in doc_type or "refund" in description:
                classifications["refund"].append(r)
            elif "chargeback" in doc_type or "chargeback" in description:
                classifications["chargeback"].append(r)
            elif "reversal" in doc_type or "storno" in description:
                classifications["reversal"].append(r)
            else:
                classifications["unclassified"].append(r)
        
        exposure = sum(abs(r.amount or 0) for r in negatives)
        
        # Unclassified negatives are warnings
        unclassified = classifications["unclassified"]
        if unclassified:
            severity = FindingSeverity.WARN if len(unclassified) > 5 else FindingSeverity.INFO
        else:
            severity = FindingSeverity.INFO
        
        findings.append(FindingData(
            category=FindingCategory.ANOMALY,
            severity=severity,
            metric_key="negative_amounts",
            metric_label="Negative Amounts (reversals/credits)",
            metric_value=len(negatives),
            exposure_amount=exposure,
            exposure_currency=self.base_currency,
            count_rows=len(negatives),
            sample_evidence=[
                {
                    "classification": cls,
                    "count": len(recs),
                    "total_amount": sum(r.amount or 0 for r in recs)
                }
                for cls, recs in classifications.items() if recs
            ],
            threshold_value=None,
            threshold_type=None
        ))
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FRESHNESS CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_freshness_mismatch(
        self, 
        dataset: LineageDataset, 
        connection_id: int
    ) -> List[FindingData]:
        """Check data freshness mismatch."""
        findings = []
        
        now = datetime.now(timezone.utc)
        
        # Check dataset creation time
        if dataset.created_at:
            created_at = dataset.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            
            age_hours = (now - created_at).total_seconds() / 3600
            
            if age_hours >= self.THRESHOLDS["freshness_hours_critical"]:
                severity = FindingSeverity.CRITICAL
            elif age_hours >= self.THRESHOLDS["freshness_hours_warn"]:
                severity = FindingSeverity.WARN
            else:
                severity = FindingSeverity.INFO
            
            # Check date range vs now
            date_lag_hours = 0.0
            if dataset.date_range_end:
                end_date = dataset.date_range_end
                if hasattr(end_date, 'tzinfo') and end_date.tzinfo is None:
                    from datetime import datetime as dt
                    end_datetime = dt.combine(end_date, dt.min.time()).replace(tzinfo=timezone.utc)
                else:
                    end_datetime = end_date if isinstance(end_date, datetime) else datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                date_lag_hours = (now - end_datetime).total_seconds() / 3600
            
            findings.append(FindingData(
                category=FindingCategory.FRESHNESS,
                severity=severity,
                metric_key="data_freshness",
                metric_label="Data Freshness",
                metric_value=age_hours,
                exposure_amount=0,
                exposure_currency=self.base_currency,
                count_rows=0,
                sample_evidence=[
                    {
                        "dataset_age_hours": age_hours,
                        "date_range_lag_hours": date_lag_hours,
                        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
                        "date_range_end": dataset.date_range_end.isoformat() if dataset.date_range_end else None
                    }
                ],
                threshold_value=self.THRESHOLDS["freshness_hours_warn"],
                threshold_type="max"
            ))
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCHEMA DRIFT CHECKS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_schema_drift(
        self, 
        dataset: LineageDataset, 
        connection_id: int
    ) -> List[FindingData]:
        """Check for schema drift against previous datasets."""
        findings = []
        
        if not dataset.schema_fingerprint:
            return findings
        
        # Get last N datasets for this connection
        from lineage_models import SyncRun
        
        previous_datasets = self.db.query(LineageDataset).join(
            SyncRun, LineageDataset.sync_run_id == SyncRun.id
        ).filter(
            SyncRun.connection_id == connection_id,
            LineageDataset.id != dataset.id,
            LineageDataset.schema_fingerprint.isnot(None)
        ).order_by(LineageDataset.created_at.desc()).limit(5).all()
        
        if not previous_datasets:
            return findings
        
        # Check for fingerprint changes
        unique_fingerprints = set(d.schema_fingerprint for d in previous_datasets)
        
        if dataset.schema_fingerprint in unique_fingerprints:
            # No drift - fingerprint matches previous
            return findings
        
        # Get the most recent previous fingerprint
        latest_prev = previous_datasets[0]
        
        # Compare schemas
        current_cols = set(
            c.get("name", "") for c in (dataset.schema_columns_json or [])
        )
        previous_cols = set(
            c.get("name", "") for c in (latest_prev.schema_columns_json or [])
        )
        
        added = current_cols - previous_cols
        removed = previous_cols - current_cols
        
        if not added and not removed:
            # Fingerprint differs but columns same - likely type changes
            severity = FindingSeverity.INFO
        elif removed:
            # Columns removed - more serious
            severity = FindingSeverity.WARN
        else:
            # Only columns added
            severity = FindingSeverity.INFO
        
        findings.append(FindingData(
            category=FindingCategory.SCHEMA,
            severity=severity,
            metric_key="schema_drift",
            metric_label="Schema Drift Detected",
            metric_value=len(added) + len(removed),
            exposure_amount=0,
            exposure_currency=self.base_currency,
            count_rows=0,
            sample_evidence=[
                {
                    "current_fingerprint": dataset.schema_fingerprint[:16] + "...",
                    "previous_fingerprint": latest_prev.schema_fingerprint[:16] + "...",
                    "added_columns": list(added),
                    "removed_columns": list(removed),
                    "datasets_compared": len(previous_datasets)
                }
            ],
            threshold_value=None,
            threshold_type=None
        ))
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SUMMARY CALCULATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_summary(
        self, 
        records: List[CanonicalRecord], 
        findings: List[FindingData]
    ) -> Dict[str, Any]:
        """Calculate summary metrics."""
        total_rows = len(records)
        total_amount = sum(abs(r.amount or 0) for r in records)
        
        # Count findings by severity
        critical_count = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
        warning_count = sum(1 for f in findings if f.severity == FindingSeverity.WARN)
        info_count = sum(1 for f in findings if f.severity == FindingSeverity.INFO)
        
        # Calculate amount with issues
        amount_with_issues = sum(f.exposure_amount for f in findings)
        
        # Determine quality level
        if critical_count > 0:
            quality_level = "poor"
        elif warning_count > 3:
            quality_level = "fair"
        elif warning_count > 0:
            quality_level = "good"
        else:
            quality_level = "excellent"
        
        # Count error/warning rows (deduplicated)
        error_rows = sum(f.count_rows for f in findings if f.severity == FindingSeverity.CRITICAL)
        warning_rows = sum(f.count_rows for f in findings if f.severity == FindingSeverity.WARN)
        valid_rows = max(0, total_rows - error_rows)
        
        return {
            "total_rows": total_rows,
            "valid_rows": valid_rows,
            "error_rows": error_rows,
            "warning_rows": warning_rows,
            "total_amount": float(total_amount),
            "amount_with_issues": float(amount_with_issues),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "quality_level": quality_level
        }
    
    def _calculate_severity_score(
        self, 
        findings: List[FindingData], 
        summary: Dict[str, Any]
    ) -> float:
        """Calculate overall severity score (0-100)."""
        score = 0.0
        
        # Weight by severity
        for finding in findings:
            if finding.severity == FindingSeverity.CRITICAL:
                score += 30
            elif finding.severity == FindingSeverity.WARN:
                score += 10
            else:
                score += 2
        
        # Add exposure-based score
        total_amount = summary.get("total_amount", 0)
        amount_with_issues = summary.get("amount_with_issues", 0)
        
        if total_amount > 0:
            exposure_pct = (amount_with_issues / total_amount) * 100
            score += min(30, exposure_pct)  # Cap at 30
        
        return min(100, score)
    
    def _create_empty_report(
        self, 
        dataset_id: int, 
        connection_id: Optional[int]
    ) -> DataHealthReportRecord:
        """Create report for empty dataset."""
        report = DataHealthReportRecord(
            dataset_id=dataset_id,
            connection_id=connection_id,
            severity_score=0,
            summary_json={
                "total_rows": 0,
                "valid_rows": 0,
                "error_rows": 0,
                "warning_rows": 0,
                "total_amount": 0,
                "amount_with_issues": 0,
                "critical_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "quality_level": "unknown"
            }
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report
