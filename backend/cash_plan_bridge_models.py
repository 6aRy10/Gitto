"""
Cash-to-Plan Bridge Models

Models for bridging FP&A accrual-based plans to cash flows via working capital timing.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
    Enum as SQLEnum, JSON, Boolean, Date, Numeric
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
import enum

# Import Base from models to share metadata
from models import Base


class PlanStatus(enum.Enum):
    """Status of an FP&A plan."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    LOCKED = "locked"


class DriverType(enum.Enum):
    """Type of plan driver."""
    REVENUE = "revenue"
    COGS = "cogs"
    OPEX = "opex"
    CAPEX = "capex"
    FINANCING = "financing"
    OTHER = "other"


class BridgeLineType(enum.Enum):
    """Type of bridge line item."""
    # Accrual to Cash conversions
    REVENUE_TO_AR = "revenue_to_ar"
    AR_TO_CASH = "ar_to_cash"
    COGS_TO_AP = "cogs_to_ap"
    AP_TO_CASH = "ap_to_cash"
    OPEX_ACCRUAL = "opex_accrual"
    OPEX_TO_CASH = "opex_to_cash"
    # Working capital adjustments
    AR_TIMING_ADJUSTMENT = "ar_timing_adjustment"
    AP_TIMING_ADJUSTMENT = "ap_timing_adjustment"
    INVENTORY_CHANGE = "inventory_change"
    PREPAID_CHANGE = "prepaid_change"
    ACCRUED_LIABILITY_CHANGE = "accrued_liability_change"
    # Direct cash items
    CAPEX_CASH = "capex_cash"
    FINANCING_CASH = "financing_cash"
    TAX_PAYMENT = "tax_payment"
    # Variances
    TIMING_VARIANCE = "timing_variance"
    AMOUNT_VARIANCE = "amount_variance"
    FX_VARIANCE = "fx_variance"
    # Unknown
    UNKNOWN = "unknown"


class EvidenceType(enum.Enum):
    """Type of evidence for bridge lines."""
    INVOICE = "invoice"
    BANK_TXN = "bank_txn"
    VENDOR_BILL = "vendor_bill"
    PLAN_DRIVER = "plan_driver"
    RECONCILIATION = "reconciliation"
    FX_RATE = "fx_rate"
    NONE = "none"


class FPAPlan(Base):
    """
    Financial Planning & Analysis Plan with driver-based assumptions.
    Monthly granularity with ability to overlay on weekly liquidity.
    """
    __tablename__ = "fpa_plans"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Plan metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    plan_version = Column(String(50), default="v1")
    
    # Time range
    start_month = Column(Date, nullable=False)  # First day of start month
    end_month = Column(Date, nullable=False)    # First day of end month
    
    # Status
    status = Column(SQLEnum(PlanStatus), default=PlanStatus.DRAFT)
    
    # Currency
    base_currency = Column(String(3), default="EUR")
    
    # Assumptions JSON for flexible driver-based modeling
    assumptions_json = Column(JSON, default=dict)
    # Example: {
    #   "revenue_growth_rate": 0.05,
    #   "gross_margin": 0.65,
    #   "opex_as_pct_revenue": 0.35,
    #   "dso_days": 45,
    #   "dpo_days": 30,
    #   "min_cash_balance": 500000
    # }
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    
    # Relationships
    drivers = relationship("PlanDriver", back_populates="plan", cascade="all, delete-orphan")
    bridges = relationship("CashToPlanBridge", back_populates="plan")


class PlanDriver(Base):
    """
    Individual driver line item in an FP&A plan.
    Represents monthly accrual-based P&L or balance sheet items.
    """
    __tablename__ = "plan_drivers"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=False, index=True)
    
    # Driver identification
    driver_type = Column(SQLEnum(DriverType), nullable=False)
    category = Column(String(100), nullable=False)  # e.g., "Product Revenue", "Cloud Hosting", "Salaries"
    subcategory = Column(String(100), nullable=True)
    
    # Time period (month)
    period_month = Column(Date, nullable=False)  # First day of month
    
    # Amounts (accrual basis)
    amount_plan = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(3), default="EUR")
    
    # Working capital conversion parameters
    # For revenue: days to collect (DSO)
    days_to_cash = Column(Integer, nullable=True)  # Override plan-level assumption
    # For expenses: days to pay (DPO)
    days_to_pay = Column(Integer, nullable=True)
    
    # Cash timing distribution (for probabilistic conversion)
    # e.g., {"0-30": 0.3, "31-60": 0.5, "61-90": 0.15, "90+": 0.05}
    cash_timing_distribution = Column(JSON, nullable=True)
    
    # Driver formula/notes
    driver_formula = Column(Text, nullable=True)  # e.g., "Units * Price", "Revenue * 0.35"
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    plan = relationship("FPAPlan", back_populates="drivers")


class CashToPlanBridge(Base):
    """
    Cash-to-Plan Bridge connecting an FP&A plan to actual snapshot data.
    Shows how accrual-based plan translates to cash via working capital timing.
    """
    __tablename__ = "cash_to_plan_bridges"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fpa_plans.id"), nullable=False, index=True)
    snapshot_id = Column(Integer, nullable=False, index=True)  # Links to locked snapshot
    
    # Bridge metadata
    name = Column(String(255), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Summary metrics
    total_plan_revenue = Column(Numeric(15, 2), default=0)
    total_plan_cash_inflows = Column(Numeric(15, 2), default=0)
    total_actual_cash_inflows = Column(Numeric(15, 2), default=0)
    
    total_plan_expenses = Column(Numeric(15, 2), default=0)
    total_plan_cash_outflows = Column(Numeric(15, 2), default=0)
    total_actual_cash_outflows = Column(Numeric(15, 2), default=0)
    
    # Variance totals
    total_inflow_variance = Column(Numeric(15, 2), default=0)
    total_outflow_variance = Column(Numeric(15, 2), default=0)
    net_variance = Column(Numeric(15, 2), default=0)
    
    # Working capital bridge totals
    ar_change = Column(Numeric(15, 2), default=0)
    ap_change = Column(Numeric(15, 2), default=0)
    other_working_capital = Column(Numeric(15, 2), default=0)
    
    # Cash constraint violations
    red_weeks_count = Column(Integer, default=0)
    min_cash_violation_amount = Column(Numeric(15, 2), default=0)
    red_weeks_json = Column(JSON, default=list)  # List of week numbers/dates
    
    # Unknown/unexplained amounts
    unknown_inflows = Column(Numeric(15, 2), default=0)
    unknown_outflows = Column(Numeric(15, 2), default=0)
    
    # Full bridge output as JSON for flexible rendering
    bridge_output_json = Column(JSON, default=dict)
    
    # Weekly overlay output
    weekly_overlay_json = Column(JSON, default=list)
    
    # Currency
    base_currency = Column(String(3), default="EUR")
    
    # Relationships
    plan = relationship("FPAPlan", back_populates="bridges")
    lines = relationship("BridgeLine", back_populates="bridge", cascade="all, delete-orphan")


class BridgeLine(Base):
    """
    Individual line item in a Cash-to-Plan bridge.
    Every line must have evidence links or be marked as Unknown.
    """
    __tablename__ = "bridge_lines"

    id = Column(Integer, primary_key=True, index=True)
    bridge_id = Column(Integer, ForeignKey("cash_to_plan_bridges.id"), nullable=False, index=True)
    
    # Line identification
    line_type = Column(SQLEnum(BridgeLineType), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Time period
    period_month = Column(Date, nullable=True)  # For monthly view
    period_week = Column(Date, nullable=True)   # For weekly overlay
    week_number = Column(Integer, nullable=True)  # Week 1-13
    
    # Amounts
    plan_amount = Column(Numeric(15, 2), default=0)      # From FP&A plan (accrual)
    plan_cash_amount = Column(Numeric(15, 2), default=0) # Plan converted to cash timing
    actual_amount = Column(Numeric(15, 2), default=0)    # From snapshot (bank truth)
    variance = Column(Numeric(15, 2), default=0)         # actual - plan_cash
    
    # Currency
    currency = Column(String(3), default="EUR")
    amount_base = Column(Numeric(15, 2), default=0)  # In base currency
    
    # Working capital adjustment details
    timing_adjustment = Column(Numeric(15, 2), default=0)
    timing_days = Column(Integer, nullable=True)  # Days shift from accrual to cash
    
    # Evidence linking - CRITICAL
    has_evidence = Column(Boolean, default=False)
    evidence_type = Column(SQLEnum(EvidenceType), default=EvidenceType.NONE)
    evidence_refs_json = Column(JSON, default=list)
    # Example: [
    #   {"type": "invoice", "id": 123, "doc_number": "INV-001", "amount": 5000},
    #   {"type": "bank_txn", "id": 456, "reference": "TXN-789", "amount": 5000}
    # ]
    
    # Evidence counts
    invoice_count = Column(Integer, default=0)
    bank_txn_count = Column(Integer, default=0)
    vendor_bill_count = Column(Integer, default=0)
    
    # If no evidence, mark as unknown
    is_unknown = Column(Boolean, default=False)
    unknown_reason = Column(String(255), nullable=True)
    
    # Drill-down support
    drilldown_available = Column(Boolean, default=False)
    drilldown_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    bridge = relationship("CashToPlanBridge", back_populates="lines")


class WeeklyPlanOverlay(Base):
    """
    Weekly overlay showing plan cash flows mapped to 13-week liquidity view.
    Highlights red weeks where plan violates cash constraints.
    """
    __tablename__ = "weekly_plan_overlays"

    id = Column(Integer, primary_key=True, index=True)
    bridge_id = Column(Integer, ForeignKey("cash_to_plan_bridges.id"), nullable=False, index=True)
    
    # Week identification
    week_number = Column(Integer, nullable=False)  # 1-13
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    
    # Opening/Closing balances
    opening_balance_plan = Column(Numeric(15, 2), default=0)
    opening_balance_actual = Column(Numeric(15, 2), default=0)
    
    # Inflows
    plan_inflows = Column(Numeric(15, 2), default=0)
    actual_inflows = Column(Numeric(15, 2), default=0)
    inflow_variance = Column(Numeric(15, 2), default=0)
    
    # Outflows
    plan_outflows = Column(Numeric(15, 2), default=0)
    actual_outflows = Column(Numeric(15, 2), default=0)
    outflow_variance = Column(Numeric(15, 2), default=0)
    
    # Closing balances
    closing_balance_plan = Column(Numeric(15, 2), default=0)
    closing_balance_actual = Column(Numeric(15, 2), default=0)
    
    # Cash constraint check
    min_cash_required = Column(Numeric(15, 2), default=0)
    is_red_week = Column(Boolean, default=False)
    cash_shortfall = Column(Numeric(15, 2), default=0)  # How much below min cash
    
    # Evidence breakdown
    explained_inflows = Column(Numeric(15, 2), default=0)
    unexplained_inflows = Column(Numeric(15, 2), default=0)
    explained_outflows = Column(Numeric(15, 2), default=0)
    unexplained_outflows = Column(Numeric(15, 2), default=0)
    
    # Detailed breakdown JSON
    inflow_breakdown_json = Column(JSON, default=list)
    outflow_breakdown_json = Column(JSON, default=list)
    
    # Currency
    currency = Column(String(3), default="EUR")
