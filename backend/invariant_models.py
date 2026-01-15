"""
Invariant Engine Models

Persistent storage for invariant runs and results.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text,
    CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import enum


Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantStatus(str, enum.Enum):
    """Status of an invariant result."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


class RunStatus(str, enum.Enum):
    """Status of an invariant run."""
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some passed, some failed


class InvariantSeverity(str, enum.Enum):
    """Severity of an invariant."""
    CRITICAL = "critical"  # Blocks snapshot lock
    ERROR = "error"        # Serious but can override
    WARNING = "warning"    # Informational
    INFO = "info"


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT RUN MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantRun(Base):
    """
    Record of an invariant check run on a snapshot.
    """
    __tablename__ = "invariant_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, nullable=False, index=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default=RunStatus.RUNNING.value)
    
    # Summary
    summary_json = Column(JSON, nullable=True)
    """
    {
        "total_invariants": int,
        "passed": int,
        "failed": int,
        "warnings": int,
        "skipped": int,
        "critical_failures": int,
        "execution_time_ms": float
    }
    """
    
    # Triggered by
    triggered_by = Column(String(100), nullable=True)
    
    # Relationships
    results = relationship("InvariantResult", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'passed', 'failed', 'partial')",
            name="ck_invariant_run_status"
        ),
        Index("ix_invariant_run_snapshot_created", "snapshot_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT RESULT MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class InvariantResult(Base):
    """
    Result of a single invariant check.
    """
    __tablename__ = "invariant_results"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("invariant_runs.id"), nullable=False, index=True)
    
    # Invariant identification
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Result
    status = Column(String(20), nullable=False)  # pass, fail, warn, skip
    severity = Column(String(20), nullable=False)  # critical, error, warning, info
    
    # Details
    details_json = Column(JSON, nullable=True)
    """
    {
        "checked": int,
        "violations": int,
        "tolerance": float,
        "actual_values": [...],
        "expected_values": [...],
        ...
    }
    """
    
    # Proof string (human-readable explanation)
    proof_string = Column(Text, nullable=True)
    
    # Evidence references
    evidence_refs_json = Column(JSON, nullable=True)
    """
    [
        {"type": "invoice", "id": 123, "details": {...}},
        {"type": "bank_txn", "id": 456, "details": {...}},
        ...
    ]
    """
    
    # Amount-weighted metrics
    exposure_amount = Column(Float, default=0.0)
    exposure_currency = Column(String(10), default="EUR")
    
    # Relationships
    run = relationship("InvariantRun", back_populates="results")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pass', 'fail', 'warn', 'skip')",
            name="ck_invariant_result_status"
        ),
        CheckConstraint(
            "severity IN ('critical', 'error', 'warning', 'info')",
            name="ck_invariant_result_severity"
        ),
        Index("ix_invariant_result_run_status", "run_id", "status"),
    )
