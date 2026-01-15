"""
Connector Interface for Data Lineage

Defines the abstract base connector and stub implementations.
Real connectors (Plaid, SAP, etc.) inherit from BaseConnector.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime, timezone
import hashlib
import json


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConnectionTestResult:
    """Result of testing a connection."""
    success: bool
    message: str
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedRow:
    """A single row extracted from source."""
    source_table: str
    source_row_id: Optional[str]
    raw_payload: Dict[str, Any]
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def raw_hash(self) -> str:
        """Compute hash of raw payload."""
        normalized = json.dumps(self.raw_payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass
class SchemaInfo:
    """Schema information from source."""
    columns: List[Dict[str, str]]  # [{"name": "amount", "type": "float"}, ...]
    primary_key: Optional[List[str]] = None
    source_table: Optional[str] = None
    
    @property
    def fingerprint(self) -> str:
        """Compute schema fingerprint."""
        sorted_cols = sorted(self.columns, key=lambda c: c.get("name", ""))
        normalized = [
            f"{c.get('name', '').lower()}:{c.get('type', 'unknown').lower()}"
            for c in sorted_cols
        ]
        schema_str = "|".join(normalized)
        return hashlib.sha256(schema_str.encode()).hexdigest()


@dataclass
class SyncProgress:
    """Progress update during sync."""
    rows_extracted: int
    rows_processed: int
    rows_error: int
    current_table: Optional[str] = None
    message: Optional[str] = None


@dataclass
class SyncResult:
    """Final result of a sync operation."""
    success: bool
    rows_extracted: int
    rows_normalized: int
    rows_loaded: int
    rows_skipped: int
    rows_error: int
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    schema_info: Optional[SchemaInfo] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CONNECTOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class BaseConnector(ABC):
    """
    Abstract base class for all data connectors.
    
    Subclasses implement:
    - test_connection(): Verify credentials and connectivity
    - get_schema(): Retrieve source schema for drift detection
    - extract(): Stream rows from source
    - normalize(): Transform raw rows to canonical format
    """
    
    def __init__(self, config: Dict[str, Any], secret_ref: Optional[str] = None):
        """
        Initialize connector.
        
        Args:
            config: Non-sensitive configuration (endpoints, filters, etc.)
            secret_ref: Reference to secrets (never raw credentials)
        """
        self.config = config
        self.secret_ref = secret_ref
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return connector type identifier."""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return source data type (ar_invoice, bank_txn, etc.)."""
        pass
    
    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """
        Test the connection.
        
        Returns:
            ConnectionTestResult with success status and message
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> SchemaInfo:
        """
        Get schema information from source.
        
        Returns:
            SchemaInfo with columns and fingerprint
        """
        pass
    
    @abstractmethod
    def extract(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        batch_size: int = 1000
    ) -> Generator[ExtractedRow, None, None]:
        """
        Extract rows from source.
        
        Args:
            since: Extract records modified after this time
            until: Extract records modified before this time
            batch_size: Rows per batch for pagination
        
        Yields:
            ExtractedRow for each source record
        """
        pass
    
    @abstractmethod
    def normalize(self, raw_row: ExtractedRow) -> Dict[str, Any]:
        """
        Normalize a raw row to canonical format.
        
        Args:
            raw_row: ExtractedRow from extract()
        
        Returns:
            Dict with canonical fields:
            - record_type: "Invoice", "VendorBill", "BankTxn", "FXRate"
            - canonical_id: Deterministic ID for idempotency
            - amount, currency, record_date, due_date, counterparty, external_id
            - payload: Full normalized payload
        """
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# STUB CONNECTORS
# ═══════════════════════════════════════════════════════════════════════════════

class StubBankConnector(BaseConnector):
    """
    Stub bank connector for testing.
    Simulates Plaid-like bank transaction extraction.
    """
    
    @property
    def connector_type(self) -> str:
        return "bank_stub"
    
    @property
    def source_type(self) -> str:
        return "bank_txn"
    
    def test_connection(self) -> ConnectionTestResult:
        """Simulate connection test."""
        return ConnectionTestResult(
            success=True,
            message="Stub bank connection successful",
            latency_ms=42.0,
            details={"stub": True, "version": "1.0"}
        )
    
    def get_schema(self) -> SchemaInfo:
        """Return stub bank schema."""
        return SchemaInfo(
            columns=[
                {"name": "transaction_id", "type": "string"},
                {"name": "account_id", "type": "string"},
                {"name": "date", "type": "date"},
                {"name": "amount", "type": "float"},
                {"name": "currency", "type": "string"},
                {"name": "name", "type": "string"},
                {"name": "merchant_name", "type": "string"},
                {"name": "category", "type": "string"},
                {"name": "pending", "type": "boolean"},
            ],
            primary_key=["transaction_id"],
            source_table="transactions"
        )
    
    def extract(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        batch_size: int = 1000
    ) -> Generator[ExtractedRow, None, None]:
        """Generate stub bank transactions."""
        # Generate sample transactions
        sample_txns = [
            {
                "transaction_id": "txn_001",
                "account_id": "acc_123",
                "date": "2026-01-10",
                "amount": -1500.00,
                "currency": "EUR",
                "name": "ACME Corp Payment",
                "merchant_name": "ACME Corp",
                "category": "supplier_payment",
                "pending": False
            },
            {
                "transaction_id": "txn_002",
                "account_id": "acc_123",
                "date": "2026-01-11",
                "amount": 5000.00,
                "currency": "EUR",
                "name": "Customer XYZ",
                "merchant_name": None,
                "category": "customer_receipt",
                "pending": False
            },
            {
                "transaction_id": "txn_003",
                "account_id": "acc_123",
                "date": "2026-01-12",
                "amount": -250.00,
                "currency": "EUR",
                "name": "Office Supplies Inc",
                "merchant_name": "Office Supplies Inc",
                "category": "supplier_payment",
                "pending": True
            },
        ]
        
        for txn in sample_txns:
            yield ExtractedRow(
                source_table="transactions",
                source_row_id=txn["transaction_id"],
                raw_payload=txn
            )
    
    def normalize(self, raw_row: ExtractedRow) -> Dict[str, Any]:
        """Normalize bank transaction to canonical format."""
        payload = raw_row.raw_payload
        
        amount = float(payload.get("amount", 0))
        currency = payload.get("currency", "EUR")
        record_date = payload.get("date")
        counterparty = payload.get("merchant_name") or payload.get("name", "Unknown")
        external_id = payload.get("transaction_id")
        
        # Generate canonical ID
        canonical_id = hashlib.sha256(
            f"BankTxn|{external_id}|{record_date}|{amount}|{currency}".encode()
        ).hexdigest()
        
        return {
            "record_type": "BankTxn",
            "canonical_id": canonical_id,
            "amount": amount,
            "currency": currency,
            "record_date": record_date,
            "due_date": None,
            "counterparty": counterparty,
            "external_id": external_id,
            "payload": {
                "transaction_id": external_id,
                "account_id": payload.get("account_id"),
                "amount": amount,
                "currency": currency,
                "date": record_date,
                "counterparty": counterparty,
                "category": payload.get("category"),
                "pending": payload.get("pending", False),
                "reference": payload.get("name")
            }
        }


class StubERPConnector(BaseConnector):
    """
    Stub ERP connector for testing.
    Simulates SAP-like invoice extraction.
    """
    
    @property
    def connector_type(self) -> str:
        return "erp_stub"
    
    @property
    def source_type(self) -> str:
        return "ar_invoice"
    
    def test_connection(self) -> ConnectionTestResult:
        """Simulate connection test."""
        return ConnectionTestResult(
            success=True,
            message="Stub ERP connection successful",
            latency_ms=150.0,
            details={"stub": True, "system": "SAP-like"}
        )
    
    def get_schema(self) -> SchemaInfo:
        """Return stub invoice schema."""
        return SchemaInfo(
            columns=[
                {"name": "BELNR", "type": "string"},  # Document number
                {"name": "BUKRS", "type": "string"},  # Company code
                {"name": "KUNNR", "type": "string"},  # Customer
                {"name": "WAERS", "type": "string"},  # Currency
                {"name": "DMBTR", "type": "float"},   # Amount
                {"name": "BLDAT", "type": "date"},    # Document date
                {"name": "ZFBDT", "type": "date"},    # Due date
                {"name": "ZLSCH", "type": "string"},  # Payment method
            ],
            primary_key=["BELNR", "BUKRS"],
            source_table="BSID"  # SAP open items
        )
    
    def extract(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        batch_size: int = 1000
    ) -> Generator[ExtractedRow, None, None]:
        """Generate stub invoices."""
        sample_invoices = [
            {
                "BELNR": "90000001",
                "BUKRS": "1000",
                "KUNNR": "CUST001",
                "WAERS": "EUR",
                "DMBTR": 10000.00,
                "BLDAT": "2026-01-05",
                "ZFBDT": "2026-02-05",
                "ZLSCH": "T"
            },
            {
                "BELNR": "90000002",
                "BUKRS": "1000",
                "KUNNR": "CUST002",
                "WAERS": "USD",
                "DMBTR": 5500.00,
                "BLDAT": "2026-01-08",
                "ZFBDT": "2026-02-08",
                "ZLSCH": "T"
            },
            {
                "BELNR": "90000003",
                "BUKRS": "1000",
                "KUNNR": "CUST001",
                "WAERS": "EUR",
                "DMBTR": 2500.00,
                "BLDAT": "2026-01-10",
                "ZFBDT": "2026-02-10",
                "ZLSCH": "S"
            },
        ]
        
        for inv in sample_invoices:
            yield ExtractedRow(
                source_table="BSID",
                source_row_id=f"{inv['BELNR']}_{inv['BUKRS']}",
                raw_payload=inv
            )
    
    def normalize(self, raw_row: ExtractedRow) -> Dict[str, Any]:
        """Normalize invoice to canonical format."""
        payload = raw_row.raw_payload
        
        amount = float(payload.get("DMBTR", 0))
        currency = payload.get("WAERS", "EUR")
        record_date = payload.get("BLDAT")
        due_date = payload.get("ZFBDT")
        counterparty = payload.get("KUNNR", "Unknown")
        external_id = payload.get("BELNR")
        company = payload.get("BUKRS", "1000")
        
        # Generate canonical ID
        canonical_id = hashlib.sha256(
            f"Invoice|{company}|{external_id}|{counterparty}|{currency}|{amount}|{record_date}|{due_date}".encode()
        ).hexdigest()
        
        return {
            "record_type": "Invoice",
            "canonical_id": canonical_id,
            "amount": amount,
            "currency": currency,
            "record_date": record_date,
            "due_date": due_date,
            "counterparty": counterparty,
            "external_id": external_id,
            "payload": {
                "document_number": external_id,
                "company_code": company,
                "customer": counterparty,
                "amount": amount,
                "currency": currency,
                "document_date": record_date,
                "due_date": due_date,
                "payment_method": payload.get("ZLSCH")
            }
        }


class StubVendorBillConnector(BaseConnector):
    """
    Stub AP connector for testing.
    Simulates vendor bill extraction.
    """
    
    @property
    def connector_type(self) -> str:
        return "ap_stub"
    
    @property
    def source_type(self) -> str:
        return "ap_bill"
    
    def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(
            success=True,
            message="Stub AP connection successful",
            latency_ms=100.0,
            details={"stub": True}
        )
    
    def get_schema(self) -> SchemaInfo:
        return SchemaInfo(
            columns=[
                {"name": "bill_id", "type": "string"},
                {"name": "vendor_id", "type": "string"},
                {"name": "vendor_name", "type": "string"},
                {"name": "amount", "type": "float"},
                {"name": "currency", "type": "string"},
                {"name": "bill_date", "type": "date"},
                {"name": "due_date", "type": "date"},
                {"name": "status", "type": "string"},
            ],
            primary_key=["bill_id"],
            source_table="vendor_bills"
        )
    
    def extract(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        batch_size: int = 1000
    ) -> Generator[ExtractedRow, None, None]:
        sample_bills = [
            {
                "bill_id": "BILL001",
                "vendor_id": "V001",
                "vendor_name": "ACME Supplies",
                "amount": 2500.00,
                "currency": "EUR",
                "bill_date": "2026-01-05",
                "due_date": "2026-02-05",
                "status": "open"
            },
            {
                "bill_id": "BILL002",
                "vendor_id": "V002",
                "vendor_name": "Tech Services Ltd",
                "amount": 8000.00,
                "currency": "EUR",
                "bill_date": "2026-01-08",
                "due_date": "2026-01-20",
                "status": "open"
            },
        ]
        
        for bill in sample_bills:
            yield ExtractedRow(
                source_table="vendor_bills",
                source_row_id=bill["bill_id"],
                raw_payload=bill
            )
    
    def normalize(self, raw_row: ExtractedRow) -> Dict[str, Any]:
        payload = raw_row.raw_payload
        
        amount = float(payload.get("amount", 0))
        currency = payload.get("currency", "EUR")
        record_date = payload.get("bill_date")
        due_date = payload.get("due_date")
        counterparty = payload.get("vendor_name", "Unknown")
        external_id = payload.get("bill_id")
        
        canonical_id = hashlib.sha256(
            f"VendorBill|{external_id}|{counterparty}|{currency}|{amount}|{record_date}|{due_date}".encode()
        ).hexdigest()
        
        return {
            "record_type": "VendorBill",
            "canonical_id": canonical_id,
            "amount": amount,
            "currency": currency,
            "record_date": record_date,
            "due_date": due_date,
            "counterparty": counterparty,
            "external_id": external_id,
            "payload": payload
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTOR REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectorRegistry:
    """Registry of available connectors."""
    
    _connectors: Dict[str, type] = {
        "bank_stub": StubBankConnector,
        "erp_stub": StubERPConnector,
        "ap_stub": StubVendorBillConnector,
    }
    
    @classmethod
    def register(cls, connector_type: str, connector_class: type):
        """Register a connector type."""
        cls._connectors[connector_type] = connector_class
    
    @classmethod
    def get(cls, connector_type: str) -> Optional[type]:
        """Get connector class by type."""
        return cls._connectors.get(connector_type)
    
    @classmethod
    def list_types(cls) -> List[str]:
        """List available connector types."""
        return list(cls._connectors.keys())
    
    @classmethod
    def create(
        cls,
        connector_type: str,
        config: Dict[str, Any],
        secret_ref: Optional[str] = None
    ) -> Optional[BaseConnector]:
        """Create connector instance."""
        connector_class = cls.get(connector_type)
        if not connector_class:
            return None
        return connector_class(config, secret_ref)
