"""
Trust Report Models

Persistent storage for trust reports, metrics, and lock gate results.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text,
    Boolean, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import enum


Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class MetricUnit(str, enum.Enum):
    """Unit types for trust metrics."""
    PERCENT = "percent"
    CURRENCY = "currency"
    HOURS = "hours"
    COUNT = "count"
    BOOLEAN = "boolean"
    RATIO = "ratio"


class LockGateStatus(str, enum.Enum):
    """Status of a lock gate check."""
    PASSED = "passed"
    FAILED = "failed"
    OVERRIDDEN = "overridden"


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST REPORT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class TrustReport(Base):
    """
    Trust certification report for a snapshot.
    """
    __tablename__ = "trust_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, nullable=False, index=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Overall trust score (0-100)
    trust_score = Column(Float, default=0.0)
    
    # Lock eligibility
    lock_eligible = Column(Boolean, default=False)
    
    # Gate failures
    gate_failures_json = Column(JSON, nullable=True)
    """
    [
        {
            "gate": "missing_fx_exposure",
            "threshold": 0.01,
            "actual": 0.05,
            "exposure": 50000.00,
            "status": "failed"
        },
        ...
    ]
    """
    
    # Computed metrics summary
    metrics_json = Column(JSON, nullable=True)
    """
    {
        "cash_explained_pct": 95.2,
        "unknown_exposure_base": 15000.00,
        "missing_fx_exposure_base": 5000.00,
        "total_forecasted_amount": 1000000.00,
        ...
    }
    """
    
    # Configuration used
    config_json = Column(JSON, nullable=True)
    """
    {
        "base_currency": "EUR",
        "missing_fx_threshold_pct": 0.01,
        "unexplained_cash_threshold_pct": 0.05,
        ...
    }
    """
    
    # Relationships
    metrics = relationship("TrustMetric", back_populates="report", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_trust_report_snapshot_created", "snapshot_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST METRIC MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class TrustMetric(Base):
    """
    Individual trust metric within a report.
    """
    __tablename__ = "trust_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("trust_reports.id"), nullable=False, index=True)
    
    # Metric identification
    key = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Value
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # percent, currency, hours, count, boolean
    
    # Amount-weighted exposure
    exposure_amount_base = Column(Float, default=0.0)
    
    # Trend (change from previous report)
    trend_delta = Column(Float, nullable=True)
    trend_direction = Column(String(10), nullable=True)  # up, down, stable
    
    # Evidence references for drilldown
    evidence_refs_json = Column(JSON, nullable=True)
    """
    [
        {"type": "invoice", "id": 123, "amount": 5000.00, "description": "..."},
        {"type": "bank_txn", "id": 456, "amount": 3000.00, "description": "..."},
        {"type": "dataset", "id": "ds_abc123", "rows": 100},
        ...
    ]
    """
    
    # Breakdown by segment (optional)
    breakdown_json = Column(JSON, nullable=True)
    """
    {
        "by_currency": {"GBP": 5000, "USD": 3000},
        "by_customer": {"ACME": 4000, "BETA": 4000},
        ...
    }
    """
    
    # Relationships
    report = relationship("TrustReport", back_populates="metrics")
    
    __table_args__ = (
        CheckConstraint(
            "unit IN ('percent', 'currency', 'hours', 'count', 'boolean', 'ratio')",
            name="ck_trust_metric_unit"
        ),
        Index("ix_trust_metric_report_key", "report_id", "key"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LOCK GATE OVERRIDE LOG
# ═══════════════════════════════════════════════════════════════════════════════

class LockGateOverrideLog(Base):
    """
    Audit log for CFO overrides of lock gates.
    """
    __tablename__ = "lock_gate_override_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, nullable=False, index=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # User who performed override
    user_id = Column(String(100), nullable=False)
    user_email = Column(String(200), nullable=True)
    user_role = Column(String(50), nullable=True)
    
    # Override details
    acknowledgment_text = Column(Text, nullable=False)
    
    # Failed gates that were overridden
    failed_gates_json = Column(JSON, nullable=False)
    """
    [
        {
            "gate": "missing_fx_exposure",
            "threshold": 0.01,
            "actual": 0.05,
            "exposure": 50000.00
        },
        ...
    ]
    """
    
    # Additional context
    override_reason = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    __table_args__ = (
        Index("ix_lock_gate_override_snapshot", "snapshot_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LOCK GATE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class LockGateConfig(Base):
    """
    Configurable lock gate thresholds per entity.
    """
    __tablename__ = "lock_gate_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, nullable=False, unique=True, index=True)
    
    # Thresholds
    missing_fx_threshold_pct = Column(Float, default=0.01)  # 1% of forecasted
    unexplained_cash_threshold_pct = Column(Float, default=0.05)  # 5%
    duplicate_exposure_threshold = Column(Float, default=0.0)  # 0 = no duplicates
    freshness_mismatch_hours = Column(Float, default=72.0)  # 3 days
    
    # Critical findings policy
    require_critical_findings_resolved = Column(Boolean, default=True)
    allow_cfo_override = Column(Boolean, default=True)
    
    # Updated at
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(String(100), nullable=True)
