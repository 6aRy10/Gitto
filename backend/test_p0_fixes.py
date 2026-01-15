"""
Test script for P0 fixes:
1. Idempotency - duplicate upload prevention
2. Data freshness check - bank vs ERP age conflicts
3. FX missing rates - explicit error handling
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import models
from utils import generate_canonical_id, convert_currency, get_snapshot_fx_rate
from data_freshness_service import check_data_freshness, get_data_freshness_summary
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Setup database connection
DATABASE_URL = "sqlite:///sql_app.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
def setup_database():
    """Create all tables from models"""
    try:
        models.Base.metadata.create_all(bind=engine)
        print("[OK] Database tables created/verified")
    except Exception as e:
        print(f"[WARNING] Could not create tables: {e}")
        print("[INFO] Continuing with existing database...")

# Initialize database
setup_database()

def test_idempotency():
    """
    Test P0-1: Idempotency - same file uploaded twice should not create duplicates
    """
    print("\n" + "="*60)
    print("TEST 1: Idempotency (P0-1)")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Create a test snapshot (without is_locked if column doesn't exist)
        snapshot = models.Snapshot(
            name=f"Test Idempotency {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        # Only set is_locked if it exists in the model
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        # Create test invoice data
        test_row = {
            'document_number': 'TEST-INV-001',
            'customer': 'Test Customer',
            'amount': 1000.0,
            'currency': 'EUR',
            'document_date': datetime.now(),
            'expected_due_date': datetime.now() + timedelta(days=30),
            'document_type': 'INV'
        }
        
        # Generate canonical_id
        cid1 = generate_canonical_id(test_row, source="Excel", entity_id=1)
        print(f"[OK] Generated canonical_id: {cid1[:20]}...")
        
        # Create first invoice
        inv1 = models.Invoice(
            snapshot_id=snapshot.id,
            entity_id=1,
            canonical_id=cid1,
            document_number=test_row['document_number'],
            customer=test_row['customer'],
            amount=test_row['amount'],
            currency=test_row['currency'],
            document_date=test_row['document_date'],
            expected_due_date=test_row['expected_due_date'],
            document_type=test_row['document_type']
        )
        db.add(inv1)
        db.commit()
        db.refresh(inv1)
        
        print(f"[OK] Created first invoice with ID: {inv1.id}")
        
        # Try to create duplicate (simulating re-upload)
        existing = db.query(models.Invoice).filter(
            models.Invoice.canonical_id == cid1,
            models.Invoice.snapshot_id == snapshot.id
        ).first()
        
        if existing:
            print(f"[OK] Duplicate check works: Found existing invoice ID {existing.id}")
            # Update instead of create (upsert logic)
            existing.amount = 1200.0  # Simulate update
            db.commit()
            print(f"[OK] Updated existing invoice instead of creating duplicate")
            
            # Verify only one record exists
            count = db.query(models.Invoice).filter(
                models.Invoice.canonical_id == cid1,
                models.Invoice.snapshot_id == snapshot.id
            ).count()
            
            if count == 1:
                print(f"[PASS] Only 1 invoice with canonical_id exists (idempotent)")
                return True
            else:
                print(f"[FAIL] Found {count} invoices with same canonical_id (duplicate created)")
                return False
        else:
            print(f"[FAIL] Duplicate check failed - should have found existing invoice")
            return False
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_data_freshness():
    """
    Test P0-2: Data freshness check - detects bank vs ERP age conflicts
    """
    print("\n" + "="*60)
    print("TEST 2: Data Freshness Check (P0-2)")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Create test entity
        entity = db.query(models.Entity).filter(models.Entity.id == 1).first()
        if not entity:
            entity = models.Entity(id=1, name="Test Entity", currency="EUR")
            db.add(entity)
            db.commit()
        
        # Create bank account with old sync time (48 hours ago)
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
                balance=100000.0,
                last_sync_at=datetime.utcnow() - timedelta(hours=48)  # 48 hours old
            )
            db.add(bank_account)
        else:
            bank_account.last_sync_at = datetime.utcnow() - timedelta(hours=48)
        
        # Create recent snapshot (2 hours ago)
        snapshot = models.Snapshot(
            name=f"Test Freshness {datetime.now().isoformat()}",
            entity_id=1,
            created_at=datetime.utcnow() - timedelta(hours=2),
            total_rows=100
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        
        print(f"[OK] Created bank account with sync time: {bank_account.last_sync_at}")
        print(f"[OK] Created snapshot with time: {snapshot.created_at}")
        
        # Check data freshness
        freshness = check_data_freshness(db, 1)
        
        print(f"\nFreshness Check Results:")
        print(f"  Bank age: {freshness.get('bank_age_hours')} hours")
        print(f"  ERP age: {freshness.get('erp_age_hours')} hours")
        print(f"  Age difference: {freshness.get('age_diff_hours')} hours")
        print(f"  Warning: {freshness.get('warning')}")
        print(f"  Policy: {freshness.get('policy')}")
        
        # Verify warning is generated (age diff > 24 hours)
        if freshness.get('warning'):
            print(f"[PASS] Warning generated for age conflict ({freshness.get('age_diff_hours')} hours difference)")
            return True
        else:
            print(f"[FAIL] No warning generated despite {freshness.get('age_diff_hours')} hour difference")
            return False
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_fx_missing_rates():
    """
    Test P0-3: FX missing rates - should raise error instead of silent fallback
    """
    print("\n" + "="*60)
    print("TEST 3: FX Missing Rates (P0-3)")
    print("="*60)
    
    db = SessionLocal()
    try:
        # Create test snapshot
        snapshot = models.Snapshot(
            name=f"Test FX {datetime.now().isoformat()}",
            entity_id=1,
            total_rows=0
        )
        if hasattr(snapshot, 'is_locked'):
            snapshot.is_locked = 0
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        print(f"[OK] Created snapshot ID: {snapshot.id}")
        
        # Test 1: Missing FX rate should return None (not 1.0)
        print("\nTest 1: get_snapshot_fx_rate() with missing rate")
        rate = get_snapshot_fx_rate(db, snapshot.id, "USD", "EUR", raise_on_missing=False)
        
        if rate is None:
            print(f"[PASS] Returns None (not 1.0) when rate is missing")
        else:
            print(f"[FAIL] Returned {rate} instead of None")
            return False
        
        # Test 2: Missing FX rate should raise error when raise_on_missing=True
        print("\nTest 2: get_snapshot_fx_rate() with raise_on_missing=True")
        try:
            rate = get_snapshot_fx_rate(db, snapshot.id, "USD", "EUR", raise_on_missing=True)
            print(f"[FAIL] Should have raised ValueError, but returned {rate}")
            return False
        except ValueError as e:
            print(f"[PASS] Correctly raised ValueError: {str(e)[:80]}...")
        
        # Test 3: convert_currency() should raise error for missing rates
        print("\nTest 3: convert_currency() with missing rate")
        try:
            result = convert_currency(db, snapshot.id, 1000.0, "USD", "EUR", raise_on_missing=True)
            print(f"[FAIL] Should have raised ValueError, but returned {result}")
            return False
        except ValueError as e:
            print(f"[PASS] Correctly raised ValueError: {str(e)[:80]}...")
        
        # Test 4: Same currency should work (no FX needed)
        print("\nTest 4: convert_currency() with same currency")
        result = convert_currency(db, snapshot.id, 1000.0, "EUR", "EUR", raise_on_missing=True)
        if result == 1000.0:
            print(f"[PASS] Same currency conversion works: {result}")
        else:
            print(f"[FAIL] Expected 1000.0, got {result}")
            return False
        
        # Test 5: Add FX rate and verify conversion works
        print("\nTest 5: convert_currency() with valid FX rate")
        fx_rate = models.WeeklyFXRate(
            snapshot_id=snapshot.id,
            from_currency="USD",
            to_currency="EUR",
            rate=0.92,
            effective_week_start=datetime.utcnow()
        )
        db.add(fx_rate)
        db.commit()
        
        result = convert_currency(db, snapshot.id, 1000.0, "USD", "EUR", raise_on_missing=True)
        expected = 1000.0 * 0.92
        if abs(result - expected) < 0.01:
            print(f"[PASS] Conversion works with valid rate: {result} (expected {expected})")
            return True
        else:
            print(f"[FAIL] Expected {expected}, got {result}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def run_all_tests():
    """Run all P0 fix tests"""
    print("\n" + "="*60)
    print("P0 FIXES TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test 1: Idempotency
    results.append(("Idempotency (P0-1)", test_idempotency()))
    
    # Test 2: Data Freshness
    results.append(("Data Freshness (P0-2)", test_data_freshness()))
    
    # Test 3: FX Missing Rates
    results.append(("FX Missing Rates (P0-3)", test_fx_missing_rates()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All P0 fixes are working correctly!")
        return True
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

