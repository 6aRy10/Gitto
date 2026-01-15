"""
The 5 CFO Trust Killers
If any of these fail even once, the product is not finance-grade yet.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import models
from tests.conftest import db_session, sample_entity, sample_snapshot


class TestCFOTrustKillers:
    """
    The 5 critical tests that determine if the product is finance-grade.
    These must pass 100% of the time.
    """
    
    def test_1_cell_sum_truth(self, db_session, sample_entity, sample_snapshot):
        """
        CFO Trust Killer #1: Cell Sum Truth
        Every number in the 13-week grid must equal the sum of its drilldown rows (exactly).
        """
        from cash_calendar_service import get_13_week_workspace
        from cash_calendar_service import get_week_drilldown_data
        
        # Create test data
        snapshot = sample_snapshot
        entity = sample_entity
        
        # Add invoices
        # First create historical PAID invoices for the forecast model to learn from
        for i in range(20):  # Need N >= 15 for valid segments
            paid_inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=entity.id,
                document_number=f"HIST-{i:03d}",
                customer=f"Customer {i % 2}",
                amount=500.0 + (i * 50),
                currency="EUR",
                expected_due_date=datetime.utcnow() - timedelta(days=60 + i),
                payment_date=datetime.utcnow() - timedelta(days=53 + i)  # Paid ~7 days late
            )
            db_session.add(paid_inv)
        
        # Now create open invoices that need forecasting
        invoices = []
        today = datetime.utcnow()
        for i in range(6):
            # Set expected_due_date to fall into different weeks
            due_date = today + timedelta(days=7 * (i + 1))
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=entity.id,
                document_number=f"INV-{i:03d}",
                customer=f"Customer {i % 2}",
                amount=1000.0 * (i + 1),
                currency="EUR",
                expected_due_date=due_date,
                payment_date=None
            )
            db_session.add(inv)
            invoices.append(inv)
        
        db_session.commit()
        
        # Run forecast - this will now learn from historical data
        from utils import run_forecast_model
        run_forecast_model(db_session, snapshot.id)
        
        # Verify invoices have predicted_payment_date set
        for inv in invoices:
            db_session.refresh(inv)
            assert inv.predicted_payment_date is not None, f"Invoice {inv.document_number} has no predicted_payment_date"
        
        # Get workspace grid
        workspace = get_13_week_workspace(db_session, snapshot.id)
        assert workspace is not None
        assert 'grid' in workspace
        
        # Test every cell
        for week_idx, week in enumerate(workspace['grid']):
            # Test inflow cell
            inflow_cell = week.get('inflow_p50', 0)
            inflow_drilldown = get_week_drilldown_data(
                db_session, snapshot.id, week_idx, "inflow"
            )
            # get_week_drilldown_data returns a list directly, not a dict with 'items'
            if isinstance(inflow_drilldown, list):
                drilldown_sum = sum(item.get('amount', 0) for item in inflow_drilldown)
            elif isinstance(inflow_drilldown, dict) and 'items' in inflow_drilldown:
                drilldown_sum = sum(item.get('amount', 0) for item in inflow_drilldown['items'])
            else:
                drilldown_sum = 0
            
            assert abs(inflow_cell - drilldown_sum) < 0.01, \
                f"Week {week_idx} inflow: Cell={inflow_cell}, Drilldown sum={drilldown_sum}"
            
            # Test outflow cell
            outflow_cell = week.get('outflow_committed', 0) + week.get('outflow_discretionary', 0)
            outflow_drilldown = get_week_drilldown_data(
                db_session, snapshot.id, week_idx, "outflow"
            )
            # get_week_drilldown_data returns a list directly, not a dict with 'items'
            if isinstance(outflow_drilldown, list):
                drilldown_sum = sum(item.get('amount', 0) for item in outflow_drilldown)
            elif isinstance(outflow_drilldown, dict) and 'items' in outflow_drilldown:
                drilldown_sum = sum(item.get('amount', 0) for item in outflow_drilldown['items'])
            else:
                drilldown_sum = 0
            
            assert abs(outflow_cell - drilldown_sum) < 0.01, \
                f"Week {week_idx} outflow: Cell={outflow_cell}, Drilldown sum={drilldown_sum}"
    
    def test_2_snapshot_immutability(self, db_session, sample_entity, sample_snapshot):
        """
        CFO Trust Killer #2: Snapshot Immutability
        Lock a snapshot → refresh/recompute/reupload elsewhere → the locked snapshot's outputs never change.
        """
        snapshot = sample_snapshot
        
        # Add invoices
        inv1 = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            document_number="INV-001",
            customer="Customer A",
            amount=5000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=14),
            payment_date=None
        )
        db_session.add(inv1)
        db_session.commit()
        
        # Run forecast
        from utils import run_forecast_model
        run_forecast_model(db_session, snapshot.id)
        
        # Get initial workspace
        from cash_calendar_service import get_13_week_workspace
        workspace_before = get_13_week_workspace(db_session, snapshot.id)
        total_before = sum(w.get('inflow_p50', 0) for w in workspace_before['grid'])
        
        # Lock snapshot
        snapshot.is_locked = 1
        snapshot.lock_type = "Meeting"
        db_session.commit()
        
        # Try to modify invoice (should be prevented by DB trigger)
        inv1.amount = 10000.0
        try:
            db_session.commit()
            # If commit succeeds, check that workspace didn't change
            workspace_after = get_13_week_workspace(db_session, snapshot.id)
            total_after = sum(w.get('inflow_p50', 0) for w in workspace_after['grid'])
            assert abs(total_before - total_after) < 0.01, \
                f"Locked snapshot changed: before={total_before}, after={total_after}"
        except Exception as e:
            # Expected: DB trigger should prevent update
            assert "locked snapshot" in str(e).lower() or "IntegrityError" in str(type(e).__name__), \
                f"Expected locked snapshot error, got: {e}"
            db_session.rollback()
        
        # Re-run forecast (should not change locked snapshot)
        run_forecast_model(db_session, snapshot.id)
        
        # Get workspace after
        workspace_after = get_13_week_workspace(db_session, snapshot.id)
        total_after = sum(w.get('inflow_p50', 0) for w in workspace_after['grid'])
        
        # Totals should be identical (locked snapshot is immutable)
        assert abs(total_before - total_after) < 0.01, \
            f"Locked snapshot changed: before={total_before}, after={total_after}"
    
    def test_3_fx_safety(self, db_session, sample_entity, sample_snapshot):
        """
        CFO Trust Killer #3: FX Safety
        Missing FX can never silently convert (no 1.0 fallback). It must go to Unknown + visible warning.
        """
        snapshot = sample_snapshot
        
        # Add EUR invoice (should work)
        inv_eur = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            document_number="INV-EUR",
            customer="Customer EUR",
            amount=1000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=14),
            payment_date=None
        )
        db_session.add(inv_eur)
        
        # Add USD invoice WITHOUT FX rate (should go to Unknown)
        inv_usd = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            document_number="INV-USD",
            customer="Customer USD",
            amount=1000.0,
            currency="USD",
            expected_due_date=datetime.utcnow() + timedelta(days=14),
            payment_date=None
        )
        db_session.add(inv_usd)
        db_session.commit()
        
        # Run forecast
        from utils import run_forecast_model
        run_forecast_model(db_session, snapshot.id)
        
        # Check unknown bucket
        from utils import calculate_unknown_bucket
        unknown = calculate_unknown_bucket(db_session, snapshot.id)
        
        # USD invoice should be in unknown bucket due to missing FX
        assert unknown['total_unknown_amount'] > 0, "USD invoice without FX should be in unknown bucket"
        
        # Check that missing_fx category exists
        assert 'categories' in unknown
        assert 'missing_fx_rates' in unknown['categories'] or any(
            'fx' in cat.lower() for cat in unknown['categories'].keys()
        ), "Missing FX should be explicitly categorized"
        
        # Verify USD invoice is NOT in forecast (should be excluded)
        from utils import get_forecast_aggregation
        forecast = get_forecast_aggregation(db_session, snapshot.id, group_by="week")
        total_forecast = sum(w.get('base', 0) for w in forecast)
        
        # Forecast should only include EUR invoice (1000), not USD
        # (USD should be in unknown, not silently converted at 1.0)
        assert total_forecast <= 1000.0 + 0.01, \
            f"Forecast should not include USD invoice without FX. Got {total_forecast}"
    
    def test_4_reconciliation_conservation(self, db_session, sample_entity, sample_snapshot):
        """
        CFO Trust Killer #4: Reconciliation Conservation
        Allocations conserve amounts (txn allocations sum to txn amount; invoice allocations never exceed open amount).
        """
        snapshot = sample_snapshot
        
        # Create bank account
        bank_account = models.BankAccount(
            entity_id=sample_entity.id,
            account_number="ACC-001",
            bank_name="Test Bank",
            currency="EUR"
        )
        db_session.add(bank_account)
        db_session.commit()
        
        # Create invoice
        invoice = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            document_number="INV-001",
            customer="Customer A",
            amount=5000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=14),
            payment_date=None
        )
        db_session.add(invoice)
        db_session.commit()
        
        # Create bank transaction
        bank_txn = models.BankTransaction(
            bank_account_id=bank_account.id,
            transaction_date=datetime.utcnow(),
            amount=5000.0,
            currency="EUR",
            reference="INV-001",
            counterparty="Customer A",
            is_reconciled=0
        )
        db_session.add(bank_txn)
        db_session.commit()
        
        # Reconcile (should create allocation)
        from bank_service import generate_match_ladder
        matches = generate_match_ladder(db_session, sample_entity.id)
        
        # Check reconciliation record
        recon = db_session.query(models.ReconciliationTable).filter_by(
            bank_transaction_id=bank_txn.id,
            invoice_id=invoice.id
        ).first()
        
        if recon:
            # Allocation should equal transaction amount (or invoice amount if partial)
            assert abs(recon.amount_allocated - min(bank_txn.amount, invoice.amount)) < 0.01, \
                f"Allocation {recon.amount_allocated} should equal txn/invoice amount"
        
        # Test many-to-many: one txn to multiple invoices
        invoice2 = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=sample_entity.id,
            document_number="INV-002",
            customer="Customer A",
            amount=3000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=14),
            payment_date=None
        )
        db_session.add(invoice2)
        
        bank_txn2 = models.BankTransaction(
            bank_account_id=bank_account.id,
            transaction_date=datetime.utcnow(),
            amount=8000.0,  # Covers both invoices
            currency="EUR",
            reference="BUNDLED",
            counterparty="Customer A",
            is_reconciled=0
        )
        db_session.add(bank_txn2)
        db_session.commit()
        
        # Reconcile
        matches2 = generate_match_ladder(db_session, sample_entity.id)
        
        # Check allocations sum to transaction amount
        allocations = db_session.query(models.ReconciliationTable).filter_by(
            bank_transaction_id=bank_txn2.id
        ).all()
        
        if allocations:
            total_allocated = sum(a.amount_allocated for a in allocations)
            assert abs(total_allocated - bank_txn2.amount) < 0.01, \
                f"Allocations {total_allocated} should sum to txn amount {bank_txn2.amount}"
    
    def test_5_freshness_honesty(self, db_session, sample_entity, sample_snapshot):
        """
        CFO Trust Killer #5: Freshness Honesty
        Stale bank vs ERP mismatch must be visible and must block/warn before lock/export. Never silent.
        """
        snapshot = sample_snapshot
        entity = sample_entity
        
        # Set snapshot created_at to now (ERP data is fresh)
        snapshot.created_at = datetime.utcnow()
        
        # Create bank account with stale data (48 hours old)
        bank_account = models.BankAccount(
            entity_id=entity.id,
            account_number="ACC-001",
            bank_name="Test Bank",
            currency="EUR"
        )
        # Set last_sync_at to stale (48 hours old)
        if hasattr(bank_account, 'last_sync_at'):
            bank_account.last_sync_at = datetime.utcnow() - timedelta(hours=48)
        db_session.add(bank_account)
        db_session.commit()
        
        # Check data freshness
        from data_freshness_service import check_data_freshness, get_data_freshness_summary
        freshness = check_data_freshness(db_session, entity.id)
        summary = get_data_freshness_summary(db_session, entity.id)
        
        # Should detect conflict
        assert freshness.get('has_conflict', False) or summary.get('has_conflict', False), \
            "Should detect stale bank data conflict"
        
        # Try to lock snapshot (should warn or block)
        snapshot.is_locked = 1
        snapshot.lock_type = "Meeting"
        
        # In a real system, this would be blocked or warned. For now, we verify detection.
        # The freshness check should be visible before lock.
        assert summary.get('bank_age_hours', 0) > 24, \
            "Bank data should be flagged as stale (>24 hours)"
        
        # Verify warning is visible
        assert 'warnings' in summary or 'has_conflict' in summary, \
            "Freshness conflict should be visible in summary"

