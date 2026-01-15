"""
Tests for Connector SDK and Normalization Layer

Verifies:
1. Messy headers are mapped correctly
2. Canonical IDs are stable regardless of row order
3. Strong typing works for dates, amounts, currencies
4. Health reports are accurate
"""

import pytest
from decimal import Decimal
from datetime import date
import io
import csv

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connector_sdk import (
    NormalizationLayer, RawBatch, RawRecord, NormalizedBatch,
    CanonicalTable, DataQualityLevel
)
from connectors_impl import (
    CSVStatementConnector, ExcelERPConnector, WarehouseSQLConnector
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════════════════════════════

MESSY_CSV_HEADERS = """Transaction ID,  Amount (EUR) ,DATE,COUNTERPARTY,Memo/Description,curr_key
TXN001,1500.00,2026-01-15,ACME Corp,Payment received,EUR
TXN002,-250.50,15/01/2026,Supplier Ltd,Office supplies,EUR
TXN003,"2,500.00",01/15/2026,Customer XYZ,Invoice payment,EUR
TXN004,(1000.00),2026-01-15,Tax Authority,Tax payment,EUR
TXN005,€3.456,78,15.01.2026,German Client,German format,EUR
"""

MESSY_CSV_HEADERS_ALT = """  ref  , total_amount ,transaction_date, merchant_name , category
REF001,999.99,2026-01-10,Shop ABC,retail
REF002,1234.56,10/01/2026,Service Co,service
"""

# Same data, different row order
SHUFFLED_CSV = """Transaction ID,Amount (EUR),DATE,COUNTERPARTY,curr_key
TXN003,2500.00,2026-01-15,Customer XYZ,EUR
TXN001,1500.00,2026-01-15,ACME Corp,EUR
TXN002,-250.50,2026-01-15,Supplier Ltd,EUR
"""

ORIGINAL_ORDER_CSV = """Transaction ID,Amount (EUR),DATE,COUNTERPARTY,curr_key
TXN001,1500.00,2026-01-15,ACME Corp,EUR
TXN002,-250.50,2026-01-15,Supplier Ltd,EUR
TXN003,2500.00,2026-01-15,Customer XYZ,EUR
"""


# ═══════════════════════════════════════════════════════════════════════════════
# COLUMN MAPPING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestColumnMapping:
    """Test column alias mapping with messy headers."""
    
    def test_map_standard_columns(self):
        """Test mapping of standard column names."""
        columns = ["amount", "currency", "date", "counterparty", "reference"]
        mapping = NormalizationLayer.map_columns(columns)
        
        assert mapping["amount"] == "amount"
        assert mapping["currency"] == "currency"
        assert mapping["counterparty"] == "counterparty"
    
    def test_map_columns_with_spaces(self):
        """Test mapping columns with leading/trailing spaces."""
        columns = ["  Amount  ", " Currency ", "  Due Date  "]
        mapping = NormalizationLayer.map_columns(columns)
        
        assert "  Amount  " in mapping or "Amount" in str(mapping)
    
    def test_map_columns_with_mixed_case(self):
        """Test mapping columns with mixed case."""
        columns = ["AMOUNT", "Currency", "DUE_DATE", "customer_name"]
        mapping = NormalizationLayer.map_columns(columns)
        
        # Should map regardless of case
        assert any("amount" in v for v in mapping.values())
        assert any("customer" in v for v in mapping.values())
    
    def test_map_erp_style_columns(self):
        """Test mapping SAP-style column names."""
        columns = ["BELNR", "DMBTR", "WAERS", "BLDAT", "ZFBDT", "KUNNR"]
        mapping = NormalizationLayer.map_columns(columns)
        
        # SAP field mappings
        assert "BELNR" in mapping  # Document number
        assert "DMBTR" in mapping  # Amount
        assert "WAERS" in mapping  # Currency
        assert "BLDAT" in mapping  # Document date
    
    def test_map_alternative_aliases(self):
        """Test mapping alternative column name variations."""
        columns = ["Invoice Amount", "Local Currency", "Expected Due Date", "Customer Name"]
        mapping = NormalizationLayer.map_columns(columns)
        
        assert any("amount" in v for v in mapping.values())
        assert any("currency" in v for v in mapping.values())
        assert any("due_date" in v for v in mapping.values())
        assert any("customer" in v for v in mapping.values())
    
    def test_map_messy_real_world_headers(self):
        """Test mapping messy real-world headers."""
        columns = ["Transaction ID", "  Amount (EUR) ", "DATE", "COUNTERPARTY", "Memo/Description", "curr_key"]
        mapping = NormalizationLayer.map_columns(columns)
        
        # Should find amount and currency mappings
        mapped_values = list(mapping.values())
        assert "amount" in mapped_values or any("amount" in str(v) for v in mapped_values)


# ═══════════════════════════════════════════════════════════════════════════════
# DATE PARSING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDateParsing:
    """Test date parsing with various formats and locales."""
    
    def test_parse_iso_date(self):
        """Test ISO format: YYYY-MM-DD."""
        result = NormalizationLayer.parse_date("2026-01-15")
        assert result == date(2026, 1, 15)
    
    def test_parse_eu_date(self):
        """Test EU format: DD/MM/YYYY."""
        result = NormalizationLayer.parse_date("15/01/2026", locale="EU")
        assert result == date(2026, 1, 15)
    
    def test_parse_us_date(self):
        """Test US format: MM/DD/YYYY."""
        result = NormalizationLayer.parse_date("01/15/2026", locale="US")
        assert result == date(2026, 1, 15)
    
    def test_parse_german_date(self):
        """Test German format: DD.MM.YYYY."""
        result = NormalizationLayer.parse_date("15.01.2026", locale="DE")
        assert result == date(2026, 1, 15)
    
    def test_parse_compact_date(self):
        """Test compact format: YYYYMMDD."""
        result = NormalizationLayer.parse_date("20260115")
        assert result == date(2026, 1, 15)
    
    def test_parse_datetime_object(self):
        """Test parsing datetime object."""
        from datetime import datetime
        dt = datetime(2026, 1, 15, 12, 30, 0)
        result = NormalizationLayer.parse_date(dt)
        assert result == date(2026, 1, 15)
    
    def test_parse_date_object(self):
        """Test parsing date object (passthrough)."""
        d = date(2026, 1, 15)
        result = NormalizationLayer.parse_date(d)
        assert result == date(2026, 1, 15)
    
    def test_parse_empty_date(self):
        """Test parsing empty values."""
        assert NormalizationLayer.parse_date(None) is None
        assert NormalizationLayer.parse_date("") is None
        assert NormalizationLayer.parse_date("   ") is None
    
    def test_parse_invalid_date(self):
        """Test parsing invalid dates."""
        assert NormalizationLayer.parse_date("not-a-date") is None
        assert NormalizationLayer.parse_date("99/99/9999") is None


# ═══════════════════════════════════════════════════════════════════════════════
# AMOUNT PARSING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAmountParsing:
    """Test amount parsing with various formats."""
    
    def test_parse_simple_amount(self):
        """Test simple decimal amount."""
        result = NormalizationLayer.parse_amount("1500.00")
        assert result == Decimal("1500.00")
    
    def test_parse_us_format(self):
        """Test US format: 1,234.56."""
        result = NormalizationLayer.parse_amount("1,234.56")
        assert result == Decimal("1234.56")
    
    def test_parse_european_format(self):
        """Test European format: 1.234,56."""
        result = NormalizationLayer.parse_amount("1.234,56")
        assert result == Decimal("1234.56")
    
    def test_parse_european_comma_decimal(self):
        """Test European comma decimal: 1234,56."""
        result = NormalizationLayer.parse_amount("1234,56")
        assert result == Decimal("1234.56")
    
    def test_parse_negative_amount(self):
        """Test negative amount."""
        result = NormalizationLayer.parse_amount("-1500.00")
        assert result == Decimal("-1500.00")
    
    def test_parse_parentheses_negative(self):
        """Test parentheses for negative: (1500.00)."""
        result = NormalizationLayer.parse_amount("(1500.00)")
        assert result == Decimal("-1500.00")
    
    def test_parse_with_currency_symbol(self):
        """Test amount with currency symbol."""
        assert NormalizationLayer.parse_amount("€1500.00") == Decimal("1500.00")
        assert NormalizationLayer.parse_amount("$1,234.56") == Decimal("1234.56")
        assert NormalizationLayer.parse_amount("£999.99") == Decimal("999.99")
    
    def test_parse_integer(self):
        """Test integer values."""
        result = NormalizationLayer.parse_amount(1500)
        assert result == Decimal("1500.00")
    
    def test_parse_float(self):
        """Test float values."""
        result = NormalizationLayer.parse_amount(1500.5)
        assert result == Decimal("1500.50")
    
    def test_parse_decimal(self):
        """Test Decimal passthrough."""
        result = NormalizationLayer.parse_amount(Decimal("1500.00"))
        assert result == Decimal("1500.00")
    
    def test_parse_empty_amount(self):
        """Test empty values."""
        assert NormalizationLayer.parse_amount(None) is None
        assert NormalizationLayer.parse_amount("") is None


# ═══════════════════════════════════════════════════════════════════════════════
# CURRENCY NORMALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCurrencyNormalization:
    """Test currency normalization."""
    
    def test_normalize_iso_code(self):
        """Test ISO currency code."""
        assert NormalizationLayer.normalize_currency("EUR") == "EUR"
        assert NormalizationLayer.normalize_currency("USD") == "USD"
        assert NormalizationLayer.normalize_currency("GBP") == "GBP"
    
    def test_normalize_lowercase(self):
        """Test lowercase currency code."""
        assert NormalizationLayer.normalize_currency("eur") == "EUR"
        assert NormalizationLayer.normalize_currency("usd") == "USD"
    
    def test_normalize_symbol(self):
        """Test currency symbols."""
        assert NormalizationLayer.normalize_currency("€") == "EUR"
        assert NormalizationLayer.normalize_currency("$") == "USD"
        assert NormalizationLayer.normalize_currency("£") == "GBP"
    
    def test_normalize_alias(self):
        """Test currency aliases."""
        assert NormalizationLayer.normalize_currency("EURO") == "EUR"
        assert NormalizationLayer.normalize_currency("euros") == "EUR"
    
    def test_normalize_empty(self):
        """Test empty values."""
        assert NormalizationLayer.normalize_currency(None) is None
        assert NormalizationLayer.normalize_currency("") is None


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL ID TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalId:
    """Test canonical ID generation for idempotency."""
    
    def test_canonical_id_deterministic(self):
        """Test that same inputs produce same canonical ID."""
        id1 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="TXN001",
            counterparty="ACME Corp",
            currency="EUR",
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        id2 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="TXN001",
            counterparty="ACME Corp",
            currency="EUR",
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        assert id1 == id2, "Same inputs must produce same canonical ID"
    
    def test_canonical_id_case_insensitive(self):
        """Test that canonical ID is case-insensitive."""
        id1 = NormalizationLayer.generate_canonical_id(
            source="BANK_CSV",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="TXN001",
            counterparty="ACME Corp",
            currency="EUR",
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        id2 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="bank_txn",
            doc_number="txn001",
            counterparty="acme corp",
            currency="eur",
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        assert id1 == id2, "Canonical ID should be case-insensitive"
    
    def test_canonical_id_different_with_different_inputs(self):
        """Test that different inputs produce different canonical IDs."""
        id1 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="TXN001",
            counterparty="ACME Corp",
            currency="EUR",
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        # Different amount
        id2 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="TXN001",
            counterparty="ACME Corp",
            currency="EUR",
            amount=Decimal("1500.01"),  # Different!
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        assert id1 != id2, "Different amounts must produce different canonical IDs"
    
    def test_canonical_id_whitespace_handling(self):
        """Test that whitespace is handled consistently."""
        id1 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="TXN001",
            counterparty="ACME Corp",
            currency="EUR",
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        id2 = NormalizationLayer.generate_canonical_id(
            source="bank_csv",
            entity_id=1,
            doc_type="BANK_TXN",
            doc_number="  TXN001  ",  # Whitespace
            counterparty="  ACME Corp  ",  # Whitespace
            currency="  EUR  ",  # Whitespace
            amount=Decimal("1500.00"),
            doc_date=date(2026, 1, 15),
            due_date=None
        )
        
        assert id1 == id2, "Whitespace should be trimmed"


# ═══════════════════════════════════════════════════════════════════════════════
# CSV CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSVStatementConnector:
    """Test CSVStatementConnector with messy data."""
    
    def test_extract_with_messy_headers(self):
        """Test extraction handles messy headers."""
        connector = CSVStatementConnector({"locale": "ISO"}, entity_id=1)
        raw_batch = connector.extract(MESSY_CSV_HEADERS)
        
        assert raw_batch.row_count == 5
        assert len(raw_batch.columns) > 0
    
    def test_normalize_produces_canonical_schema(self):
        """Test normalization produces canonical schema."""
        connector = CSVStatementConnector({"locale": "ISO"}, entity_id=1)
        raw_batch = connector.extract(MESSY_CSV_HEADERS)
        normalized = connector.normalize(raw_batch)
        
        # Should have bank transactions
        assert len(normalized.bank_txns) > 0
        
        # Each record should have canonical fields
        for record in normalized.bank_txns:
            assert record.canonical_id is not None
            assert len(record.canonical_id) == 64  # SHA256 hex
            assert record.table == CanonicalTable.BANK_TXNS
    
    def test_canonical_ids_stable_regardless_of_row_order(self):
        """Test that canonical IDs are the same regardless of row order."""
        connector = CSVStatementConnector({"locale": "ISO"}, entity_id=1)
        
        # Process original order
        raw_original = connector.extract(ORIGINAL_ORDER_CSV)
        normalized_original = connector.normalize(raw_original)
        
        # Process shuffled order
        raw_shuffled = connector.extract(SHUFFLED_CSV)
        normalized_shuffled = connector.normalize(raw_shuffled)
        
        # Get canonical IDs
        original_ids = {r.external_id: r.canonical_id for r in normalized_original.bank_txns}
        shuffled_ids = {r.external_id: r.canonical_id for r in normalized_shuffled.bank_txns}
        
        # Same transactions should have same canonical IDs
        for txn_id in original_ids:
            assert txn_id in shuffled_ids, f"Transaction {txn_id} missing in shuffled"
            assert original_ids[txn_id] == shuffled_ids[txn_id], \
                f"Canonical ID for {txn_id} differs between original and shuffled order"
    
    def test_health_report_generated(self):
        """Test that health report is generated."""
        connector = CSVStatementConnector({"locale": "ISO"}, entity_id=1)
        raw_batch = connector.extract(MESSY_CSV_HEADERS)
        normalized = connector.normalize(raw_batch)
        
        assert normalized.health_report is not None
        assert normalized.health_report.total_rows == 5
        assert normalized.health_report.schema_fingerprint is not None
    
    def test_alternative_column_names(self):
        """Test handling alternative column name variations."""
        connector = CSVStatementConnector({"locale": "ISO"}, entity_id=1)
        raw_batch = connector.extract(MESSY_CSV_HEADERS_ALT)
        normalized = connector.normalize(raw_batch)
        
        assert len(normalized.bank_txns) == 2
        
        # Should have mapped columns correctly
        for record in normalized.bank_txns:
            assert record.amount is not None
            assert record.counterparty is not None


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExcelERPConnector:
    """Test ExcelERPConnector."""
    
    def test_connector_available(self):
        """Test that Excel connector is available."""
        connector = ExcelERPConnector({"locale": "ISO"}, entity_id=1)
        result = connector.test()
        
        # Should succeed if pandas/openpyxl available
        assert result.success or "Missing dependency" in result.message


# ═══════════════════════════════════════════════════════════════════════════════
# WAREHOUSE CONNECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWarehouseSQLConnector:
    """Test WarehouseSQLConnector stub."""
    
    def test_stub_test_succeeds(self):
        """Test that stub test succeeds with valid config."""
        config = {
            "warehouse_type": "snowflake",
            "account": "test_account",
            "warehouse": "test_wh",
            "database": "test_db",
            "schema": "test_schema"
        }
        connector = WarehouseSQLConnector(config, entity_id=1)
        result = connector.test()
        
        assert result.success
        assert "stub" in result.details
    
    def test_stub_test_fails_missing_config(self):
        """Test that stub test fails with missing config."""
        config = {"warehouse_type": "snowflake"}  # Missing required fields
        connector = WarehouseSQLConnector(config, entity_id=1)
        result = connector.test()
        
        assert not result.success
        assert "Missing" in result.message
    
    def test_stub_extract_returns_empty(self):
        """Test that stub extract returns empty batch."""
        config = {"warehouse_type": "snowflake"}
        connector = WarehouseSQLConnector(config, entity_id=1)
        
        raw_batch = connector.extract("SELECT * FROM test")
        
        assert raw_batch.row_count == 0
        assert raw_batch.metadata.get("stub") == True


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEndToEndNormalization:
    """End-to-end normalization tests."""
    
    def test_full_pipeline_csv(self):
        """Test full CSV pipeline: extract -> normalize -> validate."""
        connector = CSVStatementConnector(
            {"locale": "ISO", "default_currency": "EUR"},
            entity_id=1
        )
        
        # Extract
        raw_batch = connector.extract(MESSY_CSV_HEADERS)
        assert raw_batch.row_count > 0
        
        # Normalize
        normalized = connector.normalize(raw_batch)
        
        # Validate output
        assert len(normalized.bank_txns) > 0
        assert normalized.health_report is not None
        assert normalized.schema_fingerprint is not None
        
        # All records have required fields
        for record in normalized.bank_txns:
            assert record.canonical_id is not None
            assert record.table == CanonicalTable.BANK_TXNS
            assert record.source_raw_hash is not None
    
    def test_idempotency_across_multiple_runs(self):
        """Test that multiple runs produce same canonical IDs."""
        connector = CSVStatementConnector(
            {"locale": "ISO", "default_currency": "EUR"},
            entity_id=1
        )
        
        # Run multiple times
        results = []
        for _ in range(3):
            raw_batch = connector.extract(ORIGINAL_ORDER_CSV)
            normalized = connector.normalize(raw_batch)
            ids = sorted([r.canonical_id for r in normalized.bank_txns])
            results.append(ids)
        
        # All runs should produce same IDs
        assert results[0] == results[1] == results[2], \
            "Multiple runs should produce identical canonical IDs"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
