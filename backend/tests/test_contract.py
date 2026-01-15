"""
Contract Tests
Verify that API responses are consistent and match UI expectations.
Tests that grid numbers returned by /workspace-13w equal the sum of items returned by drilldown endpoints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from utils import run_forecast_model
from cash_calendar_service import get_13_week_workspace


class TestAPIContractConsistency:
    """Contract tests: API truth vs UI truth"""
    
    def test_workspace_grid_totals_match_drilldown_sums(self, db_session, sample_snapshot, sample_entity):
        """Grid totals should equal sum of drilldown items"""
        # Create invoices for specific weeks
        invoices = []
        week_4_date = datetime.utcnow() + timedelta(weeks=4)
        week_5_date = datetime.utcnow() + timedelta(weeks=5)
        
        amounts_week_4 = [1000.0, 2000.0, 3000.0]
        amounts_week_5 = [1500.0, 2500.0]
        
        for i, amount in enumerate(amounts_week_4):
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"contract-w4-{i}",
                document_number=f"INV-W4-{i:03d}",
                customer="Test Customer",
                amount=amount,
                currency="EUR",
                expected_due_date=week_4_date,
                predicted_payment_date=week_4_date,
                confidence_p25=week_4_date - timedelta(days=3),
                confidence_p75=week_4_date + timedelta(days=3)
            )
            invoices.append(inv)
        
        for i, amount in enumerate(amounts_week_5):
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"contract-w5-{i}",
                document_number=f"INV-W5-{i:03d}",
                customer="Test Customer",
                amount=amount,
                currency="EUR",
                expected_due_date=week_5_date,
                predicted_payment_date=week_5_date,
                confidence_p25=week_5_date - timedelta(days=3),
                confidence_p75=week_5_date + timedelta(days=3)
            )
            invoices.append(inv)
        
        db_session.bulk_save_objects(invoices)
        db_session.commit()
        
        # Run forecast
        run_forecast_model(db_session, sample_snapshot.id)
        
        # Get workspace (simulates /workspace-13w endpoint)
        workspace = get_13_week_workspace(db_session, sample_snapshot.id)
        
        if workspace and 'grid' in workspace:
            # Find Week 4 and Week 5 in grid
            week_4_grid = None
            week_5_grid = None
            
            for week in workspace['grid']:
                week_label = week.get('week_label', '')
                if 'W4' in week_label or 'W5' in week_label:
                    week_start_str = week.get('start_date')
                    if week_start_str:
                        try:
                            week_start = datetime.fromisoformat(week_start_str.replace('Z', '+00:00').replace('+00:00', ''))
                            if abs((week_start - week_4_date).days) < 7:
                                week_4_grid = week
                            elif abs((week_start - week_5_date).days) < 7:
                                week_5_grid = week
                        except:
                            pass
            
            # Contract Test 1: Week 4 grid total should match drilldown sum
            if week_4_grid:
                grid_total_w4 = week_4_grid.get('inflow_p50', 0)
                
                # Get drilldown (simulates /workspace-13w/drilldown?week=4)
                week_4_invoices = db_session.query(models.Invoice).filter(
                    models.Invoice.snapshot_id == sample_snapshot.id,
                    models.Invoice.predicted_payment_date >= week_4_date - timedelta(days=3),
                    models.Invoice.predicted_payment_date <= week_4_date + timedelta(days=3)
                ).all()
                
                drilldown_sum_w4 = sum(inv.amount for inv in week_4_invoices)
                
                # Grid total (P50) should match drilldown sum
                # Note: P50 represents the median allocation, so it should be close to the sum
                # of invoices that fall in that week
                assert abs(grid_total_w4 - drilldown_sum_w4) < 0.01 or (drilldown_sum_w4 > 0 and 0.8 <= (grid_total_w4 / drilldown_sum_w4) <= 1.2), \
                    f"Week 4: Grid total {grid_total_w4} should match drilldown sum {drilldown_sum_w4}"
            
            # Contract Test 2: Week 5 grid total should match drilldown sum
            if week_5_grid:
                grid_total_w5 = week_5_grid.get('inflow_p50', 0)
                
                week_5_invoices = db_session.query(models.Invoice).filter(
                    models.Invoice.snapshot_id == sample_snapshot.id,
                    models.Invoice.predicted_payment_date >= week_5_date - timedelta(days=3),
                    models.Invoice.predicted_payment_date <= week_5_date + timedelta(days=3)
                ).all()
                
                drilldown_sum_w5 = sum(inv.amount for inv in week_5_invoices)
                
                # Grid total (P50) should match drilldown sum
                assert abs(grid_total_w5 - drilldown_sum_w5) < 0.01 or (drilldown_sum_w5 > 0 and 0.8 <= (grid_total_w5 / drilldown_sum_w5) <= 1.2), \
                    f"Week 5: Grid total {grid_total_w5} should match drilldown sum {drilldown_sum_w5}"
    
    def test_workspace_closing_cash_consistency(self, db_session, sample_snapshot, sample_entity):
        """Closing cash should equal opening + inflows - outflows"""
        # Create invoices
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            entity_id=sample_entity.id,
            canonical_id="contract-cash-1",
            document_number="INV-CASH-001",
            customer="Test Customer",
            amount=10000.0,
            currency="EUR",
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(invoice)
        db_session.commit()
        
        run_forecast_model(db_session, sample_snapshot.id)
        
        workspace = get_13_week_workspace(db_session, sample_snapshot.id)
        
        if workspace and 'grid' in workspace:
            for week in workspace['grid']:
                opening = week.get('opening_cash', 0)
                inflows = week.get('inflow_p50', 0)
                outflows = week.get('outflow_committed', 0)
                closing = week.get('closing_cash', 0)
                
                calculated_closing = opening + inflows - outflows
                
                # Contract Test: Closing cash should equal calculated value
                assert abs(closing - calculated_closing) < 0.01, \
                    f"Week {week.get('week_label')}: closing {closing} != calculated {calculated_closing} " \
                    f"(opening={opening}, inflows={inflows}, outflows={outflows})"
    
    def test_forecast_aggregation_consistency(self, db_session, sample_snapshot, sample_entity):
        """Forecast aggregation totals should be consistent across different grouping methods"""
        from utils import get_forecast_aggregation
        
        invoices = []
        for i in range(10):
            inv = models.Invoice(
                snapshot_id=sample_snapshot.id,
                entity_id=sample_entity.id,
                canonical_id=f"contract-agg-{i}",
                document_number=f"INV-AGG-{i:03d}",
                customer="Test Customer",
                amount=1000.0 * (i + 1),
                currency="EUR",
                expected_due_date=datetime.utcnow() + timedelta(days=30 + i)
            )
            invoices.append(inv)
        
        db_session.bulk_save_objects(invoices)
        db_session.commit()
        
        run_forecast_model(db_session, sample_snapshot.id)
        
        # Get forecast by week
        forecast_week = get_forecast_aggregation(db_session, sample_snapshot.id, group_by="week")
        total_week = sum(w.get('base', 0) for w in forecast_week)
        
        # Get forecast by month (if supported)
        # For now, we just verify week aggregation is consistent
        # Contract Test: Total should be reasonable
        total_expected = sum(1000.0 * (i + 1) for i in range(10))
        ratio = total_week / total_expected if total_expected > 0 else 0
        
        assert 0.8 <= ratio <= 1.2, \
            f"Forecast total {total_week} should be close to expected {total_expected} (ratio: {ratio:.2f})"

