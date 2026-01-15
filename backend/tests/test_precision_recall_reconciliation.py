"""
Precision/Recall Metrics for Reconciliation
Not just "it matches" — measure actual accuracy metrics.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from bank_service import generate_match_ladder, find_deterministic_match_optimized, build_invoice_indexes


class TestReconciliationPrecisionRecall:
    """
    Precision/Recall metrics for reconciliation matching.
    Builds a labeled mini dataset and computes real metrics.
    """
    
    def test_deterministic_match_precision(self, db_session, sample_entity, sample_bank_account):
        """
        Deterministic match precision should be ≈ 100%
        Precision = True Positives / (True Positives + False Positives)
        """
        # Create labeled test dataset: invoices with known matches
        invoices = []
        true_matches = []  # (invoice, transaction) pairs that should match
        
        # Create snapshot for these invoices
        snapshot = models.Snapshot(
            name="Precision Test Snapshot",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow()
        )
        snapshot.is_locked = 0
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)
        
        for i in range(20):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"precision-inv-{i}",
                document_number=f"INV-PREC-{i:03d}",
                customer=f"Customer{i % 5}",
                amount=1000.0 + (i * 100),
                currency="EUR",
                expected_due_date=datetime.utcnow() + timedelta(days=30)
            )
            invoices.append(inv)
            
            # Create matching transaction
            # Use exact invoice number in reference for deterministic matching
            txn = models.BankTransaction(
                bank_account_id=sample_bank_account.id,
                transaction_date=datetime.utcnow(),
                amount=inv.amount,  # Use exact invoice amount
                reference=f"INV-PREC-{i:03d}",  # Exact invoice number for deterministic match
                counterparty=f"Customer{i % 5}",
                currency="EUR",
                is_reconciled=0
            )
            db_session.add(txn)
            true_matches.append((inv, txn))
        
        db_session.add_all(invoices)
        db_session.commit()
        
        # Refresh invoices to get their IDs
        for inv in invoices:
            db_session.refresh(inv)
        
        # Verify invoices are in the database and have correct entity_id
        invoice_count = db_session.query(models.Invoice).filter(
            models.Invoice.entity_id == sample_entity.id,
            models.Invoice.payment_date == None
        ).count()
        
        # Verify transactions are in the database
        txn_count = db_session.query(models.BankTransaction).filter(
            models.BankTransaction.bank_account_id == sample_bank_account.id,
            models.BankTransaction.is_reconciled == 0
        ).count()
        
        # Debug: Check what we have before reconciliation
        invoice_count = db_session.query(models.Invoice).filter(
            models.Invoice.entity_id == sample_entity.id,
            models.Invoice.payment_date == None
        ).count()
        txn_count = db_session.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankTransaction.is_reconciled == 0,
            models.BankAccount.entity_id == sample_entity.id
        ).count()
        
        # Run reconciliation
        results = generate_match_ladder(db_session, sample_entity.id)
        
        # Refresh all transactions
        for _, expected_txn in true_matches:
            db_session.refresh(expected_txn)
        
        # Calculate precision
        true_positives = 0
        false_positives = 0
        
        # Track which transactions we've already counted
        counted_txns = set()
        
        for inv, expected_txn in true_matches:
            db_session.refresh(expected_txn)
            inv_id = inv.id  # Store ID before potential deletion
            
            if expected_txn.is_reconciled == 1:
                # Check if it matched the correct invoice
                recon = db_session.query(models.ReconciliationTable).filter(
                    models.ReconciliationTable.bank_transaction_id == expected_txn.id,
                    models.ReconciliationTable.invoice_id == inv_id
                ).first()
                
                if recon and expected_txn.id not in counted_txns:
                    true_positives += 1
                    counted_txns.add(expected_txn.id)
                elif expected_txn.id not in counted_txns:
                    # Matched but wrong invoice
                    wrong_recon = db_session.query(models.ReconciliationTable).filter(
                        models.ReconciliationTable.bank_transaction_id == expected_txn.id
                    ).first()
                    if wrong_recon:
                        false_positives += 1
                        counted_txns.add(expected_txn.id)
        
        # Count unmatched transactions that should have matched
        unmatched_count = sum(1 for _, txn in true_matches if txn.is_reconciled == 0)
        
        # Also check for false positives: transactions matched but not in our true matches
        all_reconciled = db_session.query(models.BankTransaction).filter(
            models.BankTransaction.is_reconciled == 1,
            models.BankTransaction.bank_account_id == sample_bank_account.id
        ).all()
        
        for txn in all_reconciled:
            if txn.id not in counted_txns:
                # This transaction was reconciled but not in our true matches
                # Check if it's actually a false positive (matched to wrong invoice)
                is_true_match = any(t[1].id == txn.id for t in true_matches)
                if not is_true_match:
                    false_positives += 1
                    counted_txns.add(txn.id)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        
        # Deterministic matching should have very high precision
        assert precision >= 0.95, \
            f"Deterministic match precision {precision:.2%} is too low. " \
            f"TP: {true_positives}, FP: {false_positives}, unmatched: {unmatched_count}. Should be ≈ 100%"
    
    def test_rules_match_precision(self, db_session, sample_entity, sample_bank_account):
        """
        Rules-based match precision (should still be very high)
        """
        # Create snapshot for these invoices
        snapshot = models.Snapshot(
            name="Rules Test Snapshot",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow()
        )
        snapshot.is_locked = 0
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)
        
        # Create invoices
        invoices = []
        for i in range(15):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"rules-inv-{i}",
                document_number=f"INV-RULES-{i:03d}",
                customer="Rules Customer",
                amount=2000.0 + (i * 50),
                currency="EUR",
                expected_due_date=datetime.utcnow() + timedelta(days=30)
            )
            invoices.append(inv)
        
        db_session.add_all(invoices)
        db_session.commit()
        
        # Refresh invoices to get their IDs
        for inv in invoices:
            db_session.refresh(inv)
        
        # Create transactions with matching amounts (but no invoice number in reference)
        # These should match via rules-based matching (amount + date window)
        true_matches = []
        for i, inv in enumerate(invoices[:10]):  # Match first 10
            txn = models.BankTransaction(
                bank_account_id=sample_bank_account.id,
                transaction_date=datetime.utcnow(),
                amount=inv.amount,  # Exact amount match
                reference="Payment reference",  # No invoice number
                counterparty="Rules Customer",
                currency="EUR",
                is_reconciled=0
            )
            db_session.add(txn)
            true_matches.append((inv, txn))
        
        db_session.commit()
        
        # Run reconciliation
        generate_match_ladder(db_session, sample_entity.id)
        
        # Calculate precision
        true_positives = 0
        false_positives = 0
        
        for inv, expected_txn in true_matches:
            db_session.refresh(expected_txn)
            if expected_txn.is_reconciled == 1:
                recon = db_session.query(models.ReconciliationTable).filter(
                    models.ReconciliationTable.bank_transaction_id == expected_txn.id,
                    models.ReconciliationTable.invoice_id == inv.id
                ).first()
                
                if recon:
                    true_positives += 1
                else:
                    false_positives += 1
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        
        # Rules-based matching should have high precision (but might be lower than deterministic)
        assert precision >= 0.80, \
            f"Rules match precision {precision:.2%} is too low. TP: {true_positives}, FP: {false_positives}"
    
    def test_suggested_match_acceptance_rate(self, db_session, sample_entity, sample_bank_account):
        """
        Suggested match acceptance rate + false positives
        Suggested matches should be flagged but not auto-reconciled
        """
        # Create snapshot for these invoices
        snapshot = models.Snapshot(
            name="Suggested Test Snapshot",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow()
        )
        snapshot.is_locked = 0
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)
        
        # Create invoices
        invoices = []
        for i in range(10):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"suggest-inv-{i}",
                document_number=f"INV-SUGGEST-{i:03d}",
                customer=f"Customer{i}",
                amount=3000.0,
                currency="EUR",
                expected_due_date=datetime.utcnow() + timedelta(days=30)
            )
            invoices.append(inv)
        
        db_session.add_all(invoices)
        db_session.commit()
        
        # Refresh invoices to get their IDs
        for inv in invoices:
            db_session.refresh(inv)
        
        # Create transactions with fuzzy matches (same customer, similar amount)
        # Make sure amounts are different enough to avoid Tier 2 (rules-based) matching
        # Rules-based matching requires exact amount match (within 0.01) AND date window
        # So we'll use amounts that are significantly different AND outside date window
        transactions = []
        for i in range(10):
            txn = models.BankTransaction(
                bank_account_id=sample_bank_account.id,
                transaction_date=datetime.utcnow() + timedelta(days=60),  # Outside 30-day window to avoid Tier 2
                amount=3000.0 + (i * 500) + 50,  # Different amounts (add 50 to avoid any exact match with 3000.0)
                reference="Fuzzy payment",  # No invoice number (avoids Tier 1)
                counterparty=f"Customer{i}",  # Same customer (for Tier 3)
                currency="EUR",
                is_reconciled=0
            )
            transactions.append(txn)
            db_session.add(txn)
        
        db_session.commit()
        
        # Run reconciliation
        results = generate_match_ladder(db_session, sample_entity.id)
        
        # Check suggested matches (should not be auto-reconciled)
        suggested_count = 0
        auto_reconciled_count = 0
        
        for txn in transactions:
            db_session.refresh(txn)
            if txn.reconciliation_type == "Suggested":
                suggested_count += 1
            elif txn.is_reconciled == 1:
                auto_reconciled_count += 1
        
        # Suggested matches should be flagged but not auto-reconciled
        assert suggested_count > 0, "Should have some suggested matches for fuzzy cases"
        assert auto_reconciled_count == 0, \
            f"Suggested matches should not be auto-reconciled. Found {auto_reconciled_count} auto-reconciled"
        
        # Acceptance rate would be measured in production by tracking user approvals
        # For this test, we verify the system flags them correctly

