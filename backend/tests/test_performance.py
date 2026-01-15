"""
Performance Regression Tests
Tests that ensure performance doesn't degrade.
"""

import pytest
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from bank_service import generate_match_ladder, build_invoice_indexes


class TestReconciliationPerformance:
    """Performance tests for reconciliation matching"""
    
    @pytest.mark.performance
    def test_reconciliation_performance_50k_txns_200k_invoices(self, db_session, sample_entity, sample_bank_account):
        """Reconciliation with 50k transactions and 200k invoices should complete under threshold"""
        # Create 200k invoices
        print("Creating 200k invoices...")
        invoices = []
        batch_size = 1000
        
        for batch_start in range(0, 200000, batch_size):
            batch_invoices = []
            for i in range(batch_start, min(batch_start + batch_size, 200000)):
                inv = models.Invoice(
                    snapshot_id=1,  # Use snapshot 1
                    entity_id=sample_entity.id,
                    canonical_id=f"perf-inv-{i}",
                    document_number=f"INV-PERF-{i:06d}",
                    customer=f"Customer{i % 100}",
                    amount=1000.0 + (i % 1000),
                    currency="EUR",
                    expected_due_date=datetime.utcnow() + timedelta(days=30)
                )
                batch_invoices.append(inv)
            
            db_session.bulk_save_objects(batch_invoices)
            db_session.commit()
            
            if batch_start % 10000 == 0:
                print(f"  Created {batch_start + len(batch_invoices)} invoices...")
        
        # Create 50k transactions
        print("Creating 50k transactions...")
        transactions = []
        batch_size = 1000
        
        for batch_start in range(0, 50000, batch_size):
            batch_txns = []
            for i in range(batch_start, min(batch_start + batch_size, 50000)):
                txn = models.BankTransaction(
                    bank_account_id=sample_bank_account.id,
                    transaction_date=datetime.utcnow(),
                    amount=1000.0 + (i % 1000),
                    reference=f"Payment INV-PERF-{i:06d}",
                    counterparty=f"Customer{i % 100}",
                    currency="EUR",
                    is_reconciled=0
                )
                batch_txns.append(txn)
            
            db_session.bulk_save_objects(batch_txns)
            db_session.commit()
            
            if batch_start % 10000 == 0:
                print(f"  Created {batch_start + len(batch_txns)} transactions...")
        
        # Fetch all invoices for indexing
        print("Building indexes...")
        all_invoices = db_session.query(models.Invoice).filter(
            models.Invoice.entity_id == sample_entity.id,
            models.Invoice.payment_date == None
        ).all()
        
        start_index = time.time()
        indexes = build_invoice_indexes(all_invoices)
        index_time = time.time() - start_index
        print(f"Index building took {index_time:.2f}s")
        
        # Run reconciliation with performance measurement
        print("Running reconciliation...")
        start = time.time()
        results = generate_match_ladder(db_session, sample_entity.id)
        elapsed = time.time() - start
        
        print(f"Reconciliation completed in {elapsed:.2f}s")
        print(f"Total matches: {len(results)}")
        
        # Performance threshold: Should complete in under 30 seconds
        # (With indexed lookups, should be much faster)
        threshold = 30.0
        
        assert elapsed < threshold, \
            f"Reconciliation took {elapsed:.2f}s, exceeds threshold of {threshold}s. " \
            f"This suggests O(n²) performance instead of indexed lookups."
        
        # Verify indexed approach was used (index building should be fast)
        assert index_time < 5.0, \
            f"Index building took {index_time:.2f}s, suggests inefficient indexing"
    
    @pytest.mark.performance
    def test_index_building_performance(self, db_session, sample_entity):
        """Index building should be fast even with large datasets"""
        # Create 10k invoices
        invoices = []
        for i in range(10000):
            inv = models.Invoice(
                snapshot_id=1,
                entity_id=sample_entity.id,
                canonical_id=f"index-perf-{i}",
                document_number=f"INV-IDX-{i:05d}",
                customer=f"Customer{i % 50}",
                amount=1000.0 + (i % 500),
                currency="EUR"
            )
            invoices.append(inv)
        
        db_session.bulk_save_objects(invoices)
        db_session.commit()
        
        # Fetch and build indexes
        all_invoices = db_session.query(models.Invoice).filter(
            models.Invoice.entity_id == sample_entity.id
        ).all()
        
        start = time.time()
        indexes = build_invoice_indexes(all_invoices)
        elapsed = time.time() - start
        
        # Should be very fast (< 1 second for 10k invoices)
        assert elapsed < 1.0, \
            f"Index building took {elapsed:.2f}s for 10k invoices, should be < 1s"
        
        # Verify indexes were created
        assert 'by_document_number' in indexes
        assert 'by_amount' in indexes
        assert 'by_customer' in indexes







