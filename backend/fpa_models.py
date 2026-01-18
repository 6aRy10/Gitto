"""
Versioned FP&A Models

SQLAlchemy models for financial planning and analysis with full versioning,
audit logging, and reproducibility guarantees.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
import json

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text, 
    ForeignKey, Numeric, JSON, Enum as SQLEnum, Index, CheckConstraint,
    event
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# =============================================================================
# ENUMS
# =============================================================================

class PlanStatus(str, Enum):
    """Status of a planning cycle"""
    DRAFT = "draft"
    ACTIVE = "active"
    LOCKED = "locked"
    ARCHIVED = "archived"


class DriverSource(str, Enum):
    """Source of a driver value"""
    MANUAL = "manual"        # User entered
    IMPORTED = "imported"    # From external system
    DERIVED = "derived"      # Calculated from other drivers


class ScenarioStatus(str, Enum):
    """Status of a scenario"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


class VarianceCategory(str, Enum):
    """Categories for variance analysis"""
    TIMING = "timing"          # Same item, different period
    VOLUME = "volume"          # Count/quantity differences
    PRICE_RATE = "price_rate"  # Unit price or FX changes
    MIX = "mix"               # Composition shift
    ONE_TIME = "one_time"     # Non-recurring
    ERROR = "error"           # Data quality issues


# =============================================================================
# CORE MODELS
# =============================================================================

class Plan(Base):
    """
    A planning cycle container.
    
    Plans are the top-level object that contains assumption versions,
    forecasts, and scenarios for a specific time period.
    """
    __tablename__ = "fpa_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.DRAFT, nullable=False)
    
    # Configuration
    base_currency = Column(String(3), default="EUR", nullable=False)
    fiscal_year_start_month = Column(Integer, default=1, nullable=False)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    assumption_sets = relationship("AssumptionSet", back_populates="plan", cascade="all, delete-orphan")
    forecast_runs = relationship("ForecastRun", back_populates="plan", cascade="all, delete-orphan")
    scenarios = relationship("Scenario", back_populates="plan", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('period_end > period_start', name='check_period_valid'),
        CheckConstraint('fiscal_year_start_month >= 1 AND fiscal_year_start_month <= 12', name='check_fiscal_month'),
        Index('ix_fpa_plans_entity_status', 'entity_id', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "name": self.name,
            "description": self.description,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "status": self.status.value if self.status else None,
            "base_currency": self.base_currency,
            "fiscal_year_start_month": self.fiscal_year_start_month,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class AssumptionSet(Base):
    """
    A versioned set of assumptions for a plan.
    
    Each assumption set is immutable once created. New versions
    are created to make changes, preserving full history.
    """
    __tablename__ = "fpa_assumption_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=False, index=True)
    
    version = Column(Integer, nullable=False)
    version_label = Column(String(100), nullable=True)  # e.g., "Q1 Budget", "March Reforecast"
    
    notes = Column(Text, nullable=True)
    
    # Parent version for tracking lineage
    parent_version_id = Column(Integer, ForeignKey("fpa_assumption_sets.id"), nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    plan = relationship("Plan", back_populates="assumption_sets")
    drivers = relationship("Driver", back_populates="assumption_set", cascade="all, delete-orphan")
    forecast_runs = relationship("ForecastRun", back_populates="assumption_set")
    parent_version = relationship("AssumptionSet", remote_side=[id])
    
    # Constraints
    __table_args__ = (
        Index('ix_fpa_assumption_sets_plan_version', 'plan_id', 'version', unique=True),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "version": self.version,
            "version_label": self.version_label,
            "notes": self.notes,
            "parent_version_id": self.parent_version_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "driver_count": len(self.drivers) if self.drivers else 0,
        }


class Driver(Base):
    """
    An individual assumption/driver value.
    
    Drivers are the inputs to the FP&A model. They can be
    manually entered, imported from systems, or derived from calculations.
    """
    __tablename__ = "fpa_drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    assumption_set_id = Column(Integer, ForeignKey("fpa_assumption_sets.id"), nullable=False, index=True)
    
    # Driver identification
    key = Column(String(100), nullable=False)  # e.g., "headcount_engineering", "revenue_growth_pct"
    category = Column(String(50), nullable=True)  # e.g., "headcount", "revenue", "expense"
    subcategory = Column(String(50), nullable=True)
    
    # Value
    value = Column(Numeric(20, 6), nullable=False)
    unit = Column(String(20), nullable=True)  # e.g., "count", "percent", "EUR", "months"
    
    # Temporal
    effective_month = Column(Date, nullable=True)  # For time-varying drivers
    
    # Source tracking
    source = Column(SQLEnum(DriverSource), default=DriverSource.MANUAL, nullable=False)
    source_system = Column(String(100), nullable=True)  # e.g., "BambooHR", "Salesforce"
    
    # Evidence/lineage
    evidence_refs_json = Column(JSON, nullable=True)  # Links to source data
    
    # Metadata
    description = Column(Text, nullable=True)
    
    # Relationships
    assumption_set = relationship("AssumptionSet", back_populates="drivers")
    
    # Constraints
    __table_args__ = (
        Index('ix_fpa_drivers_set_key', 'assumption_set_id', 'key'),
        Index('ix_fpa_drivers_category', 'category', 'subcategory'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "assumption_set_id": self.assumption_set_id,
            "key": self.key,
            "category": self.category,
            "subcategory": self.subcategory,
            "value": str(self.value) if self.value is not None else None,
            "unit": self.unit,
            "effective_month": self.effective_month.isoformat() if self.effective_month else None,
            "source": self.source.value if self.source else None,
            "source_system": self.source_system,
            "evidence_refs_json": self.evidence_refs_json,
            "description": self.description,
        }


class ActualsSnapshot(Base):
    """
    An immutable snapshot of actual financial data.
    
    Once locked, this snapshot cannot be modified. All forecasts
    that use this snapshot will produce the same outputs.
    """
    __tablename__ = "fpa_actuals_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Period
    period_month = Column(Date, nullable=False)  # First day of month
    period_label = Column(String(50), nullable=True)  # e.g., "January 2026"
    
    # Source data
    source_dataset_id = Column(Integer, nullable=True)  # Link to Dataset from lineage
    gl_data_json = Column(JSON, nullable=True)  # General ledger lines
    ar_aggregates_json = Column(JSON, nullable=True)  # AR summary
    ap_aggregates_json = Column(JSON, nullable=True)  # AP summary
    bank_data_json = Column(JSON, nullable=True)  # Bank balances
    
    # Computed aggregates (stored for reproducibility)
    revenue_total = Column(Numeric(20, 2), nullable=True)
    cogs_total = Column(Numeric(20, 2), nullable=True)
    opex_total = Column(Numeric(20, 2), nullable=True)
    cash_ending = Column(Numeric(20, 2), nullable=True)
    
    # Lock status
    locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(100), nullable=True)
    lock_reason = Column(Text, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    forecast_runs = relationship("ForecastRun", back_populates="actuals_snapshot")
    
    # Constraints
    __table_args__ = (
        Index('ix_fpa_actuals_entity_period', 'entity_id', 'period_month', unique=True),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "period_month": self.period_month.isoformat() if self.period_month else None,
            "period_label": self.period_label,
            "source_dataset_id": self.source_dataset_id,
            "revenue_total": str(self.revenue_total) if self.revenue_total else None,
            "cogs_total": str(self.cogs_total) if self.cogs_total else None,
            "opex_total": str(self.opex_total) if self.opex_total else None,
            "cash_ending": str(self.cash_ending) if self.cash_ending else None,
            "locked": self.locked,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "locked_by": self.locked_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ForecastRun(Base):
    """
    A reproducible forecast computation.
    
    Given the same actuals_snapshot + assumption_set, the forecast
    must produce identical outputs. This is the key invariant.
    """
    __tablename__ = "fpa_forecast_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Inputs (deterministic)
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=False, index=True)
    assumption_set_id = Column(Integer, ForeignKey("fpa_assumption_sets.id"), nullable=False)
    actuals_snapshot_id = Column(Integer, ForeignKey("fpa_actuals_snapshots.id"), nullable=True)
    
    # Run metadata
    run_label = Column(String(100), nullable=True)
    forecast_horizon_months = Column(Integer, default=12, nullable=False)
    
    # Outputs (JSON for flexibility, but with defined schema)
    outputs_json = Column(JSON, nullable=True)  # P&L, Cash, etc.
    metrics_json = Column(JSON, nullable=True)  # KPIs, aggregates
    
    # Computed summary fields (for quick access)
    total_revenue = Column(Numeric(20, 2), nullable=True)
    total_ebitda = Column(Numeric(20, 2), nullable=True)
    ending_cash = Column(Numeric(20, 2), nullable=True)
    runway_months = Column(Integer, nullable=True)
    
    # Validation
    outputs_hash = Column(String(64), nullable=True)  # SHA256 of outputs for integrity
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    compute_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    plan = relationship("Plan", back_populates="forecast_runs")
    assumption_set = relationship("AssumptionSet", back_populates="forecast_runs")
    actuals_snapshot = relationship("ActualsSnapshot", back_populates="forecast_runs")
    
    # Constraints
    __table_args__ = (
        Index('ix_fpa_forecast_inputs', 'assumption_set_id', 'actuals_snapshot_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "assumption_set_id": self.assumption_set_id,
            "actuals_snapshot_id": self.actuals_snapshot_id,
            "run_label": self.run_label,
            "forecast_horizon_months": self.forecast_horizon_months,
            "outputs_json": self.outputs_json,
            "metrics_json": self.metrics_json,
            "total_revenue": str(self.total_revenue) if self.total_revenue else None,
            "total_ebitda": str(self.total_ebitda) if self.total_ebitda else None,
            "ending_cash": str(self.ending_cash) if self.ending_cash else None,
            "runway_months": self.runway_months,
            "outputs_hash": self.outputs_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "compute_time_ms": self.compute_time_ms,
        }


class Scenario(Base):
    """
    A what-if scenario branching from a base assumption set.
    
    Scenarios allow exploring alternatives without modifying
    the base plan.
    """
    __tablename__ = "fpa_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=False, index=True)
    base_assumption_set_id = Column(Integer, ForeignKey("fpa_assumption_sets.id"), nullable=False)
    
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    status = Column(SQLEnum(ScenarioStatus), default=ScenarioStatus.DRAFT, nullable=False)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    # Relationships
    plan = relationship("Plan", back_populates="scenarios")
    base_assumption_set = relationship("AssumptionSet")
    diffs = relationship("ScenarioDiff", back_populates="scenario", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "base_assumption_set_id": self.base_assumption_set_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
        }


class ScenarioDiff(Base):
    """
    Differences between a scenario and its base.
    
    Stores the delta in drivers and the computed impact.
    """
    __tablename__ = "fpa_scenario_diffs"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("fpa_scenarios.id"), nullable=False, index=True)
    
    # The differences
    diff_json = Column(JSON, nullable=False)  # {driver_key: {old: x, new: y}}
    
    # Computed impact
    impact_summary_json = Column(JSON, nullable=True)  # Revenue impact, EBITDA impact, etc.
    
    # Forecast run for this scenario (if computed)
    forecast_run_id = Column(Integer, ForeignKey("fpa_forecast_runs.id"), nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    scenario = relationship("Scenario", back_populates="diffs")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "diff_json": self.diff_json,
            "impact_summary_json": self.impact_summary_json,
            "forecast_run_id": self.forecast_run_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# ARTIFACT MODELS
# =============================================================================

class FPAArtifact(Base):
    """
    Output artifacts from FP&A workflows.
    
    Briefings, packs, and reports are stored as artifacts with
    full evidence references.
    """
    __tablename__ = "fpa_artifacts"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    artifact_type = Column(String(50), nullable=False)  # "morning_briefing", "weekly_pack", "monthly_pack"
    artifact_date = Column(Date, nullable=False)
    
    # Source data references
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=True)
    forecast_run_id = Column(Integer, ForeignKey("fpa_forecast_runs.id"), nullable=True)
    actuals_snapshot_id = Column(Integer, ForeignKey("fpa_actuals_snapshots.id"), nullable=True)
    
    # Content
    content_json = Column(JSON, nullable=False)  # Structured content
    evidence_refs_json = Column(JSON, nullable=True)  # Links to source data
    
    # Narrative (generated separately)
    narrative_text = Column(Text, nullable=True)
    narrative_generated_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default="draft", nullable=False)  # draft, final, superseded
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('ix_fpa_artifacts_entity_type_date', 'entity_id', 'artifact_type', 'artifact_date'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "artifact_type": self.artifact_type,
            "artifact_date": self.artifact_date.isoformat() if self.artifact_date else None,
            "plan_id": self.plan_id,
            "forecast_run_id": self.forecast_run_id,
            "actuals_snapshot_id": self.actuals_snapshot_id,
            "content_json": self.content_json,
            "evidence_refs_json": self.evidence_refs_json,
            "narrative_text": self.narrative_text,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# DECISION MODELS
# =============================================================================

class FPADecision(Base):
    """
    A decision requiring review/approval.
    
    Created by workflows when actions require human judgment.
    """
    __tablename__ = "fpa_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Classification
    severity = Column(String(20), nullable=False)  # "critical", "high", "medium", "low"
    decision_type = Column(String(50), nullable=False)  # "forecast_approval", "assumption_change", etc.
    
    # Content
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Options
    options_json = Column(JSON, nullable=False)  # Available choices
    recommended_option = Column(String(100), nullable=True)
    recommendation_reasoning = Column(Text, nullable=True)
    
    # Policy context
    requires_approval = Column(Boolean, default=True, nullable=False)
    policy_snapshot_json = Column(JSON, nullable=True)  # Policy state at creation
    
    # Evidence
    evidence_refs_json = Column(JSON, nullable=True)
    
    # Related objects
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=True)
    forecast_run_id = Column(Integer, ForeignKey("fpa_forecast_runs.id"), nullable=True)
    artifact_id = Column(Integer, ForeignKey("fpa_artifacts.id"), nullable=True)
    
    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, approved, rejected, auto_approved
    
    # Timing
    expires_at = Column(DateTime, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    approvals = relationship("FPAApproval", back_populates="decision", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_fpa_decisions_entity_status', 'entity_id', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "severity": self.severity,
            "decision_type": self.decision_type,
            "title": self.title,
            "description": self.description,
            "options_json": self.options_json,
            "recommended_option": self.recommended_option,
            "recommendation_reasoning": self.recommendation_reasoning,
            "requires_approval": self.requires_approval,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class FPAApproval(Base):
    """
    An approval/rejection action on a decision.
    """
    __tablename__ = "fpa_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(Integer, ForeignKey("fpa_decisions.id"), nullable=False, index=True)
    
    user_id = Column(String(100), nullable=False)
    option_selected = Column(String(100), nullable=False)
    note = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    decision = relationship("FPADecision", back_populates="approvals")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "user_id": self.user_id,
            "option_selected": self.option_selected,
            "note": self.note,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# VARIANCE MODELS
# =============================================================================

class VarianceReport(Base):
    """
    A variance analysis report comparing two data points.
    """
    __tablename__ = "fpa_variance_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Comparison type
    comparison_type = Column(String(50), nullable=False)  # "actual_vs_plan", "actual_vs_forecast", "forecast_vs_forecast"
    
    # Sources
    source_a_type = Column(String(50), nullable=False)
    source_a_id = Column(Integer, nullable=False)
    source_b_type = Column(String(50), nullable=False)
    source_b_id = Column(Integer, nullable=False)
    
    # Results
    variance_items_json = Column(JSON, nullable=False)  # List of variances with categories
    root_causes_json = Column(JSON, nullable=True)  # Root cause analysis
    talking_points_json = Column(JSON, nullable=True)  # Bullet points (not prose)
    
    # Summary
    total_variance = Column(Numeric(20, 2), nullable=True)
    variance_by_category_json = Column(JSON, nullable=True)
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "comparison_type": self.comparison_type,
            "source_a_type": self.source_a_type,
            "source_a_id": self.source_a_id,
            "source_b_type": self.source_b_type,
            "source_b_id": self.source_b_id,
            "variance_items_json": self.variance_items_json,
            "root_causes_json": self.root_causes_json,
            "talking_points_json": self.talking_points_json,
            "total_variance": str(self.total_variance) if self.total_variance else None,
            "variance_by_category_json": self.variance_by_category_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# =============================================================================
# AUDIT LOG MODEL
# =============================================================================

class FPAAuditLog(Base):
    """
    Comprehensive audit log for all FP&A operations.
    """
    __tablename__ = "fpa_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Action
    action = Column(String(50), nullable=False)  # "create", "update", "lock", "approve", etc.
    resource_type = Column(String(50), nullable=False)  # "plan", "assumption_set", "forecast_run", etc.
    resource_id = Column(Integer, nullable=True)
    
    # Details
    details_json = Column(JSON, nullable=True)
    
    # User
    user_id = Column(String(100), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('ix_fpa_audit_resource', 'resource_type', 'resource_id'),
    )


# =============================================================================
# EVENT LISTENERS FOR AUDIT LOGGING
# =============================================================================

def log_fpa_change(mapper, connection, target, action):
    """Create audit log entry for FPA model changes"""
    from sqlalchemy.orm import object_session
    
    session = object_session(target)
    if session is None:
        return
    
    # Determine resource type from table name
    resource_type = target.__tablename__.replace('fpa_', '')
    
    # Create audit entry
    audit_entry = FPAAuditLog(
        entity_id=getattr(target, 'entity_id', None) or getattr(target, 'plan_id', None) or 0,
        action=action,
        resource_type=resource_type,
        resource_id=target.id if hasattr(target, 'id') else None,
        details_json={"action": action},
        user_id=getattr(target, 'created_by', None) or getattr(target, 'locked_by', None),
    )
    session.add(audit_entry)


# Register event listeners
for model_class in [Plan, AssumptionSet, Driver, ActualsSnapshot, ForecastRun, Scenario, ScenarioDiff]:
    event.listen(model_class, 'after_insert', lambda m, c, t: log_fpa_change(m, c, t, 'create'))
    event.listen(model_class, 'after_update', lambda m, c, t: log_fpa_change(m, c, t, 'update'))
