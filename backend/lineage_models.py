"""
Data Lineage + SyncRun Models

Provides full traceability from raw source data to canonical records:
- Connection: Data source configuration
- SyncRun: Execution audit trail
- Dataset: Versioned data batch
- RawRecord: Extracted raw data
- CanonicalRecord: Normalized records
- EvidenceRef: Links to evidence for audit
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text,
    UniqueConstraint, CheckConstraint, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime
import enum
import hashlib
import json
import uuid


Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionType(str, enum.Enum):
    """Supported connection types."""
    BANK_PLAID = "bank_plaid"
    BANK_MT940 = "bank_mt940"
    BANK_BAI2 = "bank_bai2"
    BANK_CAMT053 = "bank_camt053"
    ERP_SAP = "erp_sap"
    ERP_NETSUITE = "erp_netsuite"
    ERP_QUICKBOOKS = "erp_quickbooks"
    ERP_XERO = "erp_xero"
    WAREHOUSE_SNOWFLAKE = "warehouse_snowflake"
    WAREHOUSE_BIGQUERY = "warehouse_bigquery"
    FILE_EXCEL = "file_excel"
    FILE_CSV = "file_csv"
    API_CUSTOM = "api_custom"


class ConnectionStatus(str, enum.Enum):
    """Connection health status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING_SETUP = "pending_setup"


class SyncStatus(str, enum.Enum):
    """Sync run status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # Some rows failed
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecordType(str, enum.Enum):
    """Canonical record types."""
    INVOICE = "Invoice"
    VENDOR_BILL = "VendorBill"
    BANK_TXN = "BankTxn"
    FX_RATE = "FXRate"


class EvidenceKind(str, enum.Enum):
    """Evidence reference types."""
    DATASET = "dataset"
    RAW_RECORD = "raw_record"
    CANONICAL_RECORD = "canonical_record"
    INVOICE = "invoice"
    VENDOR_BILL = "vendor_bill"
    BANK_TXN = "bank_txn"
    RECONCILIATION = "reconciliation"
    FORECAST_ROW = "forecast_row"


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class LineageConnection(Base):
    """
    Data source connection configuration.
    
    Stores connection metadata, credentials reference, and health status.
    Never stores raw credentials - uses secret_ref to reference external secrets.
    """
    __tablename__ = "lineage_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, nullable=True, index=True)  # FK to entities
    
    # Connection identity
    type = Column(String(50), nullable=False)  # ConnectionType value
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(30), default=ConnectionStatus.PENDING_SETUP.value, nullable=False)
    status_message = Column(String(500), nullable=True)
    
    # Configuration (non-sensitive)
    config_json = Column(JSON, nullable=True)  # e.g., {"endpoint": "...", "warehouse": "..."}
    
    # Credentials reference (never store raw secrets)
    secret_ref = Column(String(200), nullable=True)  # e.g., "vault://secrets/plaid-credentials"
    
    # Sync configuration
    sync_schedule = Column(String(50), nullable=True)  # cron expression
    sync_enabled = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_test_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    sync_runs = relationship("SyncRun", back_populates="connection", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'error', 'pending_setup')",
            name="ck_lineage_connection_status"
        ),
        Index("ix_lineage_connection_entity_type", "entity_id", "type"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SYNC RUN MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class SyncRun(Base):
    """
    Audit trail of sync execution.
    
    Every ingest/sync produces a SyncRun record tracking:
    - Timing (started_at, finished_at)
    - Status (pending, running, success, partial, failed)
    - Metrics (rows extracted, normalized, loaded)
    - Errors and warnings
    """
    __tablename__ = "sync_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("lineage_connections.id"), nullable=False, index=True)
    
    # Timing
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(30), default=SyncStatus.PENDING.value, nullable=False)
    
    # Metrics
    rows_extracted = Column(Integer, default=0)
    rows_normalized = Column(Integer, default=0)
    rows_loaded = Column(Integer, default=0)
    rows_skipped = Column(Integer, default=0)
    rows_error = Column(Integer, default=0)
    
    # Error/Warning tracking
    errors_json = Column(JSON, nullable=True)  # [{row_idx, error_type, message, raw_data}]
    warning_count = Column(Integer, default=0)
    warnings_json = Column(JSON, nullable=True)  # [{row_idx, warning_type, message}]
    
    # Trigger info
    triggered_by = Column(String(100), nullable=True)  # user, schedule, webhook
    
    # Relationships
    connection = relationship("LineageConnection", back_populates="sync_runs")
    datasets = relationship("LineageDataset", back_populates="sync_run", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'success', 'partial', 'failed', 'cancelled')",
            name="ck_sync_run_status"
        ),
        Index("ix_sync_run_connection_status", "connection_id", "status"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DATASET MODEL
# ═══════════════════════════════════════════════════════════════════════════════

def generate_dataset_id() -> str:
    """Generate deterministic dataset ID."""
    return f"ds_{uuid.uuid4().hex[:12]}"


class LineageDataset(Base):
    """
    Versioned data batch from a sync run.
    
    Every ingest produces a Dataset with:
    - Unique dataset_id for reference
    - Source summary (what was extracted)
    - Schema fingerprint for drift detection
    - Aggregate metrics (row count, total amount)
    """
    __tablename__ = "lineage_datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(String(50), unique=True, nullable=False, index=True, default=generate_dataset_id)
    entity_id = Column(Integer, nullable=True, index=True)
    sync_run_id = Column(Integer, ForeignKey("sync_runs.id"), nullable=True, index=True)
    
    # Source summary
    source_type = Column(String(50), nullable=False)  # "ar_invoice", "ap_bill", "bank_txn", "fx_rate"
    source_summary_json = Column(JSON, nullable=True)  # {"connection_id": ..., "filters": ..., "date_range": ...}
    
    # Schema tracking for drift detection
    schema_fingerprint = Column(String(64), nullable=True)  # SHA256 of normalized column set + types
    schema_columns_json = Column(JSON, nullable=True)  # [{"name": "amount", "type": "float"}, ...]
    
    # Aggregate metrics
    row_count = Column(Integer, default=0)
    amount_total_base = Column(Float, default=0.0)  # Total amount in base currency
    currency = Column(String(10), nullable=True)  # Base currency
    
    # Date range covered
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    sync_run = relationship("SyncRun", back_populates="datasets")
    raw_records = relationship("RawRecord", back_populates="dataset", cascade="all, delete-orphan")
    canonical_records = relationship("CanonicalRecord", back_populates="dataset", cascade="all, delete-orphan")
    
    @staticmethod
    def compute_schema_fingerprint(columns: list) -> str:
        """
        Compute schema fingerprint from column definitions.
        
        Args:
            columns: List of {"name": str, "type": str} dicts
        
        Returns:
            SHA256 hash of normalized schema
        """
        # Sort by name for determinism
        sorted_cols = sorted(columns, key=lambda c: c.get("name", ""))
        # Normalize types
        normalized = [
            f"{c.get('name', '').lower()}:{c.get('type', 'unknown').lower()}"
            for c in sorted_cols
        ]
        schema_str = "|".join(normalized)
        return hashlib.sha256(schema_str.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# RAW RECORD MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class RawRecord(Base):
    """
    Raw extracted data before normalization.
    
    Stores the original payload from the source system for:
    - Audit trail
    - Debugging transformation issues
    - Re-processing capability
    """
    __tablename__ = "raw_records"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("lineage_datasets.id"), nullable=False, index=True)
    
    # Source identification
    source_table = Column(String(200), nullable=True)  # e.g., "BKPF", "transactions", "Sheet1"
    source_row_id = Column(String(200), nullable=True)  # Original row identifier if available
    
    # Raw payload
    raw_payload_json = Column(JSON, nullable=False)
    raw_hash = Column(String(64), nullable=False, index=True)  # SHA256 of payload for dedup
    
    # Extraction metadata
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Processing status
    is_processed = Column(Integer, default=0)
    processing_error = Column(String(500), nullable=True)
    
    # Relationships
    dataset = relationship("LineageDataset", back_populates="raw_records")
    canonical_records = relationship("CanonicalRecord", back_populates="raw_record")
    
    __table_args__ = (
        Index("ix_raw_record_dataset_hash", "dataset_id", "raw_hash"),
    )
    
    @staticmethod
    def compute_raw_hash(payload: dict) -> str:
        """Compute hash of raw payload for deduplication."""
        # Sort keys for determinism
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL RECORD MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class CanonicalRecord(Base):
    """
    Normalized record in canonical format.
    
    Every raw record is transformed into one or more canonical records.
    The canonical_id ensures idempotency - re-loading same data won't duplicate.
    """
    __tablename__ = "canonical_records"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("lineage_datasets.id"), nullable=False, index=True)
    raw_record_id = Column(Integer, ForeignKey("raw_records.id"), nullable=True, index=True)
    
    # Record classification
    record_type = Column(String(20), nullable=False)  # RecordType value
    
    # Canonical identity (for idempotency)
    canonical_id = Column(String(100), nullable=False, index=True)
    
    # Normalized payload
    payload_json = Column(JSON, nullable=False)
    
    # Key fields extracted for querying
    amount = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    record_date = Column(DateTime, nullable=True)  # Transaction/invoice date
    due_date = Column(DateTime, nullable=True)
    counterparty = Column(String(200), nullable=True)  # Customer/Vendor name
    external_id = Column(String(200), nullable=True)  # Document number, reference
    
    # Processing metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    dataset = relationship("LineageDataset", back_populates="canonical_records")
    raw_record = relationship("RawRecord", back_populates="canonical_records")
    
    __table_args__ = (
        # CRITICAL: Idempotency constraint - same canonical_id cannot exist twice in a dataset
        UniqueConstraint('dataset_id', 'canonical_id', name='uix_canonical_record_dataset_canonical'),
        CheckConstraint(
            "record_type IN ('Invoice', 'VendorBill', 'BankTxn', 'FXRate')",
            name="ck_canonical_record_type"
        ),
        Index("ix_canonical_record_type_date", "record_type", "record_date"),
        Index("ix_canonical_record_counterparty", "counterparty"),
    )
    
    @staticmethod
    def generate_canonical_id(
        record_type: str,
        source: str,
        entity_id: int,
        doc_type: str,
        doc_number: str,
        counterparty: str,
        currency: str,
        amount: float,
        doc_date: str,
        due_date: str,
        line_id: str = "0"
    ) -> str:
        """
        Generate deterministic canonical ID for idempotency.
        
        Same input will always produce the same canonical_id.
        """
        def clean(val):
            if val is None:
                return ""
            return str(val).strip().upper()
        
        components = [
            clean(record_type),
            clean(source),
            str(entity_id or "GLOBAL"),
            clean(doc_type),
            clean(doc_number),
            clean(counterparty),
            clean(currency),
            f"{float(amount or 0):.2f}",
            clean(doc_date),
            clean(due_date),
            clean(line_id)
        ]
        
        raw_str = "|".join(components)
        return hashlib.sha256(raw_str.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE REF MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class LineageEvidenceRef(Base):
    """
    Evidence reference for audit trail.
    
    Links any audit/trust item to its source evidence:
    - Which dataset did this come from?
    - Which raw record?
    - Which canonical record?
    """
    __tablename__ = "lineage_evidence_refs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Evidence type and reference
    kind = Column(String(30), nullable=False)  # EvidenceKind value
    ref_id = Column(Integer, nullable=False)
    
    # Additional metadata
    metadata_json = Column(JSON, nullable=True)  # e.g., {"row_number": 42, "sheet": "Data"}
    
    # Context (what this evidence supports)
    context_type = Column(String(50), nullable=True)  # "trust_metric", "invariant", "reconciliation"
    context_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint(
            "kind IN ('dataset', 'raw_record', 'canonical_record', 'invoice', 'vendor_bill', 'bank_txn', 'reconciliation', 'forecast_row')",
            name="ck_evidence_ref_kind"
        ),
        Index("ix_evidence_ref_kind_ref", "kind", "ref_id"),
        Index("ix_evidence_ref_context", "context_type", "context_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaDriftEvent(Base):
    """
    Records schema changes detected between dataset versions.
    """
    __tablename__ = "schema_drift_events"
    
    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("lineage_connections.id"), nullable=False, index=True)
    
    # Dataset references
    old_dataset_id = Column(Integer, ForeignKey("lineage_datasets.id"), nullable=True)
    new_dataset_id = Column(Integer, ForeignKey("lineage_datasets.id"), nullable=False)
    
    # Drift details
    old_fingerprint = Column(String(64), nullable=True)
    new_fingerprint = Column(String(64), nullable=False)
    
    # Changes detected
    added_columns_json = Column(JSON, nullable=True)  # [{"name": "new_col", "type": "string"}]
    removed_columns_json = Column(JSON, nullable=True)
    type_changes_json = Column(JSON, nullable=True)  # [{"name": "amount", "old_type": "string", "new_type": "float"}]
    
    # Severity
    severity = Column(String(20), default="info")  # info, warning, error
    
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
