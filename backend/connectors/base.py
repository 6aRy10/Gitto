"""
Gitto Connector SDK - Base Classes

This module defines the interface that all connectors must implement.
Connectors handle: test → extract → normalize → load
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Iterator
from datetime import datetime
from enum import Enum
import hashlib
import json


class ConnectorType(Enum):
    """Supported connector types."""
    # Bank Connectors
    BANK_MT940 = "bank_mt940"
    BANK_BAI2 = "bank_bai2"
    BANK_CSV = "bank_csv"
    BANK_API = "bank_api"
    BANK_PLAID = "bank_plaid"
    BANK_NORDIGEN = "bank_nordigen"
    
    # ERP/Accounting Connectors
    ERP_NETSUITE = "erp_netsuite"
    ERP_SAP = "erp_sap"
    ERP_QUICKBOOKS = "erp_quickbooks"
    ERP_XERO = "erp_xero"
    
    # Payment Processors
    PAYMENTS = "payments"
    PAYMENTS_STRIPE = "payments_stripe"
    PAYMENTS_SQUARE = "payments_square"
    
    # AP/Procurement
    AP_COUPA = "ap_coupa"
    AP_TIPALTI = "ap_tipalti"
    AP_BILLCOM = "ap_billcom"
    
    # Payroll
    PAYROLL_WORKDAY = "payroll_workday"
    PAYROLL_ADP = "payroll_adp"
    PAYROLL_GUSTO = "payroll_gusto"
    
    # Data Warehouses
    WAREHOUSE_SNOWFLAKE = "warehouse_snowflake"
    WAREHOUSE_BIGQUERY = "warehouse_bigquery"
    
    # Manual
    MANUAL_UPLOAD = "manual_upload"


class SyncMode(Enum):
    """How to handle existing data."""
    FULL_REPLACE = "full_replace"  # Replace all data from this source
    INCREMENTAL = "incremental"    # Append/update since cursor
    SNAPSHOT = "snapshot"          # Create new snapshot, preserve old


@dataclass
class SyncContext:
    """Context passed to connector during sync."""
    connection_id: int
    entity_id: Optional[int]
    sync_run_id: int
    
    # Incremental sync support
    cursor: Optional[str] = None  # Last sync position
    since_timestamp: Optional[datetime] = None
    
    # Configuration
    sync_mode: SyncMode = SyncMode.SNAPSHOT
    dry_run: bool = False
    
    # Source profile (field mappings)
    field_mappings: Dict[str, str] = field(default_factory=dict)
    transform_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedRecord:
    """A single record extracted from source system."""
    source_id: str  # Unique ID in source system
    record_type: str  # 'bank_txn', 'invoice', 'vendor_bill', etc.
    data: Dict[str, Any]  # Raw extracted data
    
    # Metadata
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    source_checksum: Optional[str] = None  # For change detection
    
    def compute_checksum(self) -> str:
        """Compute deterministic checksum of record data."""
        content = json.dumps(self.data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass 
class NormalizedRecord:
    """A record normalized to Gitto's canonical schema."""
    canonical_id: str  # Gitto's stable identifier
    record_type: str
    data: Dict[str, Any]  # Normalized to canonical field names
    
    # Lineage
    source_id: str
    source_system: str
    source_checksum: str
    
    # Data quality flags
    quality_issues: List[str] = field(default_factory=list)
    is_complete: bool = True


@dataclass
class ConnectorResult:
    """Result of a connector operation."""
    success: bool
    message: str
    
    # Metrics
    records_extracted: int = 0
    records_normalized: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    
    # For incremental sync
    new_cursor: Optional[str] = None
    
    # Errors (if any)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class BaseConnector(ABC):
    """
    Base class for all Gitto connectors.
    
    Subclasses must implement:
    - test_connection(): Verify credentials and connectivity
    - extract(): Pull records from source system
    - normalize(): Transform to canonical schema
    
    Optionally override:
    - get_schema(): Return expected source schema
    - get_sync_cursor(): Get current sync position
    """
    
    connector_type: ConnectorType
    display_name: str
    description: str
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration.
        
        Args:
            config: Connection configuration (credentials, endpoints, etc.)
                    Sensitive values should be references, not plaintext.
        """
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate that required config keys are present."""
        pass
    
    @abstractmethod
    def test_connection(self) -> ConnectorResult:
        """
        Test that the connection is valid and working.
        
        Returns:
            ConnectorResult with success=True if connection works.
        """
        pass
    
    @abstractmethod
    def extract(self, context: SyncContext) -> Iterator[ExtractedRecord]:
        """
        Extract records from the source system.
        
        Args:
            context: Sync context with cursor, entity, etc.
            
        Yields:
            ExtractedRecord for each record in source.
        """
        pass
    
    @abstractmethod
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """
        Normalize an extracted record to Gitto's canonical schema.
        
        Args:
            record: Raw extracted record
            context: Sync context with field mappings
            
        Returns:
            NormalizedRecord with canonical field names
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Return the expected source schema.
        
        Override to provide schema discovery.
        """
        return {}
    
    def get_sync_cursor(self) -> Optional[str]:
        """
        Get current sync position for incremental sync.
        
        Override to support incremental extraction.
        """
        return None
    
    def sync(self, context: SyncContext) -> ConnectorResult:
        """
        Execute a full sync operation: extract → normalize → yield.
        
        This is the main entry point for running a sync.
        """
        result = ConnectorResult(success=True, message="Sync started")
        
        try:
            for extracted in self.extract(context):
                result.records_extracted += 1
                
                try:
                    normalized = self.normalize(extracted, context)
                    result.records_normalized += 1
                    
                    if normalized.quality_issues:
                        result.warnings.extend(normalized.quality_issues)
                        
                except Exception as e:
                    result.warnings.append(f"Failed to normalize record {extracted.source_id}: {str(e)}")
                    continue
            
            result.message = f"Extracted {result.records_extracted}, normalized {result.records_normalized}"
            result.new_cursor = self.get_sync_cursor()
            
        except Exception as e:
            result.success = False
            result.message = f"Sync failed: {str(e)}"
            result.errors.append(str(e))
        
        return result


class FileConnector(BaseConnector):
    """
    Base class for file-based connectors (MT940, BAI2, CSV).
    
    Subclasses implement parse_file() to handle specific formats.
    """
    
    @abstractmethod
    def parse_file(self, content: bytes) -> Iterator[ExtractedRecord]:
        """
        Parse file content and yield extracted records.
        
        Args:
            content: Raw file bytes
            
        Yields:
            ExtractedRecord for each transaction/record in file
        """
        pass
    
    def extract(self, context: SyncContext) -> Iterator[ExtractedRecord]:
        """
        Extract records from file content stored in config.
        """
        file_content = self.config.get('file_content')
        if not file_content:
            raise ValueError("file_content required in config")
        
        yield from self.parse_file(file_content)


class APIConnector(BaseConnector):
    """
    Base class for API-based connectors (NetSuite, QuickBooks, Xero).
    
    Subclasses implement authenticate() and fetch_records().
    """
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the API.
        
        Returns:
            True if authentication succeeded
        """
        pass
    
    @abstractmethod
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """
        Fetch records from API.
        
        Args:
            context: Sync context with cursor for pagination
            
        Yields:
            Raw API response records
        """
        pass
    
    def extract(self, context: SyncContext) -> Iterator[ExtractedRecord]:
        """
        Extract records via API.
        """
        if not self.authenticate():
            raise ConnectionError("Authentication failed")
        
        for raw_record in self.fetch_records(context):
            yield ExtractedRecord(
                source_id=str(raw_record.get('id', '')),
                record_type=self._get_record_type(),
                data=raw_record,
                extracted_at=datetime.utcnow()
            )
    
    @abstractmethod
    def _get_record_type(self) -> str:
        """Return the record type this connector extracts."""
        pass

