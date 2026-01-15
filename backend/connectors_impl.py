"""
Concrete Connector Implementations

Provides:
- CSVStatementConnector: Bank CSV upload
- ExcelERPConnector: AR/AP Excel upload
- WarehouseSQLConnector: Snowflake/BigQuery stub
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, date
from decimal import Decimal
import hashlib
import io
import csv

from connector_sdk import (
    BaseConnector, TestResult, RawBatch, RawRecord, NormalizedBatch, NormalizedRecord,
    DataHealthIssue, DataHealthReport, CanonicalTable, NormalizationLayer
)


# ═══════════════════════════════════════════════════════════════════════════════
# CSV STATEMENT CONNECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class CSVStatementConnector(BaseConnector):
    """
    Connector for bank statement CSV uploads.
    
    Handles various CSV formats from different banks with:
    - Flexible delimiter detection (comma, semicolon, tab)
    - Header row detection
    - Column alias mapping
    - Strong typing for dates and amounts
    """
    
    @property
    def connector_type(self) -> str:
        return "csv_statement"
    
    @property
    def source_type(self) -> str:
        return "bank_csv"
    
    @property
    def output_tables(self) -> List[CanonicalTable]:
        return [CanonicalTable.BANK_TXNS]
    
    def test(self) -> TestResult:
        """Test that CSV parsing capabilities are available."""
        return TestResult(
            success=True,
            message="CSV connector ready",
            details={"supported_delimiters": [",", ";", "\t"]}
        )
    
    def extract(
        self,
        data: Union[bytes, str],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> RawBatch:
        """
        Extract raw records from CSV data.
        
        Args:
            data: CSV content (bytes or string)
            since: Filter records after this date
            until: Filter records before this date
        
        Returns:
            RawBatch with raw records
        """
        # Convert bytes to string
        if isinstance(data, bytes):
            # Try different encodings
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    data = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
        
        # Detect delimiter
        delimiter = self._detect_delimiter(data)
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
        
        records = []
        columns = reader.fieldnames or []
        
        for idx, row in enumerate(reader):
            records.append(RawRecord(
                source_table="bank_statement",
                row_index=idx,
                raw_data=dict(row)
            ))
        
        # Infer column types
        column_types = self._infer_column_types(records, columns)
        
        return RawBatch(
            records=records,
            source_type=self.source_type,
            source_name=self.config.get("source_name", "CSV Upload"),
            columns=columns,
            column_types=column_types,
            metadata={
                "delimiter": delimiter,
                "encoding": "auto-detected"
            }
        )
    
    def normalize(self, raw_batch: RawBatch) -> NormalizedBatch:
        """
        Normalize bank statement CSV to canonical format.
        """
        # Map columns
        column_mapping = NormalizationLayer.map_columns(raw_batch.columns)
        
        records = []
        issues = []
        locale = self.config.get("locale", "ISO")
        
        for raw_record in raw_batch.records:
            try:
                # Map raw data to canonical fields
                mapped = self._map_record(raw_record.raw_data, column_mapping)
                
                # Parse with strong typing
                amount = NormalizationLayer.parse_amount(mapped.get("amount"))
                currency = NormalizationLayer.normalize_currency(
                    mapped.get("currency") or self.config.get("default_currency", "EUR")
                )
                record_date = NormalizationLayer.parse_date(
                    mapped.get("document_date") or mapped.get("transaction_date"),
                    locale
                )
                
                # Counterparty
                counterparty = (
                    mapped.get("counterparty") or 
                    mapped.get("merchant") or 
                    mapped.get("name") or
                    "Unknown"
                )
                
                # External ID
                external_id = (
                    mapped.get("external_id") or 
                    mapped.get("transaction_id") or
                    mapped.get("reference") or
                    f"row_{raw_record.row_index}"
                )
                
                # Track issues
                if amount is None:
                    issues.append(DataHealthIssue(
                        issue_type="missing_amount",
                        severity="error",
                        row_indices=[raw_record.row_index],
                        message="Missing or invalid amount"
                    ))
                
                if record_date is None:
                    issues.append(DataHealthIssue(
                        issue_type="missing_date",
                        severity="warning",
                        row_indices=[raw_record.row_index],
                        message="Missing or invalid transaction date"
                    ))
                
                # Generate canonical ID
                canonical_id = NormalizationLayer.generate_canonical_id(
                    source=self.source_type,
                    entity_id=self.entity_id,
                    doc_type="BANK_TXN",
                    doc_number=external_id,
                    counterparty=counterparty,
                    currency=currency or "EUR",
                    amount=amount or Decimal('0'),
                    doc_date=record_date,
                    due_date=None,
                    line_id=str(raw_record.row_index)
                )
                
                # Build normalized record
                normalized = NormalizedRecord(
                    table=CanonicalTable.BANK_TXNS,
                    canonical_id=canonical_id,
                    data={
                        "transaction_id": external_id,
                        "amount": float(amount) if amount else None,
                        "currency": currency,
                        "transaction_date": record_date.isoformat() if record_date else None,
                        "counterparty": counterparty,
                        "reference": mapped.get("reference") or mapped.get("description"),
                        "category": mapped.get("category") or mapped.get("document_type"),
                        "description": mapped.get("description"),
                        "is_credit": float(amount) > 0 if amount else None
                    },
                    source_row_index=raw_record.row_index,
                    source_raw_hash=raw_record.raw_hash,
                    amount=amount,
                    currency=currency,
                    record_date=record_date,
                    counterparty=counterparty,
                    external_id=external_id
                )
                
                records.append(normalized)
                
            except Exception as e:
                issues.append(DataHealthIssue(
                    issue_type="parse_error",
                    severity="error",
                    row_indices=[raw_record.row_index],
                    message=f"Failed to parse row: {str(e)}"
                ))
        
        # Consolidate issues by type
        issues = self._consolidate_issues(issues)
        
        # Generate health report
        health_report = NormalizationLayer.generate_health_report(
            raw_batch=raw_batch,
            normalized_records=records,
            column_mapping=column_mapping,
            issues=issues
        )
        
        return NormalizedBatch(
            bank_txns=records,
            health_report=health_report,
            schema_fingerprint=raw_batch.schema_fingerprint
        )
    
    def _detect_delimiter(self, data: str) -> str:
        """Detect CSV delimiter."""
        first_lines = data.split('\n')[:5]
        sample = '\n'.join(first_lines)
        
        # Count occurrences
        counts = {
            ',': sample.count(','),
            ';': sample.count(';'),
            '\t': sample.count('\t')
        }
        
        # Return most common
        return max(counts, key=counts.get)
    
    def _infer_column_types(
        self, 
        records: List[RawRecord], 
        columns: List[str]
    ) -> Dict[str, str]:
        """Infer column types from sample data."""
        types = {}
        sample_size = min(10, len(records))
        
        for col in columns:
            values = [r.raw_data.get(col) for r in records[:sample_size] if r.raw_data.get(col)]
            
            if not values:
                types[col] = "unknown"
                continue
            
            # Check if numeric
            numeric_count = sum(1 for v in values if self._is_numeric(v))
            if numeric_count >= len(values) * 0.8:
                types[col] = "float"
                continue
            
            # Check if date
            date_count = sum(1 for v in values if NormalizationLayer.parse_date(v) is not None)
            if date_count >= len(values) * 0.8:
                types[col] = "date"
                continue
            
            types[col] = "string"
        
        return types
    
    def _is_numeric(self, value: Any) -> bool:
        """Check if value is numeric."""
        if value is None:
            return False
        try:
            float(str(value).replace(',', '.').replace(' ', ''))
            return True
        except:
            return False
    
    def _map_record(
        self, 
        raw_data: Dict[str, Any], 
        column_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Map raw data using column mapping."""
        mapped = {}
        for source_col, canonical_col in column_mapping.items():
            if source_col in raw_data:
                mapped[canonical_col] = raw_data[source_col]
        
        # Also include unmapped columns with original names
        for col, value in raw_data.items():
            if col not in column_mapping:
                mapped[col] = value
        
        return mapped
    
    def _consolidate_issues(self, issues: List[DataHealthIssue]) -> List[DataHealthIssue]:
        """Consolidate issues by type."""
        consolidated = {}
        
        for issue in issues:
            key = (issue.issue_type, issue.severity, issue.message)
            if key in consolidated:
                consolidated[key].row_indices.extend(issue.row_indices)
            else:
                consolidated[key] = issue
        
        return list(consolidated.values())


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL ERP CONNECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class ExcelERPConnector(BaseConnector):
    """
    Connector for AR/AP Excel uploads from ERP systems.
    
    Handles:
    - Multiple sheets (AR, AP, combined)
    - Various ERP export formats (SAP, NetSuite, etc.)
    - Invoice and vendor bill normalization
    """
    
    @property
    def connector_type(self) -> str:
        return "excel_erp"
    
    @property
    def source_type(self) -> str:
        return "erp_excel"
    
    @property
    def output_tables(self) -> List[CanonicalTable]:
        return [CanonicalTable.INVOICES, CanonicalTable.VENDOR_BILLS]
    
    def test(self) -> TestResult:
        """Test that Excel parsing capabilities are available."""
        try:
            import pandas as pd
            import openpyxl
            return TestResult(
                success=True,
                message="Excel connector ready",
                details={"pandas_version": pd.__version__}
            )
        except ImportError as e:
            return TestResult(
                success=False,
                message=f"Missing dependency: {str(e)}"
            )
    
    def extract(
        self,
        data: bytes,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> RawBatch:
        """
        Extract raw records from Excel data.
        """
        import pandas as pd
        
        # Load Excel
        xl = pd.ExcelFile(io.BytesIO(data))
        
        # Determine which sheet to use
        sheet_name = self.config.get("sheet_name")
        if not sheet_name:
            # Auto-detect: prefer "Data", "AR", "AP", or first sheet
            for name in ['Data', 'AR', 'AP', 'Invoices', 'Bills']:
                if name in xl.sheet_names:
                    sheet_name = name
                    break
            if not sheet_name:
                sheet_name = xl.sheet_names[0]
        
        # Read with string dtype to prevent transformations
        df = xl.parse(sheet_name, dtype=str)
        
        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        
        records = []
        columns = list(df.columns)
        
        for idx, row in df.iterrows():
            raw_data = {col: row[col] for col in columns if pd.notna(row[col])}
            records.append(RawRecord(
                source_table=sheet_name,
                row_index=idx,
                raw_data=raw_data
            ))
        
        # Infer column types
        column_types = {}
        for col in columns:
            sample = df[col].dropna().head(10)
            if sample.empty:
                column_types[col] = "unknown"
            elif sample.apply(lambda x: self._is_numeric_str(x)).mean() > 0.8:
                column_types[col] = "float"
            elif sample.apply(lambda x: NormalizationLayer.parse_date(x) is not None).mean() > 0.8:
                column_types[col] = "date"
            else:
                column_types[col] = "string"
        
        return RawBatch(
            records=records,
            source_type=self.source_type,
            source_name=self.config.get("source_name", "Excel Upload"),
            columns=columns,
            column_types=column_types,
            metadata={
                "sheet_name": sheet_name,
                "available_sheets": xl.sheet_names
            }
        )
    
    def normalize(self, raw_batch: RawBatch) -> NormalizedBatch:
        """
        Normalize Excel ERP data to canonical format.
        
        Detects AR (invoices) vs AP (vendor bills) automatically.
        """
        # Map columns
        column_mapping = NormalizationLayer.map_columns(raw_batch.columns)
        
        invoices = []
        vendor_bills = []
        issues = []
        locale = self.config.get("locale", "ISO")
        
        # Determine record type from config or auto-detect
        record_type = self.config.get("record_type")  # "ar", "ap", or None for auto
        
        for raw_record in raw_batch.records:
            try:
                # Map raw data
                mapped = self._map_record(raw_record.raw_data, column_mapping)
                
                # Parse with strong typing
                amount = NormalizationLayer.parse_amount(mapped.get("amount"))
                currency = NormalizationLayer.normalize_currency(
                    mapped.get("currency") or self.config.get("default_currency", "EUR")
                )
                doc_date = NormalizationLayer.parse_date(mapped.get("document_date"), locale)
                due_date = NormalizationLayer.parse_date(mapped.get("due_date"), locale)
                payment_date = NormalizationLayer.parse_date(mapped.get("payment_date"), locale)
                
                # Counterparty (customer for AR, vendor for AP)
                customer = mapped.get("customer")
                vendor = mapped.get("vendor")
                counterparty = customer or vendor or mapped.get("counterparty") or "Unknown"
                
                # Document number
                doc_number = (
                    mapped.get("document_number") or 
                    mapped.get("invoice_number") or
                    mapped.get("external_id") or
                    f"row_{raw_record.row_index}"
                )
                
                # Auto-detect record type if not specified
                actual_type = record_type
                if not actual_type:
                    if customer and not vendor:
                        actual_type = "ar"
                    elif vendor and not customer:
                        actual_type = "ap"
                    elif amount and amount > 0:
                        actual_type = "ar"  # Positive = receivable
                    else:
                        actual_type = "ap"  # Negative = payable
                
                # Track issues
                if amount is None:
                    issues.append(DataHealthIssue(
                        issue_type="missing_amount",
                        severity="error",
                        row_indices=[raw_record.row_index],
                        message="Missing or invalid amount"
                    ))
                
                if due_date is None:
                    issues.append(DataHealthIssue(
                        issue_type="missing_due_date",
                        severity="warning",
                        row_indices=[raw_record.row_index],
                        message="Missing or invalid due date"
                    ))
                
                # Generate canonical ID
                canonical_id = NormalizationLayer.generate_canonical_id(
                    source=self.source_type,
                    entity_id=self.entity_id,
                    doc_type="INV" if actual_type == "ar" else "BILL",
                    doc_number=doc_number,
                    counterparty=counterparty,
                    currency=currency or "EUR",
                    amount=amount or Decimal('0'),
                    doc_date=doc_date,
                    due_date=due_date
                )
                
                # Build normalized record
                if actual_type == "ar":
                    record = NormalizedRecord(
                        table=CanonicalTable.INVOICES,
                        canonical_id=canonical_id,
                        data={
                            "document_number": doc_number,
                            "customer": counterparty,
                            "amount": float(amount) if amount else None,
                            "currency": currency,
                            "document_date": doc_date.isoformat() if doc_date else None,
                            "due_date": due_date.isoformat() if due_date else None,
                            "payment_date": payment_date.isoformat() if payment_date else None,
                            "document_type": mapped.get("document_type"),
                            "project": mapped.get("project"),
                            "country": mapped.get("country"),
                            "payment_terms": mapped.get("payment_terms"),
                            "description": mapped.get("description")
                        },
                        source_row_index=raw_record.row_index,
                        source_raw_hash=raw_record.raw_hash,
                        amount=amount,
                        currency=currency,
                        record_date=doc_date,
                        due_date=due_date,
                        counterparty=counterparty,
                        external_id=doc_number
                    )
                    invoices.append(record)
                else:
                    record = NormalizedRecord(
                        table=CanonicalTable.VENDOR_BILLS,
                        canonical_id=canonical_id,
                        data={
                            "document_number": doc_number,
                            "vendor": counterparty,
                            "amount": float(amount) if amount else None,
                            "currency": currency,
                            "document_date": doc_date.isoformat() if doc_date else None,
                            "due_date": due_date.isoformat() if due_date else None,
                            "payment_date": payment_date.isoformat() if payment_date else None,
                            "document_type": mapped.get("document_type"),
                            "category": mapped.get("category"),
                            "description": mapped.get("description")
                        },
                        source_row_index=raw_record.row_index,
                        source_raw_hash=raw_record.raw_hash,
                        amount=amount,
                        currency=currency,
                        record_date=doc_date,
                        due_date=due_date,
                        counterparty=counterparty,
                        external_id=doc_number
                    )
                    vendor_bills.append(record)
                
            except Exception as e:
                issues.append(DataHealthIssue(
                    issue_type="parse_error",
                    severity="error",
                    row_indices=[raw_record.row_index],
                    message=f"Failed to parse row: {str(e)}"
                ))
        
        # Consolidate issues
        issues = self._consolidate_issues(issues)
        
        # Generate health report
        all_records = invoices + vendor_bills
        health_report = NormalizationLayer.generate_health_report(
            raw_batch=raw_batch,
            normalized_records=all_records,
            column_mapping=column_mapping,
            issues=issues
        )
        
        return NormalizedBatch(
            invoices=invoices,
            vendor_bills=vendor_bills,
            health_report=health_report,
            schema_fingerprint=raw_batch.schema_fingerprint
        )
    
    def _is_numeric_str(self, value: Any) -> bool:
        """Check if string value is numeric."""
        if value is None or str(value).strip() == '':
            return False
        try:
            val = str(value).replace(',', '.').replace(' ', '')
            float(val)
            return True
        except:
            return False
    
    def _map_record(
        self, 
        raw_data: Dict[str, Any], 
        column_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """Map raw data using column mapping."""
        mapped = {}
        for source_col, canonical_col in column_mapping.items():
            if source_col in raw_data:
                mapped[canonical_col] = raw_data[source_col]
        
        for col, value in raw_data.items():
            if col not in column_mapping:
                mapped[col] = value
        
        return mapped
    
    def _consolidate_issues(self, issues: List[DataHealthIssue]) -> List[DataHealthIssue]:
        """Consolidate issues by type."""
        consolidated = {}
        
        for issue in issues:
            key = (issue.issue_type, issue.severity, issue.message)
            if key in consolidated:
                consolidated[key].row_indices.extend(issue.row_indices)
            else:
                consolidated[key] = issue
        
        return list(consolidated.values())


# ═══════════════════════════════════════════════════════════════════════════════
# WAREHOUSE SQL CONNECTOR (STUB)
# ═══════════════════════════════════════════════════════════════════════════════

class WarehouseSQLConnector(BaseConnector):
    """
    Stub connector for data warehouses (Snowflake, BigQuery).
    
    Structure only - no real authentication or execution.
    Shows the interface for future implementation.
    """
    
    @property
    def connector_type(self) -> str:
        return "warehouse_sql"
    
    @property
    def source_type(self) -> str:
        warehouse_type = self.config.get("warehouse_type", "snowflake")
        return f"warehouse_{warehouse_type}"
    
    @property
    def output_tables(self) -> List[CanonicalTable]:
        # Depends on query configuration
        table_type = self.config.get("output_table", "invoices")
        mapping = {
            "invoices": CanonicalTable.INVOICES,
            "vendor_bills": CanonicalTable.VENDOR_BILLS,
            "bank_txns": CanonicalTable.BANK_TXNS,
            "fx_rates": CanonicalTable.FX_RATES
        }
        return [mapping.get(table_type, CanonicalTable.INVOICES)]
    
    def test(self) -> TestResult:
        """
        Test warehouse connection (stub).
        
        In real implementation, would verify:
        - Credentials
        - Network connectivity
        - Query permissions
        """
        warehouse_type = self.config.get("warehouse_type", "snowflake")
        
        # Validate required config
        required_fields = {
            "snowflake": ["account", "warehouse", "database", "schema"],
            "bigquery": ["project_id", "dataset"]
        }
        
        missing = []
        for field in required_fields.get(warehouse_type, []):
            if not self.config.get(field):
                missing.append(field)
        
        if missing:
            return TestResult(
                success=False,
                message=f"Missing required config: {', '.join(missing)}",
                details={"warehouse_type": warehouse_type, "missing_fields": missing}
            )
        
        # Stub: return success
        return TestResult(
            success=True,
            message=f"{warehouse_type.title()} connection test successful (stub)",
            latency_ms=100.0,
            details={
                "warehouse_type": warehouse_type,
                "stub": True,
                "note": "Real authentication not implemented"
            }
        )
    
    def extract(
        self,
        data: Any,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> RawBatch:
        """
        Execute SQL query and extract results (stub).
        
        Args:
            data: SQL query string or query config dict
            since: Filter records after this time
            until: Filter records before this time
        
        In real implementation, would:
        - Connect to warehouse
        - Execute query with date filters
        - Stream results in batches
        """
        query = data if isinstance(data, str) else data.get("query", "")
        
        # Stub: return empty batch with structure
        return RawBatch(
            records=[],
            source_type=self.source_type,
            source_name=self.config.get("source_name", "Warehouse Query"),
            columns=["id", "amount", "currency", "date", "counterparty", "reference"],
            column_types={
                "id": "string",
                "amount": "float",
                "currency": "string",
                "date": "date",
                "counterparty": "string",
                "reference": "string"
            },
            metadata={
                "warehouse_type": self.config.get("warehouse_type", "snowflake"),
                "query": query[:100] + "..." if len(query) > 100 else query,
                "stub": True,
                "note": "Real query execution not implemented"
            }
        )
    
    def normalize(self, raw_batch: RawBatch) -> NormalizedBatch:
        """
        Normalize warehouse query results (stub).
        
        Real implementation would follow same pattern as other connectors.
        """
        # Column mapping
        column_mapping = NormalizationLayer.map_columns(raw_batch.columns)
        
        records = []
        issues = []
        locale = self.config.get("locale", "ISO")
        output_table = self.output_tables[0]
        
        for raw_record in raw_batch.records:
            try:
                mapped = {
                    column_mapping.get(k, k): v 
                    for k, v in raw_record.raw_data.items()
                }
                
                amount = NormalizationLayer.parse_amount(mapped.get("amount"))
                currency = NormalizationLayer.normalize_currency(mapped.get("currency"))
                record_date = NormalizationLayer.parse_date(mapped.get("date"), locale)
                
                canonical_id = NormalizationLayer.generate_canonical_id(
                    source=self.source_type,
                    entity_id=self.entity_id,
                    doc_type=output_table.value.upper(),
                    doc_number=mapped.get("id", str(raw_record.row_index)),
                    counterparty=mapped.get("counterparty", "Unknown"),
                    currency=currency or "EUR",
                    amount=amount or Decimal('0'),
                    doc_date=record_date,
                    due_date=None
                )
                
                records.append(NormalizedRecord(
                    table=output_table,
                    canonical_id=canonical_id,
                    data=mapped,
                    source_row_index=raw_record.row_index,
                    source_raw_hash=raw_record.raw_hash,
                    amount=amount,
                    currency=currency,
                    record_date=record_date,
                    counterparty=mapped.get("counterparty")
                ))
                
            except Exception as e:
                issues.append(DataHealthIssue(
                    issue_type="parse_error",
                    severity="error",
                    row_indices=[raw_record.row_index],
                    message=str(e)
                ))
        
        # Generate health report
        health_report = NormalizationLayer.generate_health_report(
            raw_batch=raw_batch,
            normalized_records=records,
            column_mapping=column_mapping,
            issues=issues
        )
        
        # Build result based on output table
        result = NormalizedBatch(
            health_report=health_report,
            schema_fingerprint=raw_batch.schema_fingerprint
        )
        
        if output_table == CanonicalTable.INVOICES:
            result.invoices = records
        elif output_table == CanonicalTable.VENDOR_BILLS:
            result.vendor_bills = records
        elif output_table == CanonicalTable.BANK_TXNS:
            result.bank_txns = records
        elif output_table == CanonicalTable.FX_RATES:
            result.fx_rates = records
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTOR REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectorSDKRegistry:
    """Registry for SDK connectors."""
    
    _connectors: Dict[str, type] = {
        "csv_statement": CSVStatementConnector,
        "excel_erp": ExcelERPConnector,
        "warehouse_sql": WarehouseSQLConnector,
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
        entity_id: Optional[int] = None
    ) -> Optional[BaseConnector]:
        """Create connector instance."""
        connector_class = cls.get(connector_type)
        if not connector_class:
            return None
        return connector_class(config, entity_id)
