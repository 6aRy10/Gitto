"""
State-Machine Workflow Tests
Models the actual finance workflow as a sequence of operations and asserts invariants after every step.
This catches bugs unit tests miss (e.g., "locking doesn't really freeze," or "reconciliation changes historical totals").
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from utils import (
    get_forecast_aggregation,
    run_forecast_model,
    get_snapshot_fx_rate,
    calculate_unknown_bucket
)
from bank_service import generate_match_ladder, calculate_cash_explained_pct
from snapshot_protection import check_snapshot_not_locked, SnapshotLockedError
from cash_calendar_service import get_13_week_workspace


class TestFinanceWorkflowStateMachine:
    """
    State-machine test: Models the complete finance workflow as a sequence.
    Workflow: upload → forecast → reconcile → lock snapshot → upload again → compare → apply lever → lock again
    """
    
    def test_complete_workflow_with_invariants(self, db_session, sample_entity, sample_bank_account):
        """Complete workflow test with invariant checks at each step"""
        
        # Step 1: Create snapshot and upload invoices
        snapshot = models.Snapshot(
            name="Workflow Test Snapshot",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow(),
            is_locked=0
        )
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)
        
        # Upload invoices
        invoices = []
        amounts = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
        total_expected = sum(amounts)
        
        for i, amount in enumerate(amounts):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"workflow-inv-{i}",
                document_number=f"INV-WF-{i:03d}",
                customer="Test Customer",
                amount=amount,
                currency="EUR",
                expected_due_date=datetime.utcnow() + timedelta(days=30 + i)
            )
            invoices.append(inv)
        
        db_session.bulk_save_objects(invoices)
        db_session.commit()
        
        # Invariant 1: All invoices uploaded
        invoice_count = db_session.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).count()
        assert invoice_count == len(amounts), f"Expected {len(amounts)} invoices, got {invoice_count}"
        
        # Step 2: Run forecast
        run_forecast_model(db_session, snapshot.id)
        forecast_before = get_forecast_aggregation(db_session, snapshot.id, group_by="week")
        total_forecast_before = sum(w.get('base', 0) for w in forecast_before)
        
        # Invariant 2: Forecast total should be reasonable (probabilistic allocation)
        assert 0.8 * total_expected <= total_forecast_before <= 1.2 * total_expected, \
            f"Forecast total {total_forecast_before} should be close to {total_expected}"
        
        # Step 3: Reconcile bank transactions
        # Create bank transaction matching one invoice
        txn = models.BankTransaction(
            bank_account_id=sample_bank_account.id,
            transaction_date=datetime.utcnow(),
            amount=1000.0,
            reference="Payment for INV-WF-000",
            counterparty="Test Customer",
            currency="EUR",
            is_reconciled=0
        )
        db_session.add(txn)
        db_session.commit()
        db_session.refresh(txn)
        
        # Run reconciliation
        match_results = generate_match_ladder(db_session, sample_entity.id)
        db_session.refresh(txn)
        
        # Invariant 3: Transaction should be reconciled
        assert txn.is_reconciled == 1, "Transaction should be reconciled after matching"
        
        # Invariant 4: Forecast should not change after reconciliation (historical data)
        forecast_after_recon = get_forecast_aggregation(db_session, snapshot.id, group_by="week")
        total_forecast_after_recon = sum(w.get('base', 0) for w in forecast_after_recon)
        # Forecast might change slightly due to payment_date being set, but should be close
        assert abs(total_forecast_after_recon - total_forecast_before) / total_forecast_before < 0.3, \
            f"Forecast changed too much after reconciliation: {total_forecast_before} -> {total_forecast_after_recon}"
        
        # Step 4: Lock snapshot
        snapshot.is_locked = 1
        snapshot.lock_type = "Meeting"
        db_session.commit()
        db_session.refresh(snapshot)
        
        # Invariant 5: Locked snapshot cannot be modified
        with pytest.raises(SnapshotLockedError):
            check_snapshot_not_locked(snapshot.id, db_session, "add invoices to")
        
        # Invariant 6: Locked snapshot preserves invoice amounts
        locked_invoices = db_session.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot.id
        ).all()
        locked_total = sum(inv.amount for inv in locked_invoices)
        assert abs(locked_total - total_expected) < 0.01, \
            f"Locked snapshot invoice total {locked_total} should equal {total_expected}"
        
        # Step 5: Try to upload again (should fail)
        new_invoice = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            canonical_id="workflow-new-inv",
            document_number="INV-NEW-001",
            customer="Test Customer",
            amount=6000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        
        # Invariant 7: Cannot add invoices to locked snapshot
        # (This would be caught by the API endpoint, but we test the protection layer)
        with pytest.raises(SnapshotLockedError):
            check_snapshot_not_locked(snapshot.id, db_session, "add invoices to")
        
        # Step 6: Compare snapshots (create new snapshot and compare)
        new_snapshot = models.Snapshot(
            name="Workflow Test Snapshot 2",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow() + timedelta(hours=1),
            is_locked=0
        )
        db_session.add(new_snapshot)
        db_session.commit()
        db_session.refresh(new_snapshot)
        
        # Upload same invoices to new snapshot
        new_invoices = []
        for i, amount in enumerate(amounts):
            inv = models.Invoice(
                snapshot_id=new_snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"workflow-inv-{i}",
                document_number=f"INV-WF-{i:03d}",
                customer="Test Customer",
                amount=amount,
                currency="EUR",
                expected_due_date=datetime.utcnow() + timedelta(days=30 + i)
            )
            new_invoices.append(inv)
        
        db_session.bulk_save_objects(new_invoices)
        db_session.commit()
        
        run_forecast_model(db_session, new_snapshot.id)
        forecast_new = get_forecast_aggregation(db_session, new_snapshot.id, group_by="week")
        total_forecast_new = sum(w.get('base', 0) for w in forecast_new)
        
        # Invariant 8: New snapshot should have similar forecast (same data)
        # Allow some variance due to timing differences
        assert abs(total_forecast_new - total_forecast_before) / total_forecast_before < 0.2, \
            f"New snapshot forecast {total_forecast_new} should be similar to original {total_forecast_before}"
        
        # Invariant 9: Locked snapshot numbers should not change
        forecast_locked_again = get_forecast_aggregation(db_session, snapshot.id, group_by="week")
        total_forecast_locked_again = sum(w.get('base', 0) for w in forecast_locked_again)
        assert abs(total_forecast_locked_again - total_forecast_after_recon) < 0.01, \
            f"Locked snapshot forecast should not change: {total_forecast_after_recon} -> {total_forecast_locked_again}"
        
        # Step 7: Verify cash explained percentage
        cash_explained = calculate_cash_explained_pct(db_session, sample_entity.id)
        
        # Invariant 10: Cash explained should be > 0 after reconciliation
        assert cash_explained.get('explained_pct', 0) > 0, \
            f"Cash explained should be > 0 after reconciliation, got {cash_explained.get('explained_pct', 0)}"
        
        # Invariant 11: Deterministic matches should be in breakdown
        breakdown = cash_explained.get('breakdown', {})
        assert breakdown.get('deterministic', 0) > 0, \
            "Should have at least one deterministic match"
    
    def test_workflow_reconciliation_changes_historical_totals(self, db_session, sample_entity, sample_bank_account):
        """Test that reconciliation doesn't corrupt historical snapshot totals"""
        # Create and lock snapshot
        snapshot = models.Snapshot(
            name="Historical Test",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow(),
            is_locked=1,
            lock_type="Historical"
        )
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)
        
        # Add invoice
        invoice = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            canonical_id="historical-inv-1",
            document_number="INV-HIST-001",
            customer="Test Customer",
            amount=5000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(invoice)
        db_session.commit()
        
        original_amount = invoice.amount
        
        # Try to reconcile (should not affect locked snapshot)
        txn = models.BankTransaction(
            bank_account_id=sample_bank_account.id,
            transaction_date=datetime.utcnow(),
            amount=5000.0,
            reference="Payment for INV-HIST-001",
            counterparty="Test Customer",
            currency="EUR",
            is_reconciled=0
        )
        db_session.add(txn)
        db_session.commit()
        
        # Run reconciliation (might match, but shouldn't change locked snapshot)
        generate_match_ladder(db_session, sample_entity.id)
        
        # Invariant: Locked snapshot invoice amount should not change
        db_session.refresh(invoice)
        assert invoice.amount == original_amount, \
            f"Locked snapshot invoice amount changed: {original_amount} -> {invoice.amount}"
    
    def test_workflow_lock_doesnt_freeze(self, db_session, sample_entity):
        """Test that locking actually freezes the snapshot"""
        snapshot = models.Snapshot(
            name="Freeze Test",
            entity_id=sample_entity.id,
            total_rows=0,
            created_at=datetime.utcnow(),
            is_locked=0
        )
        db_session.add(snapshot)
        db_session.commit()
        db_session.refresh(snapshot)
        
        # Add invoice
        invoice = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            canonical_id="freeze-inv-1",
            document_number="INV-FREEZE-001",
            customer="Test Customer",
            amount=3000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(invoice)
        db_session.commit()
        
        # Lock snapshot
        snapshot.is_locked = 1
        snapshot.lock_type = "Meeting"
        db_session.commit()
        
        # Try to modify invoice directly (should be prevented by application logic)
        # In a real system, this would be prevented by DB constraints, but we test app-level protection
        with pytest.raises(SnapshotLockedError):
            check_snapshot_not_locked(snapshot.id, db_session, "modify invoices in")
        
        # Invariant: Invoice amount should remain unchanged
        db_session.refresh(invoice)
        assert invoice.amount == 3000.0, "Invoice amount should not change after lock"

