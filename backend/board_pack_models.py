"""
Board Pack Autopilot Models

Generates a 10-slide-equivalent report from snapshot + plan outputs.
All numbers deterministically derived. Narrative describes computed results only.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
    Enum as SQLEnum, JSON, Boolean, Date, Numeric
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from models import Base


class BoardPackStatus(enum.Enum):
    """Status of a board pack."""
    DRAFT = "draft"
    REVIEW = "review"
    PENDING_SIGNOFF = "pending_signoff"
    SIGNED_OFF = "signed_off"
    ARCHIVED = "archived"


class SlideType(enum.Enum):
    """Types of slides in the board pack."""
    COVER = "cover"
    EXECUTIVE_SUMMARY = "executive_summary"
    KEY_HIGHLIGHTS = "key_highlights"
    RUNWAY_ANALYSIS = "runway_analysis"
    FORECAST_VS_ACTUAL = "forecast_vs_actual"
    REVENUE_DRIVERS = "revenue_drivers"
    EXPENSE_DRIVERS = "expense_drivers"
    RISKS_MITIGATIONS = "risks_mitigations"
    ACTION_PLAN = "action_plan"
    APPENDIX = "appendix"


class RiskSeverity(enum.Enum):
    """Severity of identified risks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BoardPack(Base):
    """
    Board Pack - a 10-slide report for board/investor meetings.
    All data derived deterministically from snapshot + plan.
    """
    __tablename__ = "board_packs"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Source data references
    snapshot_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=True, index=True)  # Optional planning scenario
    
    # Comparison reference (last month's pack for variance)
    previous_pack_id = Column(Integer, ForeignKey("board_packs.id"), nullable=True)
    
    # Pack metadata
    title = Column(String(255), nullable=False)
    period_label = Column(String(50), nullable=False)  # e.g., "January 2026"
    as_of_date = Column(Date, nullable=False)
    
    # Status
    status = Column(SQLEnum(BoardPackStatus), default=BoardPackStatus.DRAFT)
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String(100), nullable=True)
    
    # CFO Sign-off
    signed_off_at = Column(DateTime, nullable=True)
    signed_off_by = Column(String(100), nullable=True)
    signoff_statement = Column(Text, nullable=True)  # Required acknowledgment
    
    # Computed summary metrics (for quick access)
    runway_months = Column(Integer, default=0)
    ending_cash = Column(Numeric(15, 2), default=0)
    ending_arr = Column(Numeric(15, 2), default=0)
    monthly_burn = Column(Numeric(15, 2), default=0)
    headcount = Column(Integer, default=0)
    
    # Month-over-month changes
    arr_change_pct = Column(Numeric(5, 2), default=0)
    burn_change_pct = Column(Numeric(5, 2), default=0)
    runway_change_months = Column(Integer, default=0)
    
    # Risk summary
    critical_risks_count = Column(Integer, default=0)
    high_risks_count = Column(Integer, default=0)
    
    # Full pack data as JSON
    pack_data_json = Column(JSON, default=dict)
    
    # Currency
    base_currency = Column(String(3), default="USD")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    slides = relationship("BoardPackSlide", back_populates="pack", cascade="all, delete-orphan")
    risks = relationship("BoardPackRisk", back_populates="pack", cascade="all, delete-orphan")
    actions = relationship("BoardPackAction", back_populates="pack", cascade="all, delete-orphan")
    audit_logs = relationship("BoardPackAuditLog", back_populates="pack", cascade="all, delete-orphan")


class BoardPackSlide(Base):
    """
    Individual slide in a board pack.
    Contains deterministically computed content only.
    """
    __tablename__ = "board_pack_slides"

    id = Column(Integer, primary_key=True, index=True)
    pack_id = Column(Integer, ForeignKey("board_packs.id"), nullable=False, index=True)
    
    # Slide metadata
    slide_number = Column(Integer, nullable=False)
    slide_type = Column(SQLEnum(SlideType), nullable=False)
    title = Column(String(255), nullable=False)
    
    # Content
    headline = Column(Text, nullable=True)  # Key message (derived from data)
    narrative = Column(Text, nullable=True)  # Descriptive text (describes computed results)
    
    # Structured data for the slide
    metrics_json = Column(JSON, default=list)
    # Structure: [{"label": "ARR", "value": 1200000, "change": 50000, "change_pct": 4.3}, ...]
    
    charts_json = Column(JSON, default=list)
    # Structure: [{"type": "bar", "title": "Monthly Revenue", "data": [...]}]
    
    tables_json = Column(JSON, default=list)
    # Structure: [{"title": "Top Customers", "headers": [...], "rows": [...]}]
    
    bullets_json = Column(JSON, default=list)
    # Structure: [{"text": "Revenue grew 15%", "source": "computed from MRR"}]
    
    # Evidence linking (which data produced this slide)
    evidence_refs_json = Column(JSON, default=list)
    
    # Relationship
    pack = relationship("BoardPack", back_populates="slides")


class BoardPackRisk(Base):
    """
    Risk identified from data analysis.
    All risks derived from computed thresholds, not subjective assessment.
    """
    __tablename__ = "board_pack_risks"

    id = Column(Integer, primary_key=True, index=True)
    pack_id = Column(Integer, ForeignKey("board_packs.id"), nullable=False, index=True)
    
    # Risk details
    risk_title = Column(String(255), nullable=False)
    risk_description = Column(Text, nullable=False)
    severity = Column(SQLEnum(RiskSeverity), nullable=False)
    
    # Quantification (all derived from data)
    exposure_amount = Column(Numeric(15, 2), default=0)
    probability_pct = Column(Numeric(5, 2), nullable=True)  # If calculable
    
    # How this risk was detected
    detection_method = Column(String(255), nullable=False)
    threshold_breached = Column(String(255), nullable=True)
    
    # Mitigation
    mitigation = Column(Text, nullable=True)
    mitigation_owner = Column(String(100), nullable=True)
    mitigation_deadline = Column(Date, nullable=True)
    
    # Evidence
    evidence_refs_json = Column(JSON, default=list)
    
    # Relationship
    pack = relationship("BoardPack", back_populates="risks")


class BoardPackAction(Base):
    """
    Action items derived from analysis.
    """
    __tablename__ = "board_pack_actions"

    id = Column(Integer, primary_key=True, index=True)
    pack_id = Column(Integer, ForeignKey("board_packs.id"), nullable=False, index=True)
    
    # Action details
    action_title = Column(String(255), nullable=False)
    action_description = Column(Text, nullable=True)
    
    # Assignment
    owner = Column(String(100), nullable=True)
    deadline = Column(Date, nullable=True)
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Status
    status = Column(String(20), default="open")  # open, in_progress, completed
    
    # Link to what triggered this action
    triggered_by = Column(String(255), nullable=True)  # e.g., "Runway < 12 months"
    
    # Relationship
    pack = relationship("BoardPack", back_populates="actions")


class BoardPackAuditLog(Base):
    """
    Audit log for board pack changes and sign-offs.
    """
    __tablename__ = "board_pack_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    pack_id = Column(Integer, ForeignKey("board_packs.id"), nullable=False, index=True)
    
    # Audit details
    action = Column(String(50), nullable=False)  # created, updated, signed_off, etc.
    actor = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Details
    details_json = Column(JSON, default=dict)
    
    # For sign-off audits
    signoff_statement = Column(Text, nullable=True)
    
    # IP/Session for security audit
    ip_address = Column(String(50), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Relationship
    pack = relationship("BoardPack", back_populates="audit_logs")
