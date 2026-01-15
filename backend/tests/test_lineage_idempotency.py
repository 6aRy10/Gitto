"""
Unit Tests for Data Lineage Idempotency

Verifies that:
1. Re-loading the same dataset cannot create duplicate canonical rows
2. The UNIQUE(dataset_id, canonical_id) constraint is enforced
3. Idempotent syncs skip duplicates gracefully
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Import models
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lineage_models import (
    Base, LineageConnection, SyncRun, LineageDataset, RawRecord, CanonicalRecord,
    ConnectionStatus, SyncStatus, RecordType, generate_dataset_id
)
from connector_interface import (
    ConnectorRegistry, StubBankConnector, StubERPConnector, ExtractedRow
)
from lineage_service import LineageService


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def lineage_service(db_session):
    """Create a LineageService instance."""
    return LineageService(db_session)


@pytest.fixture
def test_connection(db_session, lineage_service):
    """Create a test connection."""
    return lineage_service.create_connection(
        entity_id=1,
        connection_type="bank_stub",
        name="Test Bank Connection",
        config={"test": True},
        description="Test connection for idempotency tests"
    )


@pytest.fixture
def test_dataset(db_session, test_connection):
    """Create a test dataset."""
    dataset = LineageDataset(
        entity_id=1,
        source_type="bank_txn",
        source_summary_json={"test": True},
        schema_fingerprint="abc123"
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)
    return dataset


# ═══════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanonicalIdempotency:
    """Test that canonical records enforce idempotency."""
    
    def test_unique_constraint_prevents_duplicate_canonical_ids(self, db_session, test_dataset):
        """
        Test that UNIQUE(dataset_id, canonical_id) constraint prevents duplicates.
        """
        # Create first canonical record
        record1 = CanonicalRecord(
            dataset_id=test_dataset.id,
            record_type=RecordType.BANK_TXN.value,
            canonical_id="test_canonical_123",
            payload_json={"test": "data1"},
            amount=1000.0,
            currency="EUR"
        )
        db_session.add(record1)
        db_session.commit()
        
        # Attempt to create duplicate with same canonical_id
        record2 = CanonicalRecord(
            dataset_id=test_dataset.id,
            record_type=RecordType.BANK_TXN.value,
            canonical_id="test_canonical_123",  # Same canonical_id!
            payload_json={"test": "data2"},
            amount=2000.0,
            currency="EUR"
        )
        db_session.add(record2)
        
        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_same_canonical_id_different_dataset_allowed(self, db_session):
        """
        Test that same canonical_id can exist in different datasets.
        (Each sync creates a new dataset, so this should be allowed.)
        """
        # Create two datasets
        dataset1 = LineageDataset(
            entity_id=1,
            source_type="bank_txn",
            schema_fingerprint="abc123"
        )
        dataset2 = LineageDataset(
            entity_id=1,
            source_type="bank_txn",
            schema_fingerprint="abc123"
        )
        db_session.add_all([dataset1, dataset2])
        db_session.commit()
        
        # Create records with same canonical_id in different datasets
        record1 = CanonicalRecord(
            dataset_id=dataset1.id,
            record_type=RecordType.BANK_TXN.value,
            canonical_id="shared_canonical_id",
            payload_json={"dataset": 1},
            amount=1000.0
        )
        record2 = CanonicalRecord(
            dataset_id=dataset2.id,
            record_type=RecordType.BANK_TXN.value,
            canonical_id="shared_canonical_id",  # Same canonical_id
            payload_json={"dataset": 2},
            amount=1000.0
        )
        
        db_session.add_all([record1, record2])
        db_session.commit()  # Should succeed
        
        # Verify both exist
        count = db_session.query(CanonicalRecord).filter(
            CanonicalRecord.canonical_id == "shared_canonical_id"
        ).count()
        assert count == 2
    
    def test_canonical_id_deterministic(self):
        """
        Test that canonical ID generation is deterministic.
        Same inputs should always produce the same canonical_id.
        """
        id1 = CanonicalRecord.generate_canonical_id(
            record_type="Invoice",
            source="SAP",
            entity_id=1,
            doc_type="INV",
            doc_number="90000001",
            counterparty="CUST001",
            currency="EUR",
            amount=10000.0,
            doc_date="2026-01-05",
            due_date="2026-02-05"
        )
        
        id2 = CanonicalRecord.generate_canonical_id(
            record_type="Invoice",
            source="SAP",
            entity_id=1,
            doc_type="INV",
            doc_number="90000001",
            counterparty="CUST001",
            currency="EUR",
            amount=10000.0,
            doc_date="2026-01-05",
            due_date="2026-02-05"
        )
        
        assert id1 == id2, "Canonical ID should be deterministic"
    
    def test_canonical_id_changes_with_different_inputs(self):
        """
        Test that different inputs produce different canonical IDs.
        """
        id1 = CanonicalRecord.generate_canonical_id(
            record_type="Invoice",
            source="SAP",
            entity_id=1,
            doc_type="INV",
            doc_number="90000001",
            counterparty="CUST001",
            currency="EUR",
            amount=10000.0,
            doc_date="2026-01-05",
            due_date="2026-02-05"
        )
        
        # Change amount
        id2 = CanonicalRecord.generate_canonical_id(
            record_type="Invoice",
            source="SAP",
            entity_id=1,
            doc_type="INV",
            doc_number="90000001",
            counterparty="CUST001",
            currency="EUR",
            amount=10001.0,  # Different amount
            doc_date="2026-01-05",
            due_date="2026-02-05"
        )
        
        assert id1 != id2, "Different amounts should produce different canonical IDs"


class TestSyncIdempotency:
    """Test that sync operations handle duplicates gracefully."""
    
    def test_sync_skips_duplicates(self, db_session, lineage_service, test_connection):
        """
        Test that running the same sync twice skips duplicates.
        """
        # First sync
        sync_run_id1, error1 = lineage_service.start_sync(
            connection_id=test_connection.id,
            triggered_by="test",
            background=False
        )
        assert error1 is None
        
        # Get first sync results
        sync_run1 = lineage_service.get_sync_run(sync_run_id1)
        first_loaded = sync_run1.rows_loaded
        
        assert first_loaded > 0, "First sync should load rows"
        
        # Second sync (same data)
        sync_run_id2, error2 = lineage_service.start_sync(
            connection_id=test_connection.id,
            triggered_by="test_resync",
            background=False
        )
        assert error2 is None
        
        # Get second sync results
        sync_run2 = lineage_service.get_sync_run(sync_run_id2)
        
        # Second sync should have skipped duplicates
        assert sync_run2.rows_skipped > 0, "Second sync should skip duplicates"
    
    def test_multiple_syncs_no_duplicate_canonical_records(self, db_session, lineage_service, test_connection):
        """
        Test that running multiple syncs doesn't create duplicate canonical records.
        """
        # Run sync 3 times
        for i in range(3):
            sync_run_id, error = lineage_service.start_sync(
                connection_id=test_connection.id,
                triggered_by=f"test_{i}",
                background=False
            )
            assert error is None
        
        # Get all canonical records
        all_records = db_session.query(CanonicalRecord).all()
        
        # Get unique canonical IDs
        canonical_ids = [r.canonical_id for r in all_records]
        unique_ids = set(canonical_ids)
        
        # Should have no duplicates within each dataset
        # (duplicates across datasets are allowed)
        for dataset_id in {r.dataset_id for r in all_records}:
            dataset_records = [r for r in all_records if r.dataset_id == dataset_id]
            dataset_canonical_ids = [r.canonical_id for r in dataset_records]
            assert len(dataset_canonical_ids) == len(set(dataset_canonical_ids)), \
                f"Dataset {dataset_id} should have no duplicate canonical IDs"


class TestRawRecordDeduplication:
    """Test raw record hash-based deduplication."""
    
    def test_raw_hash_deterministic(self):
        """Test that raw hash is deterministic."""
        from connector_interface import ExtractedRow
        
        payload = {"amount": 1000.0, "currency": "EUR", "date": "2026-01-10"}
        
        row1 = ExtractedRow(
            source_table="transactions",
            source_row_id="txn_001",
            raw_payload=payload
        )
        
        row2 = ExtractedRow(
            source_table="transactions",
            source_row_id="txn_001",
            raw_payload=payload
        )
        
        assert row1.raw_hash == row2.raw_hash, "Same payload should produce same hash"
    
    def test_raw_hash_changes_with_payload(self):
        """Test that raw hash changes with payload."""
        from connector_interface import ExtractedRow
        
        row1 = ExtractedRow(
            source_table="transactions",
            source_row_id="txn_001",
            raw_payload={"amount": 1000.0}
        )
        
        row2 = ExtractedRow(
            source_table="transactions",
            source_row_id="txn_001",
            raw_payload={"amount": 1001.0}
        )
        
        assert row1.raw_hash != row2.raw_hash, "Different payload should produce different hash"


class TestSchemaFingerprint:
    """Test schema fingerprint for drift detection."""
    
    def test_fingerprint_deterministic(self):
        """Test that schema fingerprint is deterministic."""
        columns = [
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "date", "type": "date"}
        ]
        
        fp1 = LineageDataset.compute_schema_fingerprint(columns)
        fp2 = LineageDataset.compute_schema_fingerprint(columns)
        
        assert fp1 == fp2, "Same columns should produce same fingerprint"
    
    def test_fingerprint_order_independent(self):
        """Test that column order doesn't affect fingerprint."""
        columns1 = [
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "date", "type": "date"}
        ]
        
        columns2 = [
            {"name": "date", "type": "date"},
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"}
        ]
        
        fp1 = LineageDataset.compute_schema_fingerprint(columns1)
        fp2 = LineageDataset.compute_schema_fingerprint(columns2)
        
        assert fp1 == fp2, "Column order should not affect fingerprint"
    
    def test_fingerprint_changes_with_columns(self):
        """Test that fingerprint changes when columns change."""
        columns1 = [
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"}
        ]
        
        columns2 = [
            {"name": "amount", "type": "float"},
            {"name": "currency", "type": "string"},
            {"name": "date", "type": "date"}  # Added column
        ]
        
        fp1 = LineageDataset.compute_schema_fingerprint(columns1)
        fp2 = LineageDataset.compute_schema_fingerprint(columns2)
        
        assert fp1 != fp2, "Different columns should produce different fingerprint"
    
    def test_fingerprint_changes_with_types(self):
        """Test that fingerprint changes when column types change."""
        columns1 = [
            {"name": "amount", "type": "float"}
        ]
        
        columns2 = [
            {"name": "amount", "type": "string"}  # Type changed
        ]
        
        fp1 = LineageDataset.compute_schema_fingerprint(columns1)
        fp2 = LineageDataset.compute_schema_fingerprint(columns2)
        
        assert fp1 != fp2, "Different types should produce different fingerprint"


class TestDatasetIdGeneration:
    """Test dataset ID generation."""
    
    def test_dataset_id_format(self):
        """Test that dataset ID has expected format."""
        dataset_id = generate_dataset_id()
        assert dataset_id.startswith("ds_"), "Dataset ID should start with 'ds_'"
        assert len(dataset_id) == 15, "Dataset ID should be 15 characters (ds_ + 12 hex)"
    
    def test_dataset_id_unique(self):
        """Test that dataset IDs are unique."""
        ids = [generate_dataset_id() for _ in range(100)]
        assert len(ids) == len(set(ids)), "Dataset IDs should be unique"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
