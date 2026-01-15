"""
Pytest configuration and fixtures for Gitto test suite

Markers:
    - unit: Fast unit tests
    - property: Property-based tests (Hypothesis)
    - metamorphic: Metamorphic relation tests
    - slow: Performance and stress tests (excluded by default)
    - integration: Integration tests requiring full stack
    - golden: Golden dataset regression tests
    - roundtrip: Round-trip format validation tests
"""

import pytest
import sys
import os
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
from decimal import Decimal
import models

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


# ═══════════════════════════════════════════════════════════════════════════════
# PYTEST CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Fast unit tests")
    config.addinivalue_line("markers", "property: Property-based tests (Hypothesis)")
    config.addinivalue_line("markers", "metamorphic: Metamorphic relation tests")
    config.addinivalue_line("markers", "slow: Performance/stress tests (excluded by default)")
    config.addinivalue_line("markers", "integration: Integration tests requiring full stack")
    config.addinivalue_line("markers", "golden: Golden dataset regression tests")
    config.addinivalue_line("markers", "roundtrip: Round-trip format validation tests")
    config.addinivalue_line("markers", "mutation: Mutation testing harness")


def pytest_addoption(parser):
    """Add custom CLI options."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--perf-threshold",
        action="store",
        default="30",
        help="Performance test threshold in seconds"
    )


def pytest_collection_modifyitems(config, items):
    """Skip slow tests unless --run-slow is passed."""
    if config.getoption("--run-slow"):
        return
    
    skip_slow = pytest.mark.skip(reason="Need --run-slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    models.Base.metadata.create_all(engine)
    
    # Add DB-level constraints for finance system integrity
    try:
        from migrations.add_db_constraints import add_finance_constraints
        add_finance_constraints(engine)
    except Exception as e:
        # Constraints might not be critical for all tests
        pass
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()

@pytest.fixture
def sample_entity(db_session):
    """Create a sample entity for testing"""
    entity = models.Entity(
        id=1,
        name="Test Entity",
        currency="EUR"
    )
    db_session.add(entity)
    db_session.commit()
    return entity

@pytest.fixture
def sample_snapshot(db_session, sample_entity):
    """Create a sample snapshot for testing"""
    snapshot = models.Snapshot(
        name="Test Snapshot",
        entity_id=sample_entity.id,
        total_rows=0,
        created_at=datetime.utcnow()
    )
    if hasattr(snapshot, 'is_locked'):
        snapshot.is_locked = 0
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot

@pytest.fixture
def sample_bank_account(db_session, sample_entity):
    """Create a sample bank account for testing"""
    account = models.BankAccount(
        entity_id=sample_entity.id,
        account_name="Test Account",
        account_number="123456",
        bank_name="Test Bank",
        currency="EUR",
        balance=100000.0,
        last_sync_at=datetime.utcnow()
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


# ═══════════════════════════════════════════════════════════════════════════════
# CI TRUST GAUNTLET FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def golden_manifest():
    """Load golden manifest JSON with expected results."""
    manifest_path = Path(__file__).parent / "fixtures" / "golden_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return {
        "version": "1.0",
        "description": "Golden dataset expected results",
        "invoices": {
            "total_count": 100,
            "total_amount": 1500000.00,
            "by_currency": {"EUR": 1200000.00, "GBP": 200000.00, "USD": 100000.00}
        },
        "bank_transactions": {
            "total_count": 50,
            "total_inflows": 800000.00,
            "total_outflows": 300000.00
        },
        "reconciliation": {
            "matched_count": 45,
            "matched_amount": 750000.00,
            "unmatched_exposure": 50000.00
        },
        "trust_metrics": {
            "cash_explained_pct": 93.75,
            "unknown_exposure_base": 50000.00,
            "missing_fx_exposure_base": 0.00
        },
        "invariants": {
            "weekly_cash_math": "pass",
            "drilldown_sum_integrity": "pass",
            "reconciliation_conservation": "pass",
            "no_overmatch": "pass",
            "fx_safety": "pass",
            "snapshot_immutability": "pass",
            "idempotency": "pass"
        }
    }


@pytest.fixture(scope="session")
def perf_threshold(request):
    """Get performance threshold from CLI or default."""
    return float(request.config.getoption("--perf-threshold"))


@pytest.fixture
def full_db_session():
    """Create a database session with ALL models (including lineage, trust, invariants)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    
    # Try to create additional model tables
    try:
        import lineage_models
        lineage_models.Base.metadata.create_all(bind=engine)
    except ImportError:
        pass
    
    try:
        import invariant_models
        invariant_models.Base.metadata.create_all(bind=engine)
    except ImportError:
        pass
    
    try:
        import trust_report_models
        trust_report_models.Base.metadata.create_all(bind=engine)
    except ImportError:
        pass
    
    try:
        import health_report_models
        health_report_models.Base.metadata.create_all(bind=engine)
    except ImportError:
        pass
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()


@pytest.fixture
def golden_entity(full_db_session):
    """Create a golden test entity."""
    entity = models.Entity(
        name="Golden Test Corp",
        currency="EUR"
    )
    full_db_session.add(entity)
    full_db_session.commit()
    return entity


@pytest.fixture
def golden_snapshot(full_db_session, golden_entity):
    """Create a golden test snapshot."""
    snapshot = models.Snapshot(
        name="Golden Snapshot Q4 2025",
        entity_id=golden_entity.id,
        total_rows=0,
        created_at=datetime.utcnow(),
        opening_bank_balance=500000.0
    )
    if hasattr(snapshot, 'is_locked'):
        snapshot.is_locked = 0
    if hasattr(snapshot, 'status'):
        snapshot.status = models.SnapshotStatus.DRAFT
    full_db_session.add(snapshot)
    full_db_session.commit()
    full_db_session.refresh(snapshot)
    return snapshot


@pytest.fixture
def golden_bank_account(full_db_session, golden_entity):
    """Create a golden test bank account."""
    account = models.BankAccount(
        entity_id=golden_entity.id,
        account_name="Golden Main Account",
        account_number="GOLDEN-001",
        bank_name="Golden Bank",
        currency="EUR",
        balance=500000.0,
        last_sync_at=datetime.utcnow()
    )
    full_db_session.add(account)
    full_db_session.commit()
    full_db_session.refresh(account)
    return account


@pytest.fixture
def golden_dataset(full_db_session, golden_snapshot, golden_bank_account, golden_manifest):
    """
    Create a complete golden dataset with invoices, transactions, and reconciliation.
    Returns dict with all created records.
    """
    from datetime import datetime, timedelta
    import hashlib
    
    records = {
        "invoices": [],
        "transactions": [],
        "reconciliations": [],
        "fx_rates": []
    }
    
    # Create invoices
    customers = ["ACME Corp", "Beta Industries", "Gamma Holdings", "Delta Tech", "Epsilon Ltd"]
    
    for i in range(100):
        customer = customers[i % len(customers)]
        amount = 10000.0 + (i * 500)  # Range from 10k to 59.5k
        currency = "EUR" if i < 80 else ("GBP" if i < 90 else "USD")
        
        canonical_id = hashlib.sha256(
            f"golden_inv_{i}_{customer}_{amount}_{currency}".encode()
        ).hexdigest()[:32]
        
        invoice = models.Invoice(
            snapshot_id=golden_snapshot.id,
            document_number=f"GOLD-INV-{i+1:04d}",
            customer=customer,
            amount=amount,
            currency=currency,
            invoice_issue_date=datetime.utcnow() - timedelta(days=60-i),
            expected_due_date=datetime.utcnow() + timedelta(days=30+i),
            country="DE" if currency == "EUR" else ("GB" if currency == "GBP" else "US"),
            canonical_id=canonical_id
        )
        full_db_session.add(invoice)
        records["invoices"].append(invoice)
    
    # Create bank transactions
    for i in range(50):
        is_inflow = i < 40
        amount = (16000.0 + i * 400) * (1 if is_inflow else -1)
        
        txn = models.BankTransaction(
            bank_account_id=golden_bank_account.id,
            transaction_date=datetime.utcnow() - timedelta(days=45-i),
            amount=amount,
            currency="EUR",
            reference=f"GOLD-REF-{i+1:04d}",
            counterparty=customers[i % len(customers)],
            transaction_type="customer_receipt" if is_inflow else "supplier_payment",
            is_reconciled=0
        )
        full_db_session.add(txn)
        records["transactions"].append(txn)
    
    full_db_session.commit()
    
    # Refresh to get IDs
    for inv in records["invoices"]:
        full_db_session.refresh(inv)
    for txn in records["transactions"]:
        full_db_session.refresh(txn)
    
    # Create reconciliation records (match 45 out of 50 transactions)
    for i in range(45):
        txn = records["transactions"][i]
        inv = records["invoices"][i]
        
        recon = models.ReconciliationTable(
            bank_transaction_id=txn.id,
            invoice_id=inv.id,
            amount_allocated=abs(txn.amount),
            match_type="exact" if i < 30 else "partial",
            confidence=0.95 if i < 30 else 0.85
        )
        full_db_session.add(recon)
        records["reconciliations"].append(recon)
        
        txn.is_reconciled = 1
    
    # Create FX rates
    for from_curr, to_curr, rate in [("GBP", "EUR", 1.17), ("USD", "EUR", 0.92)]:
        fx = models.WeeklyFXRate(
            snapshot_id=golden_snapshot.id,
            from_currency=from_curr,
            to_currency=to_curr,
            rate=rate
        )
        full_db_session.add(fx)
        records["fx_rates"].append(fx)
    
    full_db_session.commit()
    
    return records


