"""
External System Certification Models

Models for comparing external TMS cash positions against Gitto bank-truth totals.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, 
    Enum as SQLEnum, JSON, Boolean, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class DiscrepancyCategory(enum.Enum):
    """Categories for explaining discrepancies between external and Gitto totals."""
    UNMATCHED_BANK_TXN = "unmatched_bank_txn"
    FX_POLICY_DIFFERENCE = "fx_policy_difference"
    STALE_DATA = "stale_data"
    MAPPING_GAP = "mapping_gap"
    TIMING_DIFFERENCE = "timing_difference"
    ROUNDING = "rounding"
    UNKNOWN = "unknown"


class CertificationStatus(enum.Enum):
    """Status of a certification report."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CERTIFIED = "certified"
    REJECTED = "rejected"


class ExternalSystemImport(Base):
    """
    Represents an import of cash position data from an external TMS.
    """
    __tablename__ = "external_system_imports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    
    # Source system info
    system_name = Column(String(100), nullable=False)  # e.g., "SAP TRM", "Kyriba", "GTreasury"
    system_version = Column(String(50))
    
    # Import metadata
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64))  # SHA-256 for integrity
    imported_at = Column(DateTime, default=datetime.utcnow)
    imported_by = Column(String(100))
    
    # As-of timing
    external_as_of = Column(DateTime, nullable=False)  # When external system captured data
    gitto_as_of = Column(DateTime, nullable=False)  # Gitto snapshot timestamp for comparison
    
    # Raw data
    raw_data_json = Column(JSON)  # Original CSV parsed as JSON
    row_count = Column(Integer, default=0)
    
    # Totals from external system
    external_total_base = Column(Float, default=0.0)  # In base currency
    external_currency = Column(String(3), default="EUR")
    
    # Relationships
    positions = relationship("ExternalCashPosition", back_populates="import_record", cascade="all, delete-orphan")
    certification_reports = relationship("CertificationReport", back_populates="import_record")


class ExternalCashPosition(Base):
    """
    Individual cash position from external TMS import.
    """
    __tablename__ = "external_cash_positions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    import_id = Column(Integer, ForeignKey("external_system_imports.id"), nullable=False)
    
    # Position identification
    external_account_id = Column(String(100))  # Account ID in external system
    account_name = Column(String(255))
    bank_name = Column(String(255))
    
    # Position details
    currency = Column(String(3), nullable=False)
    amount = Column(Float, nullable=False)
    amount_base = Column(Float)  # Converted to base currency
    fx_rate_used = Column(Float)  # Rate used by external system
    
    # Mapping to Gitto
    gitto_account_id = Column(Integer, ForeignKey("bank_accounts.id"))
    is_mapped = Column(Boolean, default=False)
    mapping_confidence = Column(Float, default=0.0)
    
    # Position date
    position_date = Column(DateTime)
    value_date = Column(DateTime)
    
    # Relationship
    import_record = relationship("ExternalSystemImport", back_populates="positions")


class CertificationReport(Base):
    """
    Certification report comparing external TMS vs Gitto bank-truth totals.
    """
    __tablename__ = "certification_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    import_id = Column(Integer, ForeignKey("external_system_imports.id"), nullable=False)
    
    # Report metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    status = Column(SQLEnum(CertificationStatus), default=CertificationStatus.DRAFT)
    
    # Summary metrics
    external_total_base = Column(Float, default=0.0)
    gitto_total_base = Column(Float, default=0.0)
    gross_difference_base = Column(Float, default=0.0)
    net_difference_base = Column(Float, default=0.0)  # After explained discrepancies
    
    # Explained amounts by category
    explained_by_unmatched = Column(Float, default=0.0)
    explained_by_fx_policy = Column(Float, default=0.0)
    explained_by_stale_data = Column(Float, default=0.0)
    explained_by_mapping_gap = Column(Float, default=0.0)
    explained_by_timing = Column(Float, default=0.0)
    explained_by_rounding = Column(Float, default=0.0)
    unexplained_amount = Column(Float, default=0.0)
    
    # Certification outcome
    certification_score = Column(Float, default=0.0)  # 0-100
    is_certified = Column(Boolean, default=False)
    certified_at = Column(DateTime)
    certified_by = Column(String(100))
    certification_notes = Column(Text)
    
    # Export
    exported_at = Column(DateTime)
    export_format = Column(String(20))  # "pdf", "xlsx", "json"
    export_file_path = Column(String(500))
    
    # Relationships
    import_record = relationship("ExternalSystemImport", back_populates="certification_reports")
    discrepancies = relationship("CertificationDiscrepancy", back_populates="report", cascade="all, delete-orphan")
    account_comparisons = relationship("AccountComparison", back_populates="report", cascade="all, delete-orphan")


class CertificationDiscrepancy(Base):
    """
    Individual discrepancy between external and Gitto totals with attribution.
    """
    __tablename__ = "certification_discrepancies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("certification_reports.id"), nullable=False)
    
    # Discrepancy details
    category = Column(SQLEnum(DiscrepancyCategory), nullable=False)
    description = Column(Text)
    
    # Amounts
    amount_base = Column(Float, nullable=False)
    currency = Column(String(3))
    original_amount = Column(Float)  # In original currency
    
    # Attribution
    external_value = Column(Float)
    gitto_value = Column(Float)
    
    # Timing context
    external_as_of = Column(DateTime)
    gitto_as_of = Column(DateTime)
    
    # Evidence linking
    evidence_refs_json = Column(JSON)  # List of {type, id, description}
    
    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)
    resolved_by = Column(String(100))
    resolved_at = Column(DateTime)
    
    # Relationship
    report = relationship("CertificationReport", back_populates="discrepancies")


class AccountComparison(Base):
    """
    Per-account comparison between external position and Gitto balance.
    """
    __tablename__ = "certification_account_comparisons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("certification_reports.id"), nullable=False)
    
    # External account info
    external_account_id = Column(String(100))
    external_account_name = Column(String(255))
    external_amount = Column(Float)
    external_currency = Column(String(3))
    external_amount_base = Column(Float)
    
    # Gitto account info
    gitto_account_id = Column(Integer, ForeignKey("bank_accounts.id"))
    gitto_account_name = Column(String(255))
    gitto_amount = Column(Float)
    gitto_amount_base = Column(Float)
    
    # Comparison
    difference_base = Column(Float)
    difference_pct = Column(Float)
    is_matched = Column(Boolean, default=False)
    match_confidence = Column(Float, default=0.0)
    
    # Attribution summary
    primary_discrepancy_category = Column(SQLEnum(DiscrepancyCategory))
    
    # Relationship
    report = relationship("CertificationReport", back_populates="account_comparisons")
