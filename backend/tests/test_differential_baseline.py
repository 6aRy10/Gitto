"""
Differential Baseline Tests
Compare Gitto output against a simple baseline model.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from utils import get_forecast_aggregation, run_forecast_model


def baseline_due_date_model(invoices, target_date):
    """
    Simple baseline model: All invoices pay exactly on their due date.
    Returns total amount due on target_date.
    """
    total = 0.0
    for inv in invoices:
        if inv.expected_due_date:
            # Check if due date falls in the week containing target_date
            week_start = target_date - timedelta(days=target_date.weekday())
            week_end = week_start + timedelta(days=7)
            
            if week_start <= inv.expected_due_date < week_end:
                total += inv.amount
    
    return total


class TestDifferentialBaseline:
    """Compare Gitto forecasts against baseline due-date model"""
    
    def test_gitto_matches_or_improves_baseline(self, db_session, sample_snapshot):
        """Gitto should match or improve upon simple due-date baseline"""
        # Create historical invoices (with payment_date) to train the model
        # These show that customers pay exactly on due date
        historical_invoices = []
        for i in range(10):
            past_due_date = datetime.utcnow() - timedelta(days=30 - i)
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=1,
                canonical_id=f"baseline-hist-{i}",
                document_number=f"INV-HIST-{i:03d}",
                customer="Test Customer",
                amount=1000.0 + (i * 100),
                currency="EUR",
                expected_due_date=past_due_date,
                payment_date=past_due_date  # Historical: they paid on due date
            )
            historical_invoices.append(inv)
        
        # Create future invoices (without payment_date) to forecast
        target_week = datetime.utcnow() + timedelta(weeks=4)
        future_invoices = []
        amounts = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
        total_expected = sum(amounts)
        
        for i, amount in enumerate(amounts):
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=1,
                canonical_id=f"baseline-test-{i}",
                document_number=f"INV-BASE-{i:03d}",
                customer="Test Customer",
                amount=amount,
                currency="EUR",
                expected_due_date=target_week
                # No payment_date - these are future invoices to forecast
            )
            future_invoices.append(inv)
        
        all_invoices = historical_invoices + future_invoices
        db_session.bulk_save_objects(all_invoices)
        db_session.commit()
        
        # Run Gitto forecast model (uses historical data to learn, forecasts future)
        run_forecast_model(db_session, sample_snapshot.id)
        gitto_forecast = get_forecast_aggregation(db_session, sample_snapshot.id, group_by="week")
        
        # Find target week in Gitto forecast
        gitto_week_total = 0
        for week in gitto_forecast:
            week_start_str = week.get('start_date')
            if week_start_str:
                week_start = datetime.fromisoformat(week_start_str.replace('Z', '+00:00').replace('+00:00', ''))
                if abs((week_start - target_week).days) < 7:
                    gitto_week_total = week.get('base', 0)
                    break
        
        # Calculate baseline model (using future invoices)
        baseline_total = baseline_due_date_model(future_invoices, target_week)
        
        # Differential test: Gitto should match or improve (be closer to actual)
        # Since all invoices paid on due date, Gitto should predict close to baseline
        # But Gitto uses probabilistic allocation, so allow some variance
        
        ratio = gitto_week_total / baseline_total if baseline_total > 0 else 0
        
        # Gitto should be within 30% of baseline (probabilistic allocation spreads amounts)
        assert 0.7 <= ratio <= 1.3, \
            f"Gitto forecast {gitto_week_total} differs significantly from baseline {baseline_total} (ratio: {ratio:.2f})"
    
    def test_gitto_never_produces_impossible_timing(self, db_session, sample_snapshot):
        """Gitto should never predict payment before invoice date"""
        # Create invoice with future due date
        invoice_date = datetime.utcnow() + timedelta(days=10)
        due_date = datetime.utcnow() + timedelta(days=40)
        
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            entity_id=1,
            canonical_id="timing-test-1",
            document_number="INV-TIME-001",
            customer="Test Customer",
            amount=5000.0,
            currency="EUR",
            document_date=invoice_date,
            expected_due_date=due_date
        )
        db_session.add(invoice)
        db_session.commit()
        
        # Run forecast
        run_forecast_model(db_session, sample_snapshot.id)
        
        # Get forecast
        forecast = get_forecast_aggregation(db_session, sample_snapshot.id, group_by="week")
        
        # Check all weeks before invoice date have zero forecast
        for week in forecast:
            week_start_str = week.get('start_date')
            if week_start_str:
                week_start = datetime.fromisoformat(week_start_str.replace('Z', '+00:00').replace('+00:00', ''))
                if week_start < invoice_date:
                    week_amount = week.get('base', 0)
                    # Should be zero (can't pay before invoice exists)
                    assert week_amount == 0, \
                        f"Week {week.get('label')} (before invoice date) has non-zero forecast: {week_amount}"
        
        # Check weeks before due date (should be low probability, but not impossible)
        # This is more lenient - Gitto might predict early payment, but not before invoice date
    
    def test_gitto_handles_constant_behavior_correctly(self, db_session, sample_snapshot):
        """Gitto should handle constant payment behavior correctly"""
        # Create historical invoices showing constant behavior (always pay on due date)
        historical_invoices = []
        for i in range(10):
            past_due_date = datetime.utcnow() - timedelta(days=30 - i)
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=1,
                canonical_id=f"constant-hist-{i}",
                document_number=f"INV-CONST-HIST-{i:03d}",
                customer="Constant Customer",
                amount=1000.0,
                currency="EUR",
                expected_due_date=past_due_date,
                payment_date=past_due_date  # Always pays on due date
            )
            historical_invoices.append(inv)
        
        # Create future invoices to forecast
        target_week = datetime.utcnow() + timedelta(weeks=4)
        future_invoices = []
        for i in range(5):
            due_date = target_week + timedelta(days=i)
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=1,
                canonical_id=f"constant-test-{i}",
                document_number=f"INV-CONST-{i:03d}",
                customer="Constant Customer",
                amount=1000.0,
                currency="EUR",
                expected_due_date=due_date
                # No payment_date - these are future invoices
            )
            future_invoices.append(inv)
        
        all_invoices = historical_invoices + future_invoices
        db_session.bulk_save_objects(all_invoices)
        db_session.commit()
        
        # Run Gitto forecast
        run_forecast_model(db_session, sample_snapshot.id)
        gitto_forecast = get_forecast_aggregation(db_session, sample_snapshot.id, group_by="week")
        
        # Calculate baseline (using future invoices)
        baseline_total = baseline_due_date_model(future_invoices, target_week)
        
        # Find Gitto forecast for target week
        gitto_total = 0
        for week in gitto_forecast:
            week_start_str = week.get('start_date')
            if week_start_str:
                week_start = datetime.fromisoformat(week_start_str.replace('Z', '+00:00').replace('+00:00', ''))
                if abs((week_start - target_week).days) < 7:
                    gitto_total = week.get('base', 0)
                    break
        
        # With constant behavior, Gitto should predict close to baseline
        # But since Gitto uses probabilistic allocation, it may spread amounts
        # The key is that it should never be wildly different
        
        if baseline_total > 0:
            ratio = gitto_total / baseline_total
            # Should be within 50% (probabilistic allocation spreads)
            assert 0.5 <= ratio <= 1.5, \
                f"Gitto {gitto_total} differs too much from baseline {baseline_total} for constant behavior (ratio: {ratio:.2f})"


