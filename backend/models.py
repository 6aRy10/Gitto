from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    total_rows = Column(Integer, default=0)
    data_health = Column(JSON)  # Store stats about the upload
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    # Lineage & Tracking
    dataset_id = Column(String, nullable=True) # UUID or hash linking to a raw upload session
    
    # CFO Dashboard configuration
    opening_bank_balance = Column(Float, default=0.0)
    min_cash_threshold = Column(Float, default=0.0)
    
    invoices = relationship("Invoice", back_populates="snapshot", cascade="all, delete-orphan")
    delays = relationship("SegmentDelay", back_populates="snapshot", cascade="all, delete-orphan")
    outflows = relationship("OutflowItem", back_populates="snapshot", cascade="all, delete-orphan")
    vendor_bills = relationship("VendorBill", back_populates="snapshot", cascade="all, delete-orphan")
    fx_rates = relationship("WeeklyFXRate", back_populates="snapshot", cascade="all, delete-orphan")
    entity = relationship("Entity", back_populates="snapshots")

class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    currency = Column(String, default="EUR")
    payment_run_day = Column(Integer, default=3) # 0=Mon, 3=Thu, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
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
    
    bank_account = relationship("BankAccount", back_populates="transactions")
    reconciled_invoices = relationship("Invoice", secondary="reconciliation_table", back_populates="bank_transactions")

class ReconciliationTable(Base):
    __tablename__ = "reconciliation_table"
    id = Column(Integer, primary_key=True, index=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount_allocated = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=True)
    
    canonical_id = Column(String, index=True) # Rich Fingerprint for idempotency
    source_system = Column(String, default="Excel")
    
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
    
    # Blockage & Dispute
    is_blocked = Column(Integer, default=0)
    blocked_reason = Column(String, nullable=True) # PO missing, Pricing mismatch, Delivery issue, Approval delay
    dispute_status = Column(String, default="active") # open, resolved
    assignee = Column(String, nullable=True)
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
    action = Column(String) # Create, Update, Delete, Override, Sign-off
    resource_type = Column(String) # Snapshot, Invoice, BankMatch, Scenario
    resource_id = Column(Integer, nullable=True)
    changes = Column(JSON, nullable=True) # Old/New value map

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
    
    snapshot = relationship("Snapshot", back_populates="delays")

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
    password = Column(String) # For MVP, simple string. Enterprise would use secrets manager.
    warehouse = Column(String)
    database = Column(String)
    schema_name = Column(String)
    role = Column(String, nullable=True)
    
    # Mapping configuration
    # { "table": "...", "mapping": { "internal_field": "source_column", ... } }
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

