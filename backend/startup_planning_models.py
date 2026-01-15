"""
Startup/Midmarket Driver-Based Planning Models

Opinionated planning module with specific drivers:
- Headcount & Compensation
- SaaS Revenue (growth, churn, CAC)
- Payment Terms (DSO/DPO)
- Vendor Commitments

Outputs: P&L, Cashflow Bridge, Runway, Hiring Capacity
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
    Enum as SQLEnum, JSON, Boolean, Date, Numeric, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from decimal import Decimal
import enum

from models import Base


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class PlanningScenarioStatus(enum.Enum):
    """Status of a planning scenario."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Department(enum.Enum):
    """Standard startup departments."""
    ENGINEERING = "engineering"
    PRODUCT = "product"
    SALES = "sales"
    MARKETING = "marketing"
    CUSTOMER_SUCCESS = "customer_success"
    G_AND_A = "g_and_a"  # General & Administrative
    OPERATIONS = "operations"
    EXECUTIVE = "executive"


class RevenueType(enum.Enum):
    """Revenue stream types."""
    MRR = "mrr"  # Monthly Recurring Revenue
    ARR = "arr"  # Annual Recurring Revenue
    SERVICES = "services"
    ONE_TIME = "one_time"


class ExpenseCategory(enum.Enum):
    """Expense categories."""
    PAYROLL = "payroll"
    BENEFITS = "benefits"
    SAAS_TOOLS = "saas_tools"
    INFRASTRUCTURE = "infrastructure"
    MARKETING_SPEND = "marketing_spend"
    OFFICE = "office"
    LEGAL_ACCOUNTING = "legal_accounting"
    TRAVEL = "travel"
    OTHER = "other"


# ═══════════════════════════════════════════════════════════════════════════════
# CORE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class StartupPlanningScenario(Base):
    """
    A planning scenario - either base plan or a branch.
    Scenarios are versioned and linked to snapshots for audit.
    """
    __tablename__ = "startup_planning_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)
    
    # Scenario identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    
    # Branching
    is_base = Column(Boolean, default=False)  # True if this is the base scenario
    parent_scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=True)
    branch_reason = Column(Text, nullable=True)  # Why this branch was created
    
    # Time range
    start_month = Column(Date, nullable=False)
    end_month = Column(Date, nullable=False)
    
    # Status and approval
    status = Column(SQLEnum(PlanningScenarioStatus), default=PlanningScenarioStatus.DRAFT)
    
    # Approval workflow
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(100), nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Link to snapshot for audit trail
    snapshot_id = Column(Integer, nullable=True)  # Locked snapshot this was approved against
    
    # Currency
    base_currency = Column(String(3), default="USD")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assumptions = relationship("PlanningAssumptions", back_populates="scenario", uselist=False, cascade="all, delete-orphan")
    headcount_plan = relationship("HeadcountPlan", back_populates="scenario", cascade="all, delete-orphan")
    revenue_drivers = relationship("SaaSRevenueDriver", back_populates="scenario", cascade="all, delete-orphan")
    vendor_commitments = relationship("VendorCommitment", back_populates="scenario", cascade="all, delete-orphan")
    outputs = relationship("PlanningOutput", back_populates="scenario", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('entity_id', 'name', 'version', name='uq_scenario_entity_name_version'),
    )


class PlanningAssumptions(Base):
    """
    Versioned assumptions object linked to a scenario.
    Contains all the driver inputs in a structured format.
    """
    __tablename__ = "planning_assumptions"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False, unique=True)
    
    # Version tracking
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # ═══════════════════════════════════════════════════════════════════
    # REVENUE ASSUMPTIONS
    # ═══════════════════════════════════════════════════════════════════
    
    # Starting MRR
    starting_mrr = Column(Numeric(15, 2), default=0)
    
    # Growth rates (monthly)
    mrr_growth_rate_pct = Column(Numeric(5, 2), default=5.0)  # 5% monthly
    
    # Churn
    monthly_churn_rate_pct = Column(Numeric(5, 2), default=2.0)  # 2% monthly
    
    # Customer metrics
    average_contract_value = Column(Numeric(15, 2), default=0)  # ACV
    customer_acquisition_cost = Column(Numeric(15, 2), default=0)  # CAC
    ltv_to_cac_target = Column(Numeric(5, 2), default=3.0)  # Target LTV:CAC ratio
    
    # ═══════════════════════════════════════════════════════════════════
    # COMPENSATION ASSUMPTIONS
    # ═══════════════════════════════════════════════════════════════════
    
    # Benefits as % of salary
    benefits_pct_of_salary = Column(Numeric(5, 2), default=25.0)  # 25%
    
    # Payroll taxes as % of salary
    payroll_tax_pct = Column(Numeric(5, 2), default=10.0)  # 10%
    
    # Annual salary increase %
    annual_raise_pct = Column(Numeric(5, 2), default=3.0)  # 3%
    
    # Average salaries by department (JSON for flexibility)
    avg_salaries_by_dept_json = Column(JSON, default=dict)
    # Example: {"engineering": 150000, "sales": 120000, ...}
    
    # ═══════════════════════════════════════════════════════════════════
    # PAYMENT TERMS (Working Capital)
    # ═══════════════════════════════════════════════════════════════════
    
    # Days Sales Outstanding - how long to collect revenue
    dso_days = Column(Integer, default=30)
    
    # Days Payable Outstanding - how long to pay vendors
    dpo_days = Column(Integer, default=30)
    
    # % of customers paying annually upfront
    annual_prepay_pct = Column(Numeric(5, 2), default=20.0)  # 20%
    
    # ═══════════════════════════════════════════════════════════════════
    # OPERATING ASSUMPTIONS
    # ═══════════════════════════════════════════════════════════════════
    
    # SaaS tools per employee per month
    saas_cost_per_employee = Column(Numeric(10, 2), default=500)
    
    # Infrastructure as % of revenue
    infra_pct_of_revenue = Column(Numeric(5, 2), default=5.0)  # 5%
    
    # Marketing spend as % of new ARR
    marketing_pct_of_new_arr = Column(Numeric(5, 2), default=30.0)  # 30%
    
    # Office cost per employee per month
    office_cost_per_employee = Column(Numeric(10, 2), default=500)
    
    # ═══════════════════════════════════════════════════════════════════
    # RUNWAY & CASH
    # ═══════════════════════════════════════════════════════════════════
    
    # Starting cash
    starting_cash = Column(Numeric(15, 2), default=0)
    
    # Minimum cash buffer (for runway calculation)
    min_cash_buffer = Column(Numeric(15, 2), default=100000)
    
    # Relationship
    scenario = relationship("StartupPlanningScenario", back_populates="assumptions")


class HeadcountPlan(Base):
    """
    Headcount plan by department and month.
    The primary driver of payroll expense.
    """
    __tablename__ = "headcount_plans"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False, index=True)
    
    # Department
    department = Column(SQLEnum(Department), nullable=False)
    
    # Role details
    role_title = Column(String(100), nullable=False)
    seniority_level = Column(String(50), nullable=True)  # Junior, Mid, Senior, Lead, Director, VP
    
    # Compensation
    annual_salary = Column(Numeric(15, 2), nullable=False)
    
    # Headcount by month (start date = first day of month they start)
    start_month = Column(Date, nullable=False)
    end_month = Column(Date, nullable=True)  # NULL = no end date
    
    # Number of people in this role
    headcount = Column(Integer, default=1)
    
    # Is this a backfill or new hire?
    is_backfill = Column(Boolean, default=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationship
    scenario = relationship("StartupPlanningScenario", back_populates="headcount_plan")


class SaaSRevenueDriver(Base):
    """
    SaaS revenue drivers by month.
    Tracks new customers, expansions, churn.
    """
    __tablename__ = "saas_revenue_drivers"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False, index=True)
    
    # Month
    period_month = Column(Date, nullable=False)
    
    # Revenue type
    revenue_type = Column(SQLEnum(RevenueType), default=RevenueType.MRR)
    
    # Customer counts
    starting_customers = Column(Integer, default=0)
    new_customers = Column(Integer, default=0)
    churned_customers = Column(Integer, default=0)
    ending_customers = Column(Integer, default=0)
    
    # MRR breakdown
    starting_mrr = Column(Numeric(15, 2), default=0)
    new_mrr = Column(Numeric(15, 2), default=0)
    expansion_mrr = Column(Numeric(15, 2), default=0)
    churned_mrr = Column(Numeric(15, 2), default=0)
    ending_mrr = Column(Numeric(15, 2), default=0)
    
    # Calculated ARR
    ending_arr = Column(Numeric(15, 2), default=0)  # ending_mrr * 12
    
    # CAC spend for this month's new customers
    cac_spend = Column(Numeric(15, 2), default=0)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationship
    scenario = relationship("StartupPlanningScenario", back_populates="revenue_drivers")


class VendorCommitment(Base):
    """
    Fixed vendor commitments (contracts, subscriptions).
    """
    __tablename__ = "vendor_commitments"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False, index=True)
    
    # Vendor details
    vendor_name = Column(String(255), nullable=False)
    category = Column(SQLEnum(ExpenseCategory), default=ExpenseCategory.SAAS_TOOLS)
    
    # Contract terms
    monthly_amount = Column(Numeric(15, 2), nullable=False)
    annual_amount = Column(Numeric(15, 2), nullable=True)  # For annual contracts
    
    # Payment timing
    payment_frequency = Column(String(20), default="monthly")  # monthly, quarterly, annual
    payment_terms_days = Column(Integer, default=30)  # NET 30, etc.
    
    # Contract dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # Auto-renewal
    auto_renews = Column(Boolean, default=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationship
    scenario = relationship("StartupPlanningScenario", back_populates="vendor_commitments")


class PlanningOutput(Base):
    """
    Generated output for a scenario - P&L, cashflow, runway.
    Computed from drivers and stored for audit.
    """
    __tablename__ = "planning_outputs"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False, index=True)
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    assumptions_version = Column(Integer, default=1)
    
    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY METRICS
    # ═══════════════════════════════════════════════════════════════════
    
    # Runway
    runway_months = Column(Integer, default=0)
    cash_zero_date = Column(Date, nullable=True)
    
    # Hiring capacity
    max_additional_hires = Column(Integer, default=0)
    hiring_capacity_details_json = Column(JSON, default=dict)
    
    # Key SaaS metrics (at end of plan period)
    ending_mrr = Column(Numeric(15, 2), default=0)
    ending_arr = Column(Numeric(15, 2), default=0)
    ending_customers = Column(Integer, default=0)
    
    # Key financial metrics
    total_revenue = Column(Numeric(15, 2), default=0)
    total_expenses = Column(Numeric(15, 2), default=0)
    total_burn = Column(Numeric(15, 2), default=0)
    ending_cash = Column(Numeric(15, 2), default=0)
    
    # ═══════════════════════════════════════════════════════════════════
    # DETAILED OUTPUTS (JSON for flexibility)
    # ═══════════════════════════════════════════════════════════════════
    
    # Monthly P&L
    monthly_pnl_json = Column(JSON, default=list)
    # Structure: [{month, revenue, cogs, gross_margin, opex_by_category, ebitda, net_income}, ...]
    
    # Monthly cashflow bridge
    monthly_cashflow_json = Column(JSON, default=list)
    # Structure: [{month, operating_cash, ar_change, ap_change, capex, financing, ending_cash}, ...]
    
    # Monthly headcount
    monthly_headcount_json = Column(JSON, default=list)
    # Structure: [{month, by_department: {eng: X, sales: Y, ...}, total}, ...]
    
    # Runway analysis
    runway_analysis_json = Column(JSON, default=dict)
    # Structure: {monthly_burn_rates, cumulative_burn, cash_projection, zero_cash_month}
    
    # Hiring capacity analysis
    hiring_analysis_json = Column(JSON, default=dict)
    # Structure: {current_burn, incremental_cost_per_hire_by_dept, max_hires_by_dept}
    
    # Relationship
    scenario = relationship("StartupPlanningScenario", back_populates="outputs")


class ScenarioComparison(Base):
    """
    Comparison between two scenarios (e.g., base vs branch).
    """
    __tablename__ = "scenario_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    
    base_scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False)
    compare_scenario_id = Column(Integer, ForeignKey("startup_planning_scenarios.id"), nullable=False)
    
    # Comparison metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    
    # Comparison results
    comparison_json = Column(JSON, default=dict)
    # Structure: {
    #   revenue_delta, expense_delta, burn_delta, runway_delta,
    #   headcount_delta_by_dept, mrr_delta, cash_delta
    # }
    
    summary = Column(Text, nullable=True)
