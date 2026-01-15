"""
Connector SDK and Normalization Layer

Provides:
1. BaseConnector interface with test/extract/normalize methods
2. RawBatch and NormalizedBatch data structures
3. Normalization rules with strong typing
4. DataHealthReport for quality assessment
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Type
from datetime import datetime, timezone, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import hashlib
import json
import re
import io


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class CanonicalTable(str, Enum):
    """Canonical output tables."""
    INVOICES = "invoices"
    VENDOR_BILLS = "vendor_bills"
    BANK_TXNS = "bank_txns"
    FX_RATES = "fx_rates"


class DataQualityLevel(str, Enum):
    """Data quality assessment levels."""
    EXCELLENT = "excellent"  # 95%+ complete, no issues
    GOOD = "good"           # 85-95% complete, minor issues
    FAIR = "fair"           # 70-85% complete, some issues
    POOR = "poor"           # <70% complete, significant issues


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TestResult:
    """Result of connector test."""
    success: bool
    message: str
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    tested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RawRecord:
    """Single raw record from source."""
    source_table: str
    row_index: int
    raw_data: Dict[str, Any]
    raw_hash: str = field(default="")
    
    def __post_init__(self):
        if not self.raw_hash:
            self.raw_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute deterministic hash of raw data."""
        normalized = json.dumps(self.raw_data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass
class RawBatch:
    """Batch of raw records from extraction."""
    records: List[RawRecord]
    source_type: str
    source_name: str
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Schema info
    columns: List[str] = field(default_factory=list)
    column_types: Dict[str, str] = field(default_factory=dict)
    
    @property
    def row_count(self) -> int:
        return len(self.records)
    
    @property
    def schema_fingerprint(self) -> str:
        """Compute schema fingerprint."""
        sorted_cols = sorted(self.columns)
        schema_str = "|".join(f"{c}:{self.column_types.get(c, 'unknown')}" for c in sorted_cols)
        return hashlib.sha256(schema_str.encode()).hexdigest()


@dataclass
class NormalizedRecord:
    """Single normalized record in canonical format."""
    table: CanonicalTable
    canonical_id: str
    data: Dict[str, Any]
    source_row_index: int
    source_raw_hash: str
    
    # Typing info
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    record_date: Optional[date] = None
    due_date: Optional[date] = None
    counterparty: Optional[str] = None
    external_id: Optional[str] = None


@dataclass
class DataHealthIssue:
    """Single data health issue."""
    issue_type: str
    severity: str  # error, warning, info
    row_indices: List[int]
    message: str
    affected_amount: Optional[Decimal] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataHealthReport:
    """Comprehensive data health assessment."""
    # Completeness metrics
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    
    # Field completeness
    completeness: Dict[str, float]  # field -> % filled
    
    # Issues
    issues: List[DataHealthIssue]
    
    # Quality level
    quality_level: DataQualityLevel
    
    # Amount-weighted metrics
    total_amount: Decimal
    valid_amount: Decimal
    amount_with_issues: Decimal
    
    # Schema
    schema_fingerprint: str
    detected_columns: List[str]
    mapped_columns: Dict[str, str]  # source -> canonical
    unmapped_columns: List[str]
    
    # Timestamps
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "error_rows": self.error_rows,
            "warning_rows": self.warning_rows,
            "completeness": self.completeness,
            "issues": [
                {
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "row_count": len(i.row_indices),
                    "row_indices": i.row_indices[:10],  # First 10
                    "message": i.message,
                    "affected_amount": float(i.affected_amount) if i.affected_amount else None
                }
                for i in self.issues
            ],
            "quality_level": self.quality_level.value,
            "total_amount": float(self.total_amount),
            "valid_amount": float(self.valid_amount),
            "amount_with_issues": float(self.amount_with_issues),
            "schema_fingerprint": self.schema_fingerprint,
            "detected_columns": self.detected_columns,
            "mapped_columns": self.mapped_columns,
            "unmapped_columns": self.unmapped_columns,
            "generated_at": self.generated_at.isoformat()
        }


@dataclass
class NormalizedBatch:
    """Batch of normalized records."""
    invoices: List[NormalizedRecord] = field(default_factory=list)
    vendor_bills: List[NormalizedRecord] = field(default_factory=list)
    bank_txns: List[NormalizedRecord] = field(default_factory=list)
    fx_rates: List[NormalizedRecord] = field(default_factory=list)
    
    health_report: Optional[DataHealthReport] = None
    schema_fingerprint: str = ""
    
    @property
    def total_records(self) -> int:
        return len(self.invoices) + len(self.vendor_bills) + len(self.bank_txns) + len(self.fx_rates)
    
    def get_all_records(self) -> List[NormalizedRecord]:
        return self.invoices + self.vendor_bills + self.bank_txns + self.fx_rates


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CONNECTOR INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class BaseConnector(ABC):
    """
    Abstract base class for all data connectors.
    
    Subclasses must implement:
    - test(): Verify connectivity/credentials
    - extract(): Pull raw data from source
    - normalize(): Transform raw data to canonical format
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        entity_id: Optional[int] = None
    ):
        """
        Initialize connector.
        
        Args:
            config: Configuration dict (endpoints, credentials ref, etc.)
            entity_id: Entity this connector belongs to
        """
        self.config = config
        self.entity_id = entity_id
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return connector type identifier."""
        pass
    
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return source data type (bank_csv, erp_excel, etc.)."""
        pass
    
    @property
    @abstractmethod
    def output_tables(self) -> List[CanonicalTable]:
        """Return canonical tables this connector produces."""
        pass
    
    @abstractmethod
    def test(self) -> TestResult:
        """
        Test the connector.
        
        Returns:
            TestResult with success status and details
        """
        pass
    
    @abstractmethod
    def extract(
        self,
        data: Any,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> RawBatch:
        """
        Extract raw records from source.
        
        Args:
            data: Source data (file content, connection params, etc.)
            since: Extract records after this time
            until: Extract records before this time
        
        Returns:
            RawBatch with raw records and metadata
        """
        pass
    
    @abstractmethod
    def normalize(self, raw_batch: RawBatch) -> NormalizedBatch:
        """
        Normalize raw batch to canonical format.
        
        Args:
            raw_batch: RawBatch from extract()
        
        Returns:
            NormalizedBatch with canonical records and health report
        """
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class NormalizationLayer:
    """
    Shared normalization utilities for all connectors.
    
    Provides:
    - Column alias mapping
    - Strong typing (dates, currency, amounts)
    - Canonical ID generation
    - Health report generation
    """
    
    # Column alias mappings (source variations -> canonical)
    COLUMN_ALIASES = {
        # Amount fields
        "amount": ["amount", "amt", "total", "total_amount", "invoice_amount", "bill_amount", 
                   "transaction_amount", "value", "sum", "DMBTR", "WRBTR", "debit", "credit",
                   "Invoice Amount", "Amount (EUR)", "Amount EUR", "Betrag"],
        
        # Currency fields
        "currency": ["currency", "curr", "ccy", "currency_code", "WAERS", "curr_key",
                     "Currency", "Local Currency", "Währung"],
        
        # Date fields
        "document_date": ["document_date", "doc_date", "invoice_date", "bill_date", 
                         "transaction_date", "date", "BLDAT", "posting_date",
                         "Document Date", "Invoice Date", "Datum"],
        
        "due_date": ["due_date", "expected_due_date", "payment_due", "maturity_date",
                     "ZFBDT", "due", "Due Date", "Expected Due Date", "Fällig"],
        
        "payment_date": ["payment_date", "paid_date", "settlement_date", "clearing_date",
                         "Payment Date", "Zahldatum"],
        
        # Identifier fields
        "document_number": ["document_number", "doc_number", "doc_num", "invoice_number", 
                           "invoice_no", "bill_number", "reference", "ref", "BELNR",
                           "Document Number", "Invoice Number", "Invoice No", "Belegnr"],
        
        "external_id": ["external_id", "ext_id", "id", "transaction_id", "txn_id",
                        "External ID", "ID"],
        
        # Counterparty fields
        "customer": ["customer", "customer_name", "cust", "client", "buyer", "debtor",
                     "KUNNR", "Customer", "Customer Name", "Kunde"],
        
        "vendor": ["vendor", "vendor_name", "supplier", "creditor", "payee",
                   "LIFNR", "Vendor", "Vendor Name", "Lieferant"],
        
        "counterparty": ["counterparty", "party", "name", "merchant", "merchant_name",
                         "Counterparty", "Name"],
        
        # Category fields
        "document_type": ["document_type", "doc_type", "type", "category", "BLART",
                          "Document Type", "Type"],
        
        "country": ["country", "country_code", "LAND1", "Country", "Land"],
        
        # Description fields
        "description": ["description", "desc", "memo", "narration", "remarks", "notes",
                        "Description", "Memo", "Beschreibung"],
        
        # Project fields
        "project": ["project", "project_number", "proj", "PROJN", "Project", "Projekt"],
        "project_desc": ["project_desc", "project_description", "project_name",
                         "Project Description", "Projektbeschreibung"],
        
        # Payment terms
        "payment_terms": ["payment_terms", "terms_of_payment", "terms", "ZTERM",
                          "Payment Terms", "Terms of Payment", "Zahlungsbedingungen"],
        "payment_terms_days": ["payment_terms_days", "terms_days", "net_days",
                               "Payment Terms (in days)"],
    }
    
    # Date format patterns to try
    DATE_FORMATS = [
        "%Y-%m-%d",           # ISO: 2026-01-15
        "%d/%m/%Y",           # EU: 15/01/2026
        "%m/%d/%Y",           # US: 01/15/2026
        "%d.%m.%Y",           # German: 15.01.2026
        "%Y/%m/%d",           # Asian: 2026/01/15
        "%d-%m-%Y",           # EU dash: 15-01-2026
        "%Y%m%d",             # Compact: 20260115
        "%d %b %Y",           # 15 Jan 2026
        "%d %B %Y",           # 15 January 2026
        "%b %d, %Y",          # Jan 15, 2026
        "%B %d, %Y",          # January 15, 2026
    ]
    
    # Currency normalization
    CURRENCY_ALIASES = {
        "€": "EUR", "EURO": "EUR", "euros": "EUR",
        "$": "USD", "US$": "USD", "dollars": "USD",
        "£": "GBP", "pounds": "GBP",
        "¥": "JPY", "yen": "JPY",
        "CHF": "CHF", "francs": "CHF",
    }
    
    @classmethod
    def map_columns(cls, source_columns: List[str]) -> Dict[str, str]:
        """
        Map source columns to canonical names.
        
        Args:
            source_columns: List of source column names
        
        Returns:
            Dict mapping source column -> canonical column
        """
        mapping = {}
        normalized_source = {c: c.strip().lower().replace(" ", "_").replace("-", "_") 
                           for c in source_columns}
        
        for canonical, aliases in cls.COLUMN_ALIASES.items():
            normalized_aliases = [a.strip().lower().replace(" ", "_").replace("-", "_") 
                                 for a in aliases]
            
            for source_col, norm_col in normalized_source.items():
                if norm_col in normalized_aliases or source_col.lower() in [a.lower() for a in aliases]:
                    mapping[source_col] = canonical
                    break
        
        return mapping
    
    @classmethod
    def parse_date(cls, value: Any, locale: str = "ISO") -> Optional[date]:
        """
        Parse date with explicit locale handling.
        
        Args:
            value: Date value (string, datetime, date)
            locale: Locale hint ("ISO", "EU", "US", "DE")
        
        Returns:
            Parsed date or None
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        value_str = str(value).strip()
        
        # Order formats based on locale hint
        formats = list(cls.DATE_FORMATS)
        if locale == "EU":
            formats = ["%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y"] + formats
        elif locale == "US":
            formats = ["%m/%d/%Y"] + formats
        elif locale == "DE":
            formats = ["%d.%m.%Y"] + formats
        
        for fmt in formats:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue
        
        # Try pandas-style parsing as last resort
        try:
            import pandas as pd
            parsed = pd.to_datetime(value_str, errors='coerce')
            if pd.notna(parsed):
                return parsed.date()
        except:
            pass
        
        return None
    
    @classmethod
    def parse_amount(cls, value: Any) -> Optional[Decimal]:
        """
        Parse amount to Decimal with proper handling.
        
        Handles:
        - European format: 1.234,56
        - US format: 1,234.56
        - Currency symbols
        - Parentheses for negatives
        """
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if isinstance(value, Decimal):
            return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        value_str = str(value).strip()
        if not value_str:
            return None
        
        # Remove currency symbols
        for symbol in ['€', '$', '£', '¥', 'EUR', 'USD', 'GBP', 'CHF', 'JPY']:
            value_str = value_str.replace(symbol, '')
        
        value_str = value_str.strip()
        
        # Handle parentheses for negatives: (1,234.56) -> -1234.56
        is_negative = False
        if value_str.startswith('(') and value_str.endswith(')'):
            is_negative = True
            value_str = value_str[1:-1]
        elif value_str.startswith('-'):
            is_negative = True
            value_str = value_str[1:]
        
        # Determine format (European vs US)
        # European: 1.234,56 (period for thousands, comma for decimal)
        # US: 1,234.56 (comma for thousands, period for decimal)
        if ',' in value_str and '.' in value_str:
            if value_str.rfind(',') > value_str.rfind('.'):
                # European: 1.234,56
                value_str = value_str.replace('.', '').replace(',', '.')
            else:
                # US: 1,234.56
                value_str = value_str.replace(',', '')
        elif ',' in value_str and '.' not in value_str:
            # Could be European decimal or US thousands
            # If comma is followed by exactly 2 digits at end, treat as decimal
            if re.match(r'^[\d.]*,\d{2}$', value_str):
                value_str = value_str.replace(',', '.')
            else:
                value_str = value_str.replace(',', '')
        
        # Remove any remaining non-numeric except decimal point
        value_str = re.sub(r'[^\d.-]', '', value_str)
        
        try:
            result = Decimal(value_str).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return -result if is_negative else result
        except InvalidOperation:
            return None
    
    @classmethod
    def normalize_currency(cls, value: Any) -> Optional[str]:
        """
        Normalize currency to uppercase ISO code.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        value_str = str(value).strip().upper()
        
        # Check aliases
        if value_str in cls.CURRENCY_ALIASES:
            return cls.CURRENCY_ALIASES[value_str]
        
        # Already ISO code
        if len(value_str) == 3 and value_str.isalpha():
            return value_str
        
        return value_str[:3].upper() if value_str else None
    
    @classmethod
    def generate_canonical_id(
        cls,
        source: str,
        entity_id: Optional[int],
        doc_type: str,
        doc_number: str,
        counterparty: str,
        currency: str,
        amount: Decimal,
        doc_date: Optional[date],
        due_date: Optional[date],
        line_id: str = "0"
    ) -> str:
        """
        Generate stable canonical ID using fingerprint.
        
        ID is deterministic: same inputs always produce same ID.
        """
        def clean(val: Any) -> str:
            if val is None:
                return ""
            return str(val).strip().upper()
        
        components = [
            clean(source),
            str(entity_id or "GLOBAL"),
            clean(doc_type),
            clean(doc_number),
            clean(counterparty)[:50],  # Limit length
            clean(currency),
            f"{float(amount or 0):.2f}",
            clean(doc_date),
            clean(due_date),
            clean(line_id)
        ]
        
        raw_str = "|".join(components)
        return hashlib.sha256(raw_str.encode()).hexdigest()
    
    @classmethod
    def generate_health_report(
        cls,
        raw_batch: RawBatch,
        normalized_records: List[NormalizedRecord],
        column_mapping: Dict[str, str],
        issues: List[DataHealthIssue]
    ) -> DataHealthReport:
        """
        Generate comprehensive health report.
        """
        total_rows = raw_batch.row_count
        error_indices = set()
        warning_indices = set()
        
        for issue in issues:
            if issue.severity == "error":
                error_indices.update(issue.row_indices)
            elif issue.severity == "warning":
                warning_indices.update(issue.row_indices)
        
        valid_rows = total_rows - len(error_indices)
        error_rows = len(error_indices)
        warning_rows = len(warning_indices - error_indices)  # Warnings not already errors
        
        # Calculate completeness per field
        completeness = {}
        canonical_fields = ["amount", "currency", "document_date", "due_date", 
                          "counterparty", "document_number"]
        
        for field in canonical_fields:
            if field in column_mapping.values():
                filled = sum(1 for r in normalized_records 
                           if r.data.get(field) is not None)
                completeness[field] = (filled / total_rows * 100) if total_rows > 0 else 0.0
            else:
                completeness[field] = 0.0
        
        # Calculate amounts
        total_amount = Decimal('0')
        valid_amount = Decimal('0')
        amount_with_issues = Decimal('0')
        
        for r in normalized_records:
            if r.amount:
                total_amount += abs(r.amount)
                if r.source_row_index not in error_indices:
                    valid_amount += abs(r.amount)
                else:
                    amount_with_issues += abs(r.amount)
        
        # Determine quality level
        completeness_avg = sum(completeness.values()) / len(completeness) if completeness else 0
        valid_pct = (valid_rows / total_rows * 100) if total_rows > 0 else 100
        
        if valid_pct >= 95 and completeness_avg >= 90:
            quality_level = DataQualityLevel.EXCELLENT
        elif valid_pct >= 85 and completeness_avg >= 75:
            quality_level = DataQualityLevel.GOOD
        elif valid_pct >= 70 and completeness_avg >= 60:
            quality_level = DataQualityLevel.FAIR
        else:
            quality_level = DataQualityLevel.POOR
        
        # Unmapped columns
        mapped_source_cols = set(column_mapping.keys())
        unmapped = [c for c in raw_batch.columns if c not in mapped_source_cols]
        
        return DataHealthReport(
            total_rows=total_rows,
            valid_rows=valid_rows,
            error_rows=error_rows,
            warning_rows=warning_rows,
            completeness=completeness,
            issues=issues,
            quality_level=quality_level,
            total_amount=total_amount,
            valid_amount=valid_amount,
            amount_with_issues=amount_with_issues,
            schema_fingerprint=raw_batch.schema_fingerprint,
            detected_columns=raw_batch.columns,
            mapped_columns=column_mapping,
            unmapped_columns=unmapped
        )
