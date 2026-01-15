"""
Data Health Report Models

Persistent storage for health reports and findings per Dataset.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text,
    UniqueConstraint, CheckConstraint, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import enum


Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class FindingSeverity(str, enum.Enum):
    """Severity levels for health findings."""
    INFO = "info"          # Informational, no action needed
    WARN = "warn"          # Warning, should review
    CRITICAL = "critical"  # Critical, blocks trust certification


class FindingCategory(str, enum.Enum):
    """Categories of health findings."""
    COMPLETENESS = "completeness"      # Missing required fields
    VALIDITY = "validity"              # Invalid values
    CONSISTENCY = "consistency"        # Duplicates, conflicts
    FRESHNESS = "freshness"            # Data staleness
    SCHEMA = "schema"                  # Schema drift
    ANOMALY = "anomaly"                # Outliers, unusual patterns


# ═══════════════════════════════════════════════════════════════════════════════
# DATA HEALTH REPORT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class DataHealthReportRecord(Base):
    """
    Persisted health report for a Dataset.
    
    Generated during ingestion or on-demand.
    Contains severity score and summary metrics.
    """
    __tablename__ = "data_health_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, nullable=False, index=True)  # FK to lineage_datasets
    connection_id = Column(Integer, nullable=True, index=True)  # FK to lineage_connections
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Overall severity (0-100, higher = more severe issues)
    severity_score = Column(Float, default=0.0)
    
    # Summary metrics
    summary_json = Column(JSON, nullable=True)
    """
    {
        "total_rows": int,
        "valid_rows": int,
        "error_rows": int,
        "warning_rows": int,
        "total_amount": float,
        "amount_with_issues": float,
        "critical_count": int,
        "warning_count": int,
        "info_count": int,
        "quality_level": str
    }
    """
    
    # Schema info
    schema_fingerprint = Column(String(64), nullable=True)
    
    # Relationships
    findings = relationship("HealthFinding", back_populates="report", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_health_report_dataset", "dataset_id"),
        Index("ix_health_report_connection", "connection_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH FINDING MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class HealthFinding(Base):
    """
    Individual health finding within a report.
    
    Each finding represents a specific data quality issue
    with amount-weighted exposure metrics.
    """
    __tablename__ = "health_findings"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("data_health_reports.id"), nullable=False, index=True)
    
    # Classification
    category = Column(String(30), nullable=False)  # FindingCategory value
    severity = Column(String(20), nullable=False)  # FindingSeverity value
    
    # Metric identification
    metric_key = Column(String(100), nullable=False)  # e.g., "missing_due_date", "duplicate_canonical_id"
    metric_label = Column(String(200), nullable=True)  # Human-readable label
    
    # Metric value (primary measure)
    metric_value = Column(Float, nullable=True)  # Count or percentage
    
    # Amount-weighted exposure
    exposure_amount_base = Column(Float, default=0.0)  # Exposure in base currency
    exposure_currency = Column(String(10), default="EUR")
    
    # Affected rows
    count_rows = Column(Integer, default=0)
    
    # Sample evidence (first N affected rows)
    sample_evidence_json = Column(JSON, nullable=True)
    """
    [
        {"row_id": int, "canonical_id": str, "amount": float, "details": {...}},
        ...
    ]
    """
    
    # Threshold info (for comparison)
    threshold_value = Column(Float, nullable=True)
    threshold_type = Column(String(20), nullable=True)  # "max", "min", "range"
    
    # Relationships
    report = relationship("DataHealthReportRecord", back_populates="findings")
    
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warn', 'critical')",
            name="ck_health_finding_severity"
        ),
        CheckConstraint(
            "category IN ('completeness', 'validity', 'consistency', 'freshness', 'schema', 'anomaly')",
            name="ck_health_finding_category"
        ),
        Index("ix_health_finding_report_severity", "report_id", "severity"),
        Index("ix_health_finding_metric", "metric_key"),
    )
