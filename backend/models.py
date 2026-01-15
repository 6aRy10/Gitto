from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

# Snapshot state machine
class SnapshotStatus:
    """Snapshot state machine: DRAFT -> READY_FOR_REVIEW -> LOCKED"""
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    LOCKED = "locked"

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total_rows = Column(Integer, default=0)
    data_health = Column(JSON)  # Store stats about the upload
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    is_locked = Column(Integer, default=0)
    lock_type = Column(String, nullable=True) # "Meeting", "Fiscal", "Scenario"
    
    # State machine
    status = Column(String(30), default=SnapshotStatus.DRAFT, nullable=False)
    ready_for_review_at = Column(DateTime, nullable=True)
    ready_for_review_by = Column(String(100), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String(100), nullable=True)
    
    # Lock gates (thresholds that must be met before locking)
    missing_fx_threshold = Column(Float, default=5.0)  # % of invoices missing FX rates
    unexplained_cash_threshold = Column(Float, default=5.0)  # % of cash unexplained
    lock_gate_checks = Column(JSON, nullable=True)  # Store gate check results
    
    # Lineage & Tracking
    dataset_id = Column(String, nullable=True) # UUID or hash linking to a raw upload session
    import_batch_id = Column(String, nullable=True) # ImportBatchID for tracking upload batches
    assumption_set_id = Column(String, nullable=True) # AssumptionSetID for scenario tracking
    fx_table_version = Column(String, nullable=True) # FX table version used
    
    # CFO Dashboard configuration
    opening_bank_balance = Column(Float, default=0.0)
    min_cash_threshold = Column(Float, default=0.0)
    unknown_bucket_kpi_target = Column(Float, default=5.0) # Configurable KPI target (<5% default)
    
    invoices = relationship("Invoice", back_populates="snapshot", cascade="all, delete-orphan")
    delays = relationship("SegmentDelay", back_populates="snapshot", cascade="all, delete-orphan")
    outflows = relationship("OutflowItem", back_populates="snapshot", cascade="all, delete-orphan")
    vendor_bills = relationship("VendorBill", back_populates="snapshot", cascade="all, delete-orphan")
    fx_rates = relationship("WeeklyFXRate", back_populates="snapshot", cascade="all, delete-orphan")
    calibration_stats = relationship("CalibrationStats", back_populates="snapshot", cascade="all, delete-orphan")
    entity = relationship("Entity", back_populates="snapshots")

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    currency = Column(String, default="EUR")
    payment_run_day = Column(Integer, default=3) # 0=Mon, 3=Thu, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Internal account identifiers for intercompany wash detection
    internal_account_ids = Column(JSON, nullable=True)  # List of internal account IDs
    
    snapshots = relationship("Snapshot", back_populates="entity")
    bank_accounts = relationship("BankAccount", back_populates="entity")
    invoices = relationship("Invoice", back_populates="entity")
    recurring_outflows = relationship("RecurringOutflow", back_populates="entity", cascade="all, delete-orphan")
    vendor_bills = relationship("VendorBill", back_populates="entity")

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    account_name = Column(String)
    account_number = Column(String)
    bank_name = Column(String)
    currency = Column(String, default="EUR")
    balance = Column(Float, default=0.0)
    balance_as_of = Column(DateTime, nullable=True)
    balance_source = Column(String, default="Manual") # Manual, API
    statement_start = Column(DateTime, nullable=True)
    statement_end = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    
    entity = relationship("Entity", back_populates="bank_accounts")
    transactions = relationship("BankTransaction", back_populates="bank_account")

class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"))
    transaction_date = Column(DateTime)
    amount = Column(Float)
    currency = Column(String)
    reference = Column(String)
    counterparty = Column(String)
    transaction_type = Column(String) # customer_receipt, supplier_payment, payroll, tax, rent, loan, etc.
    is_reconciled = Column(Integer, default=0)
    reconciliation_type = Column(String, nullable=True) # Deterministic, Rule, Manual, Suggested
    match_confidence = Column(Float, nullable=True)
    is_wash = Column(Integer, default=0) # Flag for intercompany wash detection
    
    # Unmatched transaction lifecycle (full statuses)
    lifecycle_status = Column(String, default="New")  # New, Assigned, In Review, Resolved, Escalated
    assignee = Column(String, nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    sla_breach_at = Column(DateTime, nullable=True)  # SLA deadline for resolution
    days_unmatched = Column(Integer, default=0)  # Aging metric
    resolution_notes = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    bank_account = relationship("BankAccount", back_populates="transactions")
    reconciled_invoices = relationship("Invoice", secondary="reconciliation_table", back_populates="bank_transactions")

class ReconciliationTable(Base):
    __tablename__ = "reconciliation_table"
    id = Column(Integer, primary_key=True, index=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount_allocated = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String, nullable=True)  # Audit trail for who created
    match_type = Column(String, nullable=True)  # Deterministic, Rule, Manual, Suggested
    confidence = Column(Float, nullable=True)
    
    # Ensure allocations don't exceed transaction amount (checked in code, not DB)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    canonical_id = Column(String, index=True) # Rich Fingerprint for idempotency
    source_system = Column(String, default="Excel")
    
    # Relationship fields for credit notes, partials, rebills
    parent_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    relationship_type = Column(String, nullable=True)  # "credit_note", "partial", "rebill", "adjustment"
    
    project_desc = Column(String)
    project = Column(String)
    country = Column(String)
    customer = Column(String)
    document_number = Column(String)
    terms_of_payment = Column(String)
    payment_terms_days = Column(Integer)
    document_date = Column(DateTime)
    invoice_issue_date = Column(DateTime)
    expected_due_date = Column(DateTime)
    payment_date = Column(DateTime, nullable=True)
    amount = Column(Float)
    currency = Column(String)
    document_type = Column(String)
    special_gl_ind = Column(String)
    due_year = Column(Integer)
    
    # Truth labeling
    truth_label = Column(String, default="modeled")  # bank-true, reconciled, modeled, unknown
    
    # Blockage & Dispute
    is_blocked = Column(Integer, default=0)
    blocked_reason = Column(String, nullable=True) # PO missing, Pricing mismatch, Delivery issue, Approval delay
    dispute_status = Column(String, default="active") # open, resolved
    assignee = Column(String, nullable=True)
    resolution_status = Column(String, default="Unresolved") # Unresolved, Disputed, Resolved
    next_action = Column(String, nullable=True)
    eta_unblock = Column(DateTime, nullable=True)
    
    # Prediction fields
    predicted_payment_date = Column(DateTime, nullable=True)
    predicted_delay = Column(Integer, nullable=True)
    prediction_segment = Column(String, nullable=True)
    confidence_p25 = Column(DateTime, nullable=True)
    confidence_p75 = Column(DateTime, nullable=True)
    
    snapshot = relationship("Snapshot", back_populates="invoices")
    entity = relationship("Entity", back_populates="invoices")
    dispute_logs = relationship("DisputeLog", back_populates="invoice", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", secondary="reconciliation_table", back_populates="reconciled_invoices")
    
    # Self-referential relationship for parent/child invoices
    parent_invoice = relationship("Invoice", remote_side=[id], backref="related_invoices")
    
    __table_args__ = (
        UniqueConstraint('snapshot_id', 'canonical_id', name='uix_snapshot_canonical'),
    )

class VendorBill(Base):
    __tablename__ = "vendor_bills"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    canonical_id = Column(String, index=True)
    vendor_name = Column(String)
    document_number = Column(String)
    amount = Column(Float)
    currency = Column(String, default="EUR")
    due_date = Column(DateTime)
    approval_date = Column(DateTime, nullable=True)
    scheduled_payment_date = Column(DateTime, nullable=True)
    hold_status = Column(Integer, default=0) # 0=Active, 1=Hold
    is_discretionary = Column(Integer, default=0)
    category = Column(String) # For gap-filling with templates
    
    # Discretionary classification workflow
    discretionary_reason = Column(String, nullable=True)  # Reason for classification
    discretionary_approved_by = Column(String, nullable=True)  # Who approved classification
    discretionary_approved_at = Column(DateTime, nullable=True)  # When approved
    
    snapshot = relationship("Snapshot", back_populates="vendor_bills")
    entity = relationship("Entity", back_populates="vendor_bills")

class WeeklyFXRate(Base):
    __tablename__ = "weekly_fx_rates"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    from_currency = Column(String)
    to_currency = Column(String)
    rate = Column(Float)
    effective_week_start = Column(DateTime) # Locked as-of snapshot date
    
    snapshot = relationship("Snapshot", back_populates="fx_rates")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user = Column(String)
    action = Column(String) # Create, Update, Delete, Override, Sign-off, PolicyChange, LeverExecution
    resource_type = Column(String) # Snapshot, Invoice, BankMatch, Scenario, MatchingPolicy, Lever
    resource_id = Column(Integer, nullable=True)
    changes = Column(JSON, nullable=True) # Old/New value map
    
    # Enhanced audit fields
    entity_id = Column(Integer, nullable=True)
    snapshot_id = Column(Integer, nullable=True)
    ip_address = Column(String, nullable=True)
    user_role = Column(String, nullable=True)

class DisputeLog(Base):
    __tablename__ = "dispute_logs"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    note = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(String)
    
    invoice = relationship("Invoice", back_populates="dispute_logs")

class SegmentDelay(Base):
    __tablename__ = "segment_delays"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    
    segment_type = Column(String) # e.g., "Customer+Country+Terms"
    segment_key = Column(String)  # JSON or stringified key
    
    count = Column(Integer)
    median_delay = Column(Float)
    p25_delay = Column(Float)
    p75_delay = Column(Float)
    p90_delay = Column(Float)
    std_delay = Column(Float)
    
    # Enhanced statistics
    mean_delay = Column(Float, nullable=True)
    min_delay = Column(Float, nullable=True)
    max_delay = Column(Float, nullable=True)
    recency_weighted = Column(Integer, default=0)  # 0 or 1
    winsorized = Column(Integer, default=0)  # 0 or 1
    
    # Regime shift detection
    is_regime_shift = Column(Integer, default=0)
    shift_detected_at = Column(DateTime, nullable=True)
    
    snapshot = relationship("Snapshot", back_populates="delays")


class CalibrationStats(Base):
    __tablename__ = "calibration_stats"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    
    segment_type = Column(String)
    segment_key = Column(String)
    
    # Coverage metrics (from conformal prediction)
    coverage_p25 = Column(Float)  # Coverage of P25-P75 interval (should be ~50%)
    coverage_p50 = Column(Float)  # Coverage of P50 (should be ~50%)
    coverage_p75 = Column(Float)  # Coverage of P75 (should be ~75%)
    coverage_p90 = Column(Float)  # Coverage of P90 (should be ~90%)
    
    calibration_error = Column(Float)  # Average deviation from expected coverage
    sample_size = Column(Integer)
    backtest_splits = Column(Integer, default=5)
    calibrated_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    snapshot = relationship("Snapshot", back_populates="calibration_stats")

class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    config = Column(JSON) # Store scenario knobs
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SnowflakeConfig(Base):
    __tablename__ = "snowflake_configs"
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String)
    user = Column(String)
    password = Column(String, nullable=True)  # DEPRECATED: Use password_env_var instead
    password_env_var = Column(String, nullable=True)  # P1 Fix: Environment variable name for password
    warehouse = Column(String)
    database = Column(String)
    schema_name = Column(String)
    role = Column(String, nullable=True)
    
    # Mapping configuration
    invoice_mapping = Column(JSON) 
    customer_mapping = Column(JSON, nullable=True)
    
    last_sync_at = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)

class OutflowItem(Base):
    __tablename__ = "outflow_items"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    category = Column(String) # payroll, tax, rent, debt, vendor, capex, etc.
    description = Column(String)
    amount = Column(Float)
    currency = Column(String, default="EUR")
    expected_date = Column(DateTime)
    is_discretionary = Column(Integer, default=0) # 0 = Committed, 1 = Delayable
    source = Column(String, default="Manual") # Manual, ERP, Payroll, Calendar
    status = Column(String, default="Planned") # Planned, Approved, Paid
    
    snapshot = relationship("Snapshot", back_populates="outflows")

class RecurringOutflow(Base):
    __tablename__ = "recurring_outflows"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    
    category = Column(String)
    description = Column(String)
    amount = Column(Float)
    currency = Column(String, default="EUR")
    
    # Scheduling logic
    frequency = Column(String) # Weekly, Monthly, Quarterly
    day_of_week = Column(Integer, nullable=True) # 0-6
    day_of_month = Column(Integer, nullable=True) # 1-31
    is_last_day = Column(Integer, default=0) 
    
    is_discretionary = Column(Integer, default=0)
    
    entity = relationship("Entity", back_populates="recurring_outflows")

class SourceMapping(Base):
    __tablename__ = "source_mappings"
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, index=True) # e.g., "SAP", "NetSuite", "Excel_Generic"
    mapping_config = Column(JSON) # { "internal_field": "source_column", ... }
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TreasuryAction(Base):
    __tablename__ = "treasury_actions"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    action_type = Column(String) # "Collection Push", "AP Hold", "Revolver Draw"
    target_id = Column(Integer, nullable=True) # ID of Invoice or VendorBill
    description = Column(String)
    expected_impact = Column(Float)
    realized_impact = Column(Float, nullable=True)
    owner = Column(String)
    status = Column(String, default="Open") # "Open", "Pending Approval", "Approved", "Executed", "Realized"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    
    # Approval workflow
    approval_required = Column(Integer, default=0)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

class LeverPolicy(Base):
    """
    Policy guardrails for liquidity levers to prevent free-form manipulation.
    """
    __tablename__ = "lever_policies"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    max_vendor_delay_days = Column(Integer, default=14)
    min_cash_threshold = Column(Float, default=0.0)
    approval_threshold = Column(Float, default=100000.0)  # Actions over this require approval
    protected_vendors = Column(JSON, default=list)  # List of vendor names that cannot be delayed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    entity = relationship("Entity", backref="lever_policies")

class CollectionAction(Base):
    """
    Minimal CRM-free tracking for collections: action taken, expected pull-forward, outcome.
    """
    __tablename__ = "collection_actions"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    action_type = Column(String)  # "called", "emailed", "escalated"
    expected_pullforward_days = Column(Integer, default=0)
    expected_pullforward_amount = Column(Float, default=0.0)
    outcome = Column(String, nullable=True)  # "paid", "partial", "no_change", null (pending)
    outcome_date = Column(DateTime, nullable=True)
    outcome_amount = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    owner = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    invoice = relationship("Invoice", backref="collection_actions")

# ========== NEW MODELS ==========

class MatchingPolicy(Base):
    """
    Configurable matching policies per entity/currency for reconciliation.
    CFO Trust: Per-entity, per-currency configurable matching with audit trail.
    """
    __tablename__ = "matching_policies"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)  # null = global default
    currency = Column(String, nullable=True)  # null = all currencies
    
    # Tolerance settings
    amount_tolerance = Column(Float, default=0.01)  # Absolute tolerance
    amount_tolerance_pct = Column(Float, default=0.0)  # Percentage tolerance
    date_window_days = Column(Integer, default=7)  # Date matching window
    
    # Tier enablement flags (CFO checklist item C4)
    deterministic_enabled = Column(Integer, default=1)  # Enable Tier 1 (exact reference)
    rules_enabled = Column(Integer, default=1)  # Enable Tier 2 (amount + date window)
    suggested_enabled = Column(Integer, default=1)  # Enable Tier 3 (fuzzy/suggested)
    
    # Tier settings
    require_counterparty_tier1 = Column(Integer, default=0)  # Require counterparty match for Tier 1
    auto_reconcile_tier1 = Column(Integer, default=1)  # Auto-reconcile Tier 1 matches
    auto_reconcile_tier2 = Column(Integer, default=1)  # Auto-reconcile Tier 2 matches
    
    # Audit
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    updated_by = Column(String, nullable=True)
    
    entity = relationship("Entity", backref="matching_policies")

class PaymentRunException(Base):
    """
    Off-cycle/urgent payment exceptions to the standard payment run schedule.
    """
    __tablename__ = "payment_run_exceptions"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    vendor_bill_id = Column(Integer, ForeignKey("vendor_bills.id"), nullable=True)
    
    exception_type = Column(String)  # "urgent", "off_cycle", "manual_override"
    requested_payment_date = Column(DateTime)
    reason = Column(String)
    
    # Approval workflow
    requested_by = Column(String)
    requested_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    status = Column(String, default="Pending")  # Pending, Approved, Rejected, Executed
    
    entity = relationship("Entity", backref="payment_exceptions")
    vendor_bill = relationship("VendorBill", backref="payment_exceptions")

class SegmentStatsCache(Base):
    """
    Cached segment statistics for performance optimization.
    Avoids recomputing distributions on every screen refresh.
    """
    __tablename__ = "segment_stats_cache"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    segment_type = Column(String)  # e.g., "Customer+Country+Terms"
    segment_key = Column(String)
    
    # Cached statistics
    count = Column(Integer)
    p25_delay = Column(Float)
    p50_delay = Column(Float)
    p75_delay = Column(Float)
    p90_delay = Column(Float)
    std_delay = Column(Float)
    
    # Cache metadata
    computed_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional TTL
    is_valid = Column(Integer, default=1)

class AISchemaField(Base):
    """
    Canonical schema fields that the AI analyst is allowed to reference.
    Prevents AI from guessing about non-existent fields.
    """
    __tablename__ = "ai_schema_fields"
    id = Column(Integer, primary_key=True, index=True)
    field_name = Column(String, unique=True)
    field_description = Column(String)
    field_type = Column(String)  # "numeric", "date", "text", "boolean"
    is_computed = Column(Integer, default=0)  # 0 = raw field, 1 = derived/computed
    computation_description = Column(String, nullable=True)

class IntercompanyWash(Base):
    """
    Tracked intercompany wash transactions requiring approval.
    """
    __tablename__ = "intercompany_washes"
    id = Column(Integer, primary_key=True, index=True)
    entity_a_id = Column(Integer, ForeignKey("entities.id"))
    entity_b_id = Column(Integer, ForeignKey("entities.id"))
    transaction_a_id = Column(Integer, ForeignKey("bank_transactions.id"))
    transaction_b_id = Column(Integer, ForeignKey("bank_transactions.id"))
    
    amount = Column(Float)
    currency = Column(String)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    detection_method = Column(String)  # "internal_account", "heuristic", "manual"
    
    # Approval workflow
    status = Column(String, default="Pending")  # Pending, Approved, Rejected
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTOR SDK MODELS - Enterprise Data Integration
# ═══════════════════════════════════════════════════════════════════════════════

class Connector(Base):
    """
    Registered connector types (bank_mt940, erp_netsuite, etc.)
    """
    __tablename__ = "connectors"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False)  # 'bank_mt940', 'bank_bai2', 'erp_netsuite', etc.
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    connections = relationship("Connection", back_populates="connector", cascade="all, delete-orphan")
    source_profiles = relationship("SourceProfile", back_populates="connector", cascade="all, delete-orphan")


class Connection(Base):
    """
    Specific endpoint instance for a connector (credentials, URL, etc.)
    """
    __tablename__ = "connections"
    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("connectors.id"), nullable=False)
    name = Column(String(100), nullable=False)
    endpoint_url = Column(String(500), nullable=True)
    credentials_ref = Column(String(100), nullable=True)  # Reference to secrets manager (never plaintext)
    
    # Sync state
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="idle")  # 'idle', 'running', 'failed', 'success'
    sync_cursor = Column(String, nullable=True)  # For incremental sync (cursor-based)
    
    # Health metrics
    last_success_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    connector = relationship("Connector", back_populates="connections")
    sync_runs = relationship("SyncRun", back_populates="connection", cascade="all, delete-orphan")


class SyncRun(Base):
    """
    Audit trail of each sync execution.
    """
    __tablename__ = "sync_runs"
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=False)
    
    # Timing
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default="running")  # 'running', 'success', 'failed', 'partial'
    error_message = Column(String, nullable=True)
    
    # Metrics
    rows_extracted = Column(Integer, default=0)
    rows_created = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    
    # Lineage
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    
    connection = relationship("Connection", back_populates="sync_runs")
    dataset = relationship("Dataset", back_populates="sync_run")


class Dataset(Base):
    """
    Versioned import batch - immutable record of data at point-in-time.
    """
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    
    source_type = Column(String(50), nullable=False)  # 'bank_statement', 'ar_invoice', 'ap_bill', etc.
    source_connection_id = Column(Integer, ForeignKey("connections.id"), nullable=True)
    
    # Point-in-time reference
    as_of_timestamp = Column(DateTime, nullable=False)
    
    # Metrics
    row_count = Column(Integer, default=0)
    checksum = Column(String(64), nullable=True)  # SHA256 of normalized content
    
    # Raw data reference (for audit/debug)
    raw_payload_ref = Column(String(200), nullable=True)  # S3/blob reference
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    sync_run = relationship("SyncRun", back_populates="dataset", uselist=False)


class SourceProfile(Base):
    """
    Saved field mappings for a connector - finance ops map once, reuse.
    """
    __tablename__ = "source_profiles"
    id = Column(Integer, primary_key=True, index=True)
    connector_id = Column(Integer, ForeignKey("connectors.id"), nullable=False)
    name = Column(String(100), nullable=False)
    
    # Field mappings: {"source_field": "canonical_field", ...}
    field_mappings = Column(JSON, nullable=True)
    
    # Transform rules: {"date_format": "DD/MM/YYYY", "currency_code_map": {...}}
    transform_rules = Column(JSON, nullable=True)
    
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    connector = relationship("Connector", back_populates="source_profiles")


class DataFreshnessAlert(Base):
    """
    Alerts when data sources become stale.
    """
    __tablename__ = "data_freshness_alerts"
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=False)
    
    alert_type = Column(String(50), nullable=False)  # 'stale_data', 'sync_failed', 'drift_detected'
    severity = Column(String(20), default="warning")  # 'info', 'warning', 'critical'
    message = Column(String(500), nullable=False)
    
    # Timing
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)


class DataQualityIssue(Base):
    """
    Data quality issues detected during ingestion.
    """
    __tablename__ = "data_quality_issues"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    
    issue_type = Column(String(50), nullable=False)  # 'duplicate', 'missing_fx', 'stale_source', 'currency_mismatch', 'missing_due_date'
    severity = Column(String(20), default="warning")  # 'info', 'warning', 'error', 'critical'
    
    # Issue details
    description = Column(String(500), nullable=False)
    affected_row_ids = Column(JSON, nullable=True)  # List of affected row IDs
    affected_amount = Column(Float, nullable=True)
    
    # Resolution
    status = Column(String(20), default="open")  # 'open', 'acknowledged', 'resolved', 'ignored'
    resolution_notes = Column(String, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# BACKTESTING & CALIBRATION MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ForecastBacktest(Base):
    """
    Backtest record for forecast calibration.
    Records predicted vs actual for accuracy measurement.
    """
    __tablename__ = "forecast_backtests"
    id = Column(Integer, primary_key=True, index=True)
    
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # When the forecast was made
    forecast_date = Column(DateTime, nullable=False)
    
    # Prediction
    predicted_week = Column(String, nullable=True)  # Week predicted for payment
    predicted_p25 = Column(Float, nullable=True)
    predicted_p50 = Column(Float, nullable=True)  # Median delay prediction
    predicted_p75 = Column(Float, nullable=True)
    predicted_p90 = Column(Float, nullable=True)
    
    # Segment used for prediction
    segment_type = Column(String(50), nullable=True)
    segment_key = Column(String(200), nullable=True)
    sample_size = Column(Integer, nullable=True)
    
    # Actuals (filled in when payment arrives)
    actual_date = Column(DateTime, nullable=True)
    actual_delay = Column(Integer, nullable=True)  # Actual delay in days
    
    # Calibration checks
    in_p25_p75 = Column(Integer, nullable=True)  # 1 if actual was in P25-P75 range
    in_p10_p90 = Column(Integer, nullable=True)  # 1 if actual was in P10-P90 range
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReconciliationException(Base):
    """
    Exception workflow for unmatched bank transactions.
    """
    __tablename__ = "reconciliation_exceptions"
    id = Column(Integer, primary_key=True, index=True)
    
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=False)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    
    # Status workflow
    status = Column(String(20), default="new")  # 'new', 'assigned', 'in_review', 'resolved', 'escalated'
    
    # Assignment
    assignee_id = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # SLA tracking
    sla_due_at = Column(DateTime, nullable=True)
    days_unmatched = Column(Integer, default=0)
    
    # Resolution
    resolution_type = Column(String(50), nullable=True)  # 'matched', 'write_off', 'fee', 'chargeback', 'other'
    resolution_notes = Column(String, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Escalation
    escalated_to = Column(String(100), nullable=True)
    escalation_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════════
# FINANCE COLLABORATION PRIMITIVES - "GitHub for Cash"
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotStatus:
    """Snapshot workflow states - Snapshot = Commit"""
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    LOCKED = "locked"


class CollaborationSnapshot(Base):
    """
    Enhanced Snapshot for collaboration - a point-in-time locked state.
    Think: GitHub commit for cash position.
    
    Contains:
    - Bank balances + transactions (as-of + statement window)
    - AR/AP datasets
    - FX table used
    - Computed forecast outputs (materialized weekly grid)
    - Policies used (payment run day, tolerances, min cash)
    """
    __tablename__ = "collaboration_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    
    # Status workflow: DRAFT → READY_FOR_REVIEW → LOCKED
    status = Column(String(30), default=SnapshotStatus.DRAFT, nullable=False)
    
    # Point-in-time references
    bank_as_of = Column(DateTime, nullable=False)
    erp_as_of = Column(DateTime, nullable=True)
    fx_version = Column(String(50), nullable=True)
    
    # Lock state - immutable once locked
    is_locked = Column(Integer, default=0)
    lock_reason = Column(String(200), nullable=True)
    locked_by = Column(String(100), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    
    # Audit
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    ready_at = Column(DateTime, nullable=True)
    ready_by = Column(String(100), nullable=True)
    
    # Computed metrics (materialized for fast access)
    total_bank_balance = Column(Float, default=0.0)
    cash_explained_pct = Column(Float, default=0.0)
    unknown_bucket_amount = Column(Float, default=0.0)
    exception_count = Column(Integer, default=0)
    
    # Policy snapshot (frozen at lock time)
    policies_json = Column(JSON, nullable=True)
    
    # Relationships
    exceptions = relationship("CollaborationException", back_populates="snapshot", cascade="all, delete-orphan")
    matches = relationship("CollaborationMatch", back_populates="snapshot", cascade="all, delete-orphan")
    scenarios = relationship("CollaborationScenario", back_populates="base_snapshot")
    comments = relationship("CollaborationComment", back_populates="snapshot", cascade="all, delete-orphan")
    weekly_packs = relationship("WeeklyPack", back_populates="snapshot", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready_for_review', 'locked')",
            name="ck_collab_snapshot_status"
        ),
        # Locked snapshots must have lock metadata
        CheckConstraint(
            "(is_locked = 0) OR (locked_by IS NOT NULL AND locked_at IS NOT NULL)",
            name="ck_collab_locked_metadata"
        ),
    )


class ExceptionType:
    """Exception types - things that prevent full trust"""
    UNMATCHED_BANK_TXN = "unmatched_bank_txn"
    SUGGESTED_MATCH_PENDING = "suggested_match_pending"
    MISSING_DUE_DATE = "missing_due_date"
    MISSING_FX_RATE = "missing_fx_rate"
    DUPLICATE_IDENTITY = "duplicate_identity"
    OUTLIER_DELAY = "outlier_delay"
    INTERCOMPANY_WASH = "intercompany_wash"
    STALE_DATA = "stale_data"


class ExceptionStatus:
    """Exception workflow states"""
    OPEN = "open"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class CollaborationException(Base):
    """
    Exception - the "Issue" - anything that prevents full trust.
    Think: GitHub Issue for cash data quality.
    """
    __tablename__ = "collaboration_exceptions"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=False)
    
    # Exception type and severity
    exception_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="warning")  # info, warning, error, critical
    
    # Impact
    amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    
    # Evidence references (JSON array of {type, id} objects)
    evidence_refs = Column(JSON, nullable=True)
    
    # Status workflow: OPEN → IN_REVIEW → (RESOLVED | WONT_FIX)
    status = Column(String(20), default=ExceptionStatus.OPEN, nullable=False)
    
    # Assignment
    assignee_id = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    assigned_by = Column(String(100), nullable=True)
    
    # SLA tracking
    sla_due_at = Column(DateTime, nullable=True)
    
    # Resolution
    resolution_type = Column(String(50), nullable=True)
    resolution_note = Column(String(500), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Escalation
    escalated_to = Column(String(100), nullable=True)
    escalation_reason = Column(String(200), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    snapshot = relationship("CollaborationSnapshot", back_populates="exceptions")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_review', 'escalated', 'resolved', 'wont_fix')",
            name="ck_collab_exception_status"
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name="ck_collab_exception_severity"
        ),
    )


class MatchType:
    """Reconciliation match types - 4-tier ladder"""
    DETERMINISTIC = "deterministic"  # Tier 1: Auto-cleared exact match
    RULE = "rule"                    # Tier 2: Pattern match
    SUGGESTED = "suggested"          # Tier 3: Needs approval
    MANUAL = "manual"                # Tier 4: Unmatched queue


class MatchStatus:
    """Match workflow states"""
    PENDING_APPROVAL = "pending_approval"  # Suggested matches start here
    RECONCILED = "reconciled"              # Approved/auto-cleared
    REJECTED = "rejected"                   # Rejected suggestion


class CollaborationMatch(Base):
    """
    Match - many-to-many link between bank transactions and invoices/bills.
    
    Hard constraints (invariants):
    - Sum allocations per txn == txn amount
    - Sum allocations to invoice ≤ open amount
    - Suggested matches NEVER auto-apply
    """
    __tablename__ = "collaboration_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=False)
    
    # Match type (4-tier ladder)
    match_type = Column(String(20), nullable=False)
    
    # Confidence score (for suggested matches)
    confidence = Column(Float, nullable=True)
    
    # Status: Suggested must be PENDING_APPROVAL until approved
    status = Column(String(20), default=MatchStatus.PENDING_APPROVAL, nullable=False)
    
    # Audit trail
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Approval (for suggested matches)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(200), nullable=True)
    
    # Relationships
    snapshot = relationship("CollaborationSnapshot", back_populates="matches")
    allocations = relationship("MatchAllocation", back_populates="match", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "match_type IN ('deterministic', 'rule', 'suggested', 'manual')",
            name="ck_collab_match_type"
        ),
        CheckConstraint(
            "status IN ('pending_approval', 'reconciled', 'rejected')",
            name="ck_collab_match_status"
        ),
        # Suggested matches must start pending
        CheckConstraint(
            "(match_type != 'suggested') OR (status = 'pending_approval') OR (approved_by IS NOT NULL)",
            name="ck_collab_suggested_approval"
        ),
    )


class MatchAllocation(Base):
    """
    Allocation within a match - tracks how much of a txn maps to which invoice.
    
    Invariants:
    - Sum of allocations for a transaction == transaction amount
    - Sum of allocations to an invoice ≤ invoice open amount
    """
    __tablename__ = "match_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("collaboration_matches.id"), nullable=False)
    
    # Bank side
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=False)
    
    # Invoice/Bill side (one or the other)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    vendor_bill_id = Column(Integer, ForeignKey("vendor_bills.id"), nullable=True)
    
    # Allocation amount
    allocated_amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    match = relationship("CollaborationMatch", back_populates="allocations")
    
    __table_args__ = (
        # Must have either invoice_id or vendor_bill_id
        CheckConstraint(
            "(invoice_id IS NOT NULL) OR (vendor_bill_id IS NOT NULL)",
            name="ck_collab_allocation_target"
        ),
    )


class ScenarioStatus:
    """Scenario workflow states - Scenario = Branch"""
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class CollaborationScenario(Base):
    """
    Scenario - the "Branch" - a what-if plan that never rewrites base truth.
    Think: GitHub branch for cash forecasting.
    """
    __tablename__ = "collaboration_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    base_snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Status workflow: DRAFT → PROPOSED → (APPROVED | REJECTED) → ARCHIVED
    status = Column(String(20), default=ScenarioStatus.DRAFT, nullable=False)
    
    # Assumptions (JSON blob of scenario parameters)
    assumptions_json = Column(JSON, nullable=True)
    
    # Computed impact (materialized for UI)
    impact_summary_json = Column(JSON, nullable=True)
    
    # Audit trail
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Submission
    submitted_by = Column(String(100), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    
    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(200), nullable=True)
    
    # Relationships
    base_snapshot = relationship("CollaborationSnapshot", back_populates="scenarios")
    actions = relationship("CollaborationAction", back_populates="scenario", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'proposed', 'approved', 'rejected', 'archived')",
            name="ck_collab_scenario_status"
        ),
    )


class ActionType:
    """Action types - decisions with cash impact"""
    DELAY_VENDOR = "delay_vendor"
    PUSH_COLLECTIONS = "push_collections"
    DRAW_REVOLVER = "draw_revolver"
    FACTOR_INVOICE = "factor_invoice"
    HOLD_PAYMENT = "hold_payment"
    EXPEDITE_PAYMENT = "expedite_payment"
    FX_HEDGE = "fx_hedge"
    OTHER = "other"


class ActionStatus:
    """Action workflow states - Action = Task with impact"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class CollaborationAction(Base):
    """
    Action - the "Task with impact" - a decision like delay vendor, push collections.
    Think: GitHub PR for treasury decisions.
    """
    __tablename__ = "collaboration_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Can belong to scenario OR directly to snapshot
    scenario_id = Column(Integer, ForeignKey("collaboration_scenarios.id"), nullable=True)
    snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=True)
    
    # Action details
    action_type = Column(String(30), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Target references (JSON array of {type, id} objects)
    target_refs = Column(JSON, nullable=True)
    
    # Ownership
    owner_id = Column(String(100), nullable=False)
    due_date = Column(DateTime, nullable=True)
    
    # Expected impact (JSON: {amount, currency, week, confidence})
    expected_cash_impact_json = Column(JSON, nullable=True)
    
    # Realized impact (filled in after execution)
    realized_cash_impact_json = Column(JSON, nullable=True)
    
    # Status workflow: DRAFT → PENDING_APPROVAL → APPROVED → IN_PROGRESS → DONE
    status = Column(String(20), default=ActionStatus.DRAFT, nullable=False)
    
    # Approval requirement
    requires_approval = Column(Integer, default=1)
    
    # Audit trail
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Approval
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(200), nullable=True)
    
    # Execution
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Audit reference
    audit_ref = Column(String(100), nullable=True)
    
    # Relationships
    scenario = relationship("CollaborationScenario", back_populates="actions")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'in_progress', 'done', 'cancelled')",
            name="ck_collab_action_status"
        ),
    )


class CollaborationComment(Base):
    """
    Comment - threaded conversation anchored to facts.
    Finance workspace needs discussion tied to evidence.
    """
    __tablename__ = "collaboration_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Parent (polymorphic - can comment on anything)
    parent_type = Column(String(30), nullable=False)  # snapshot, exception, match, scenario, action
    parent_id = Column(Integer, nullable=False)
    
    # Optional snapshot context
    snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=True)
    
    # Comment content
    text = Column(String(2000), nullable=False)
    
    # Threading
    reply_to_id = Column(Integer, ForeignKey("collaboration_comments.id"), nullable=True)
    
    # Author
    author_id = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Soft delete
    is_deleted = Column(Integer, default=0)
    
    # Relationships
    snapshot = relationship("CollaborationSnapshot", back_populates="comments")
    evidence_links = relationship("EvidenceLink", back_populates="comment", cascade="all, delete-orphan")
    replies = relationship("CollaborationComment", backref="parent_comment", remote_side=[id])


class EvidenceLink(Base):
    """
    Evidence Link - ties comments to specific data artifacts.
    """
    __tablename__ = "evidence_links"
    
    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("collaboration_comments.id"), nullable=False)
    
    # Evidence reference
    evidence_type = Column(String(30), nullable=False)  # invoice, bank_txn, grid_cell, vendor_bill
    evidence_id = Column(String(100), nullable=False)  # ID or composite key (e.g., "week:3|bucket:cash_in")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    comment = relationship("CollaborationComment", back_populates="evidence_links")


class WeeklyPack(Base):
    """
    Weekly Pack - the "meeting artifact" - generated view/report for snapshot.
    
    Contents:
    - Cash today (bank truth)
    - 13-week expected + downside
    - Red weeks
    - Variance vs last locked snapshot
    - Unknown bucket
    - Top exceptions
    - Approved actions / scenarios
    """
    __tablename__ = "weekly_packs"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=False)
    
    # Pack content (JSON blob with all sections)
    content_json = Column(JSON, nullable=False)
    
    # Generation metadata
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    generated_by = Column(String(100), nullable=False)
    
    # Export references
    pdf_url = Column(String(500), nullable=True)
    
    # Relationships
    snapshot = relationship("CollaborationSnapshot", back_populates="weekly_packs")


class CollaborationAuditLog(Base):
    """
    Enhanced Audit Log for collaboration actions.
    Every approval/match/override logged with who/when/what.
    """
    __tablename__ = "collaboration_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # When
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Who
    user_id = Column(String(100), nullable=False)
    user_role = Column(String(30), nullable=True)
    
    # What
    action = Column(String(50), nullable=False)  # create, update, approve, reject, lock, assign, resolve
    resource_type = Column(String(30), nullable=False)  # snapshot, exception, match, scenario, action, comment
    resource_id = Column(Integer, nullable=False)
    
    # Context
    snapshot_id = Column(Integer, ForeignKey("collaboration_snapshots.id"), nullable=True)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    # Changes (JSON: {field: {old, new}})
    changes_json = Column(JSON, nullable=True)
    
    # Additional context
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(200), nullable=True)
    notes = Column(String(500), nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# GITTO TRUST CERTIFICATION MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class TrustReportRecord(Base):
    """
    Persisted Trust Report for audit trail.
    Generated for every snapshot certification attempt.
    """
    __tablename__ = "trust_report_records"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    
    # Report metadata
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    generated_by = Column(String(100), nullable=True)
    
    # Overall scores
    overall_trust_score = Column(Float, nullable=False)
    lock_eligible = Column(Integer, default=0)  # 0 or 1
    
    # Full report JSON
    report_json = Column(JSON, nullable=False)
    
    # Checksum for integrity verification
    report_checksum = Column(String(64), nullable=True)
    
    # Status
    status = Column(String(30), default="generated")  # generated, reviewed, approved, rejected


class TrustGateOverride(Base):
    """
    CFO Override record for failed trust gates.
    Requires explicit acknowledgment text for audit.
    """
    __tablename__ = "trust_gate_overrides"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    trust_report_id = Column(Integer, ForeignKey("trust_report_records.id"), nullable=True)
    
    # Gate identification
    gate_name = Column(String(100), nullable=False)
    gate_type = Column(String(30), nullable=False)  # metric, invariant
    
    # Override details
    acknowledgment_text = Column(String(500), nullable=False)
    override_reason = Column(String(500), nullable=True)
    
    # CFO/User info
    overridden_by = Column(String(100), nullable=False)
    overridden_at = Column(DateTime, default=datetime.datetime.utcnow)
    user_role = Column(String(50), nullable=True)
    
    # Evidence at time of override
    gate_value_at_override = Column(Float, nullable=True)
    gate_threshold = Column(Float, nullable=True)
    evidence_refs_json = Column(JSON, nullable=True)


class TrustInvariantResult(Base):
    """
    Persisted invariant check results.
    Stored each time trust certification runs.
    """
    __tablename__ = "trust_invariant_results"
    
    id = Column(Integer, primary_key=True, index=True)
    trust_report_id = Column(Integer, ForeignKey("trust_report_records.id"), nullable=False)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    
    # Invariant identification
    invariant_name = Column(String(100), nullable=False)
    
    # Result
    passed = Column(Integer, nullable=False)  # 0 or 1
    severity = Column(String(20), nullable=False)  # critical, error, warning
    message = Column(String(500), nullable=True)
    
    # Evidence
    evidence_count = Column(Integer, default=0)
    evidence_refs_json = Column(JSON, nullable=True)
    details_json = Column(JSON, nullable=True)
    
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)
