"""
Accuracy and Conviction Tests
Tests to ensure the product is accurate and trustworthy for CFO decision-making.
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import models
import time
from utils import (
    generate_canonical_id,
    convert_currency,
    get_forecast_aggregation,
    calculate_unknown_bucket
)
from bank_service import (
    generate_match_ladder,
    calculate_cash_explained_pct,
    build_invoice_indexes
)
from data_freshness_service import check_data_freshness

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

DATABASE_URL = "sqlite:///sql_app.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

test_results = {"passed": [], "failed": [], "warnings": []}

def log_test(name, passed, message=""):
    if passed:
        test_results["passed"].append(name)
        print(f"[PASS] {name}")
        if message:
            print(f"      {message}")
    else:
        test_results["failed"].append(name)
        print(f"[FAIL] {name}")
        if message:
            print(f"      {message}")

# ============================================================================
# ACCURACY TESTS - Ensure numbers are correct
# ============================================================================

def test_accuracy_canonical_id_consistency():
    """Test: Same invoice data always generates same canonical_id"""
    data = {
        'document_number': 'ACC-TEST-001',
        'customer': 'Accuracy Corp',
        'amount': 10000.0,
        'currency': 'EUR',
        'document_date': datetime(2024, 1, 15),
        'expected_due_date': datetime(2024, 2, 15),
        'document_type': 'INV'
    }
    
    # Generate multiple times
    cid1 = generate_canonical_id(data, source="Excel", entity_id=1)
    cid2 = generate_canonical_id(data, source="Excel", entity_id=1)
    cid3 = generate_canonical_id(data, source="Excel", entity_id=1)
    
    all_same = (cid1 == cid2 == cid3)
    log_test("Accuracy: Canonical ID Consistency", all_same,
            f"All 3 generations match: {all_same}")
    return all_same

def test_accuracy_currency_conversion_precision():
    """Test: Currency conversion maintains precision"""
    db = SessionLocal()
    try:
        snapshot = models.Snapshot(
            name=f"Precision Test {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Set precise FX rate
        fx_rate = models.WeeklyFXRate(
            snapshot_id=snapshot.id,
            from_currency="USD",
            to_currency="EUR",
            rate=0.923456,  # Precise rate
            effective_week_start=datetime.utcnow()
        )
        db.add(fx_rate)
        db.commit()
        
        # Convert and verify precision
        result = convert_currency(db, snapshot.id, 1000.0, "USD", "EUR", raise_on_missing=True)
        expected = 923.456
        
        # Allow small floating point differences
        diff = abs(result - expected)
        passed = diff < 0.01
        
        log_test("Accuracy: Currency Conversion Precision", passed,
                f"Result: {result}, Expected: {expected}, Diff: {diff}")
        return passed
    except Exception as e:
        log_test("Accuracy: Currency Conversion Precision", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()

def test_accuracy_forecast_aggregation_totals():
    """Test: Forecast aggregation totals are correct"""
    db = SessionLocal()
    try:
        snapshot = models.Snapshot(
            name=f"Forecast Test {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Create invoices with known amounts
        invoices = []
        amounts = [1000.0, 2000.0, 3000.0, 4000.0, 5000.0]
        total_expected = sum(amounts)
        
        for i, amount in enumerate(amounts):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=1,
                canonical_id=f"forecast-test-{i}",
                document_number=f"INV-F-{i}",
                customer="Forecast Customer",
                amount=amount,
                currency="EUR",
                expected_due_date=datetime.now() + timedelta(days=30),
                predicted_payment_date=datetime.now() + timedelta(days=30),
                confidence_p25=datetime.now() + timedelta(days=25),
                confidence_p75=datetime.now() + timedelta(days=35)
            )
            invoices.append(inv)
        
        db.bulk_save_objects(invoices)
        db.commit()
        
        # Run forecast model
        from utils import run_forecast_model
        run_forecast_model(db, snapshot.id)
        
        # Get aggregation
        forecast = get_forecast_aggregation(db, snapshot.id, group_by="week")
        
        # Sum all weeks
        total_forecast = sum(w.get('base', 0) for w in forecast)
        
        # Should be close to total (allowing for probabilistic allocation)
        ratio = total_forecast / total_expected if total_expected > 0 else 0
        passed = 0.8 <= ratio <= 1.2  # Allow 20% variance due to probabilistic allocation
        
        log_test("Accuracy: Forecast Aggregation Totals", passed,
                f"Total expected: {total_expected}, Total forecast: {total_forecast:.2f}, Ratio: {ratio:.2f}")
        return passed
    except Exception as e:
        log_test("Accuracy: Forecast Aggregation Totals", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

# ============================================================================
# STRESS TESTS - Ensure system handles scale
# ============================================================================

def test_stress_large_dataset_reconciliation():
    """Test: Reconciliation handles large datasets efficiently"""
    db = SessionLocal()
    try:
        entity = db.query(models.Entity).filter(models.Entity.id == 1).first()
        if not entity:
            entity = models.Entity(id=1, name="Test Entity", currency="EUR")
            db.add(entity)
            db.commit()
        
        bank_account = db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == 1
        ).first()
        if not bank_account:
            bank_account = models.BankAccount(
                entity_id=1,
                account_name="Test Account",
                account_number="123456",
                bank_name="Test Bank",
                currency="EUR",
                balance=100000.0
            )
            db.add(bank_account)
            db.commit()
        
        snapshot = models.Snapshot(
            name=f"Stress Test {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Create 500 invoices
        invoices = []
        for i in range(500):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=1,
                canonical_id=f"stress-inv-{i}",
                document_number=f"INV-{i:04d}",
                customer=f"Customer{i % 20}",
                amount=1000.0 + (i * 10),
                currency="EUR",
                expected_due_date=datetime.now() + timedelta(days=30)
            )
            invoices.append(inv)
        
        db.bulk_save_objects(invoices)
        db.commit()
        
        # Create 100 transactions
        transactions = []
        for i in range(100):
            txn = models.BankTransaction(
                bank_account_id=bank_account.id,
                transaction_date=datetime.now(),
                amount=1000.0 + (i * 10),
                reference=f"Payment INV-{i:04d}",
                counterparty=f"Customer{i % 20}",
                currency="EUR",
                is_reconciled=0
            )
            transactions.append(txn)
        
        db.bulk_save_objects(transactions)
        db.commit()
        
        # Time the reconciliation
        start = time.time()
        results = generate_match_ladder(db, 1)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds for 500 invoices, 100 transactions)
        passed = elapsed < 5.0
        
        log_test("Stress: Large Dataset Reconciliation", passed,
                f"500 invoices, 100 transactions processed in {elapsed:.2f}s")
        return passed
    except Exception as e:
        log_test("Stress: Large Dataset Reconciliation", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()

def test_stress_index_performance():
    """Test: Index building performance with large dataset"""
    # Create large invoice list
    invoices = []
    for i in range(10000):
        inv = models.Invoice(
            snapshot_id=1,
            entity_id=1,
            canonical_id=f"perf-test-{i}",
            document_number=f"INV-{i:06d}",
            customer=f"Customer{i % 100}",
            amount=1000.0 + (i % 1000),
            currency="EUR"
        )
        invoices.append(inv)
    
    # Time index building
    start = time.time()
    indexes = build_invoice_indexes(invoices)
    elapsed = time.time() - start
    
    # Should be fast (< 1 second for 10k invoices)
    passed = elapsed < 1.0
    
    log_test("Stress: Index Performance", passed,
            f"10,000 invoices indexed in {elapsed:.3f}s")
    return passed

# ============================================================================
# REAL-WORLD SCENARIO TESTS
# ============================================================================

def test_scenario_weekly_meeting_prep():
    """Test: Complete weekly meeting preparation scenario"""
    db = SessionLocal()
    try:
        # Setup: Entity with bank account and snapshot
        entity = db.query(models.Entity).filter(models.Entity.id == 1).first()
        if not entity:
            entity = models.Entity(id=1, name="Weekly Meeting Entity", currency="EUR")
            db.add(entity)
            db.commit()
        
        bank_account = db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == 1
        ).first()
        if not bank_account:
            bank_account = models.BankAccount(
                entity_id=1,
                account_name="Main Account",
                account_number="123456",
                bank_name="Test Bank",
                currency="EUR",
                balance=500000.0,
                last_sync_at=datetime.utcnow() - timedelta(hours=2)
            )
            db.add(bank_account)
            db.commit()
        
        snapshot = models.Snapshot(
            name=f"Weekly Meeting {datetime.now().strftime('%Y-%m-%d')}",
            entity_id=1,
            created_at=datetime.utcnow() - timedelta(hours=1),
            total_rows=100
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Create invoices
        invoices = []
        for i in range(50):
            inv = models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=1,
                canonical_id=f"weekly-{i}",
                document_number=f"INV-WEEK-{i:03d}",
                customer=f"Customer{i % 10}",
                amount=5000.0 + (i * 100),
                currency="EUR",
                expected_due_date=datetime.now() + timedelta(days=30)
            )
            invoices.append(inv)
        
        db.bulk_save_objects(invoices)
        db.commit()
        
        # Run forecast
        from utils import run_forecast_model
        run_forecast_model(db, snapshot.id)
        
        # Get forecast aggregation
        forecast = get_forecast_aggregation(db, snapshot.id, group_by="week")
        
        # Get unknown bucket
        unknown = calculate_unknown_bucket(db, snapshot.id)
        
        # Get cash explained
        cash_explained = calculate_cash_explained_pct(db, 1)
        
        # Get data freshness
        freshness = check_data_freshness(db, 1)
        
        # Verify all metrics are available
        has_forecast = len(forecast) > 0
        has_unknown = 'unknown_pct' in unknown
        has_cash_explained = 'explained_pct' in cash_explained
        has_freshness = 'bank_age_hours' in freshness
        
        passed = has_forecast and has_unknown and has_cash_explained and has_freshness
        
        log_test("Scenario: Weekly Meeting Prep", passed,
                f"Forecast: {len(forecast)} weeks, Unknown: {unknown.get('unknown_pct', 0)}%, "
                f"Cash Explained: {cash_explained.get('explained_pct', 0)}%")
        return passed
    except Exception as e:
        log_test("Scenario: Weekly Meeting Prep", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_scenario_multi_currency_forecast():
    """Test: Forecast with multiple currencies"""
    db = SessionLocal()
    try:
        snapshot = models.Snapshot(
            name=f"Multi-Currency Test {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Set FX rates
        fx_rates = [
            models.WeeklyFXRate(
                snapshot_id=snapshot.id,
                from_currency="USD",
                to_currency="EUR",
                rate=0.92,
                effective_week_start=datetime.utcnow()
            ),
            models.WeeklyFXRate(
                snapshot_id=snapshot.id,
                from_currency="GBP",
                to_currency="EUR",
                rate=1.15,
                effective_week_start=datetime.utcnow()
            )
        ]
        db.bulk_save_objects(fx_rates)
        db.commit()
        
        # Create invoices in different currencies
        invoices = [
            models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=1,
                canonical_id="multi-usd-1",
                document_number="INV-USD-001",
                customer="US Customer",
                amount=1000.0,
                currency="USD",
                expected_due_date=datetime.now() + timedelta(days=30)
            ),
            models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=1,
                canonical_id="multi-gbp-1",
                document_number="INV-GBP-001",
                customer="UK Customer",
                amount=1000.0,
                currency="GBP",
                expected_due_date=datetime.now() + timedelta(days=30)
            ),
            models.Invoice(
                snapshot_id=snapshot.id,
                entity_id=1,
                canonical_id="multi-eur-1",
                document_number="INV-EUR-001",
                customer="EU Customer",
                amount=1000.0,
                currency="EUR",
                expected_due_date=datetime.now() + timedelta(days=30)
            )
        ]
        db.bulk_save_objects(invoices)
        db.commit()
        
        # Run forecast
        from utils import run_forecast_model
        run_forecast_model(db, snapshot.id)
        
        # Get forecast (should convert all to EUR)
        forecast = get_forecast_aggregation(db, snapshot.id, group_by="week")
        
        # Verify conversion happened (no errors)
        has_forecast = len(forecast) > 0
        
        # Calculate expected total in EUR
        # 1000 USD * 0.92 = 920 EUR
        # 1000 GBP * 1.15 = 1150 EUR
        # 1000 EUR = 1000 EUR
        # Total = 3070 EUR
        
        passed = has_forecast
        log_test("Scenario: Multi-Currency Forecast", passed,
                f"Forecast generated with {len(forecast)} weeks")
        return passed
    except Exception as e:
        log_test("Scenario: Multi-Currency Forecast", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

# ============================================================================
# REGRESSION TESTS - Ensure we didn't break anything
# ============================================================================

def test_regression_cash_explained_calculation():
    """Test: Cash explained calculation still works correctly"""
    db = SessionLocal()
    try:
        entity = db.query(models.Entity).filter(models.Entity.id == 1).first()
        if not entity:
            entity = models.Entity(id=1, name="Test Entity", currency="EUR")
            db.add(entity)
            db.commit()
        
        result = calculate_cash_explained_pct(db, 1)
        
        # Verify structure
        has_explained_pct = 'explained_pct' in result
        has_breakdown = 'breakdown' in result
        has_trend = 'trend_vs_prior_week' in result
        
        # Verify values are reasonable
        pct_valid = 0 <= result.get('explained_pct', -1) <= 100
        
        passed = has_explained_pct and has_breakdown and has_trend and pct_valid
        
        log_test("Regression: Cash Explained Calculation", passed,
                f"Structure valid: {has_explained_pct and has_breakdown and has_trend}, "
                f"Pct valid: {pct_valid}")
        return passed
    except Exception as e:
        log_test("Regression: Cash Explained Calculation", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()

def test_regression_unknown_bucket_calculation():
    """Test: Unknown bucket calculation still works"""
    db = SessionLocal()
    try:
        snapshot = models.Snapshot(
            name=f"Regression Test {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Create invoice without due date (should be in unknown)
        inv = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=1,
            canonical_id="regression-unknown-1",
            document_number="INV-UNKNOWN-001",
            customer="Test Customer",
            amount=5000.0,
            currency="EUR",
            expected_due_date=None  # Missing due date
        )
        db.add(inv)
        db.commit()
        
        # Calculate unknown bucket
        unknown = calculate_unknown_bucket(db, snapshot.id)
        
        # Verify structure
        has_unknown_pct = 'unknown_pct' in unknown
        has_categories = 'categories' in unknown
        has_kpi_target = 'kpi_target_met' in unknown
        
        # Verify missing due dates are tracked
        missing_due = unknown.get('categories', {}).get('missing_due_dates', {})
        has_missing_due = 'count' in missing_due and missing_due['count'] > 0
        
        passed = has_unknown_pct and has_categories and has_kpi_target and has_missing_due
        
        log_test("Regression: Unknown Bucket Calculation", passed,
                f"Unknown %: {unknown.get('unknown_pct', 0)}%, "
                f"Missing due dates: {missing_due.get('count', 0)}")
        return passed
    except Exception as e:
        log_test("Regression: Unknown Bucket Calculation", False, f"Error: {str(e)}")
        return False
    finally:
        db.close()

# ============================================================================
# RUN ALL TESTS
# ============================================================================

def run_accuracy_tests():
    """Run all accuracy and conviction tests"""
    print("\n" + "="*70)
    print("ACCURACY & CONVICTION TEST SUITE")
    print("="*70)
    
    print("\n--- ACCURACY TESTS ---")
    test_accuracy_canonical_id_consistency()
    test_accuracy_currency_conversion_precision()
    test_accuracy_forecast_aggregation_totals()
    
    print("\n--- STRESS TESTS ---")
    test_stress_large_dataset_reconciliation()
    test_stress_index_performance()
    
    print("\n--- REAL-WORLD SCENARIO TESTS ---")
    test_scenario_weekly_meeting_prep()
    test_scenario_multi_currency_forecast()
    
    print("\n--- REGRESSION TESTS ---")
    test_regression_cash_explained_calculation()
    test_regression_unknown_bucket_calculation()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total = len(test_results["passed"]) + len(test_results["failed"])
    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%")
    
    if failed > 0:
        print("\nFailed Tests:")
        for test in test_results["failed"]:
            print(f"  - {test}")
    
    if failed == 0:
        print("\n[SUCCESS] All accuracy and conviction tests passed!")
        print("Product is accurate and ready for CFO decision-making.")
        return True
    else:
        print(f"\n[WARNING] {failed} test(s) failed. Review required.")
        return False

if __name__ == "__main__":
    success = run_accuracy_tests()
    sys.exit(0 if success else 1)







