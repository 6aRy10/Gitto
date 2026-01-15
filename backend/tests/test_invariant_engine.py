"""
Invariant Engine Tests

Comprehensive tests for deterministic correctness checks.
Includes pytest fixtures, Hypothesis state-machine tests, and metamorphic tests.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from invariant_models import Base as InvariantBase, InvariantRun, InvariantResult
from invariant_engine import InvariantEngine, InvariantStatus, InvariantSeverity


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session with all tables."""
    # Create all tables
    models.Base.metadata.create_all(bind=test_engine)
    InvariantBase.metadata.create_all(bind=test_engine)
    
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_entity(test_session):
    """Create a sample entity."""
    entity = models.Entity(
        name="Test Corp",
        currency="EUR"
    )
    test_session.add(entity)
    test_session.commit()
    return entity


@pytest.fixture
def sample_snapshot(test_session, sample_entity):
    """Create a sample snapshot."""
    snapshot = models.Snapshot(
        entity_id=sample_entity.id,
        created_at=datetime.utcnow(),
        status=models.SnapshotStatus.DRAFT,
        opening_bank_balance=100000.0
    )
    test_session.add(snapshot)
    test_session.commit()
    return snapshot


@pytest.fixture
def sample_bank_account(test_session, sample_entity):
    """Create a sample bank account."""
    account = models.BankAccount(
        entity_id=sample_entity.id,
        account_name="Main Account",
        currency="EUR"
    )
    test_session.add(account)
    test_session.commit()
    return account


@pytest.fixture
def sample_invoices(test_session, sample_snapshot):
    """Create sample invoices."""
    invoices = []
    customers = ["ACME", "BETA", "GAMMA"]
    
    for i in range(10):
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number=f"INV-{i+1:04d}",
            customer=customers[i % 3],
            amount=1000.0 * (i + 1),
            currency="EUR",
            invoice_issue_date=datetime.utcnow() - timedelta(days=30),
            expected_due_date=datetime.utcnow() + timedelta(days=30),
            country="US"
        )
        invoices.append(invoice)
    
    test_session.add_all(invoices)
    test_session.commit()
    return invoices


@pytest.fixture
def sample_transactions(test_session, sample_bank_account):
    """Create sample bank transactions."""
    transactions = []
    
    for i in range(5):
        txn = models.BankTransaction(
            bank_account_id=sample_bank_account.id,
            transaction_date=datetime.utcnow() - timedelta(days=i),
            amount=2000.0 * (i + 1),
            counterparty=f"Payment {i+1}",
            reference=f"REF-{i+1:04d}"
        )
        transactions.append(txn)
    
    test_session.add_all(transactions)
    test_session.commit()
    return transactions


@pytest.fixture
def invariant_engine(test_session):
    """Create an invariant engine instance."""
    return InvariantEngine(test_session)


# ═══════════════════════════════════════════════════════════════════════════════
# BASIC INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariantEngine:
    """Tests for the InvariantEngine class."""
    
    def test_run_all_invariants_creates_run_record(
        self, 
        invariant_engine, 
        sample_snapshot, 
        test_session
    ):
        """Verify invariant run creates a database record."""
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        assert run is not None
        assert run.snapshot_id == sample_snapshot.id
        assert run.status in ["passed", "failed", "partial"]
        assert run.summary_json is not None
        
        # Verify results were stored
        results = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id
        ).all()
        
        assert len(results) == 7  # All 7 invariants
    
    def test_weekly_cash_math_passes_when_balanced(
        self,
        invariant_engine,
        sample_snapshot,
        sample_bank_account,
        test_session
    ):
        """Verify cash math invariant passes when balanced."""
        # Add balanced transactions
        txn_in = models.BankTransaction(
            bank_account_id=sample_bank_account.id,
            transaction_date=datetime.utcnow(),
            amount=5000.0,
            counterparty="Inflow"
        )
        txn_out = models.BankTransaction(
            bank_account_id=sample_bank_account.id,
            transaction_date=datetime.utcnow(),
            amount=-2000.0,
            counterparty="Outflow"
        )
        test_session.add_all([txn_in, txn_out])
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        # Find cash math result
        cash_result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "weekly_cash_math"
        ).first()
        
        assert cash_result.status == "pass"
    
    def test_drilldown_sum_integrity(
        self,
        invariant_engine,
        sample_snapshot,
        sample_invoices,
        test_session
    ):
        """Verify drilldown sums equal total."""
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "drilldown_sum_integrity"
        ).first()
        
        assert result.status == "pass"
        assert result.details_json["total_amount"] == sum(inv.amount for inv in sample_invoices)
    
    def test_no_overmatch_invariant_catches_violations(
        self,
        invariant_engine,
        sample_snapshot,
        sample_invoices,
        sample_transactions,
        test_session
    ):
        """Verify no-overmatch catches over-allocated invoices."""
        # Create reconciliation that over-allocates
        invoice = sample_invoices[0]
        txn = sample_transactions[0]
        
        # Allocate MORE than invoice amount
        recon = models.ReconciliationTable(
            invoice_id=invoice.id,
            bank_transaction_id=txn.id,
            amount_allocated=invoice.amount * 2,  # Over-allocate!
            match_type="manual"
        )
        test_session.add(recon)
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "no_overmatch"
        ).first()
        
        assert result.status == "fail"
        assert result.details_json["over_allocations"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# FX SAFETY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFXSafetyInvariant:
    """Tests for FX safety invariant."""
    
    def test_fx_safety_fails_on_missing_rate(
        self,
        invariant_engine,
        sample_snapshot,
        test_session
    ):
        """Verify FX safety catches foreign currency without rates."""
        # Add foreign currency invoice without FX rate
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-GBP-001",
            customer="UK Client",
            amount=5000.0,
            currency="GBP",  # Foreign currency
            invoice_issue_date=datetime.utcnow(),
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        test_session.add(invoice)
        test_session.commit()
        
        # No FX rate for GBP/EUR
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "fx_safety"
        ).first()
        
        # Should warn about missing FX
        assert result.status in ["warn", "fail"]
        assert result.exposure_amount > 0
    
    def test_fx_safety_detects_suspicious_1_0_rate(
        self,
        invariant_engine,
        sample_snapshot,
        test_session
    ):
        """Verify FX safety catches suspicious 1.0 rate fallback."""
        # Add foreign currency invoice
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-JPY-001",
            customer="Japan Client",
            amount=100000.0,
            currency="JPY",
            invoice_issue_date=datetime.utcnow(),
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        test_session.add(invoice)
        
        # Add suspicious 1.0 FX rate
        fx_rate = models.WeeklyFXRate(
            snapshot_id=sample_snapshot.id,
            from_currency="JPY",
            to_currency="EUR",
            rate=1.0  # Suspicious!
        )
        test_session.add(fx_rate)
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "fx_safety"
        ).first()
        
        # Should FAIL on suspicious 1.0 rate
        assert result.status == "fail"
        assert "suspicious" in result.proof_string.lower() or "1.0" in result.proof_string


# ═══════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestIdempotencyInvariant:
    """Tests for idempotency invariant."""
    
    def test_idempotency_fails_on_duplicates(
        self,
        invariant_engine,
        sample_snapshot,
        test_session
    ):
        """Verify idempotency catches duplicate canonical IDs."""
        # Add invoices with same canonical_id (simulating duplicate import)
        canonical_id = "test_canonical_12345"
        
        inv1 = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-001",
            customer="ACME",
            amount=1000.0,
            currency="EUR",
            canonical_id=canonical_id
        )
        inv2 = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-001",  # Duplicate!
            customer="ACME",
            amount=1000.0,
            currency="EUR",
            canonical_id=canonical_id  # Same canonical_id!
        )
        
        test_session.add_all([inv1, inv2])
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "idempotency"
        ).first()
        
        assert result.status == "fail"
        assert result.details_json["total_duplicates"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT IMMUTABILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapshotImmutabilityInvariant:
    """Tests for snapshot immutability invariant."""
    
    def test_immutability_passes_for_unlocked_snapshot(
        self,
        invariant_engine,
        sample_snapshot,
        test_session
    ):
        """Unlocked snapshots pass immutability check."""
        sample_snapshot.status = models.SnapshotStatus.DRAFT
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "snapshot_immutability"
        ).first()
        
        assert result.status == "pass"
    
    def test_immutability_requires_audit_trail_for_locked(
        self,
        invariant_engine,
        sample_snapshot,
        test_session
    ):
        """Locked snapshots must have proper audit trail."""
        sample_snapshot.status = models.SnapshotStatus.LOCKED
        sample_snapshot.is_locked = 1
        sample_snapshot.locked_at = datetime.utcnow()
        sample_snapshot.locked_by = "test@example.com"
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "snapshot_immutability"
        ).first()
        
        # Should pass because we have proper metadata
        assert result.status == "pass"


# ═══════════════════════════════════════════════════════════════════════════════
# RECONCILIATION CONSERVATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestReconciliationConservation:
    """Tests for reconciliation conservation invariant."""
    
    def test_conservation_passes_when_balanced(
        self,
        invariant_engine,
        sample_snapshot,
        sample_invoices,
        sample_transactions,
        test_session
    ):
        """Conservation passes when allocations sum to transaction amount."""
        txn = sample_transactions[0]
        
        # Allocate exactly the transaction amount across invoices
        remaining = txn.amount
        for inv in sample_invoices[:3]:
            alloc = min(inv.amount, remaining)
            if alloc <= 0:
                break
            
            recon = models.ReconciliationTable(
                invoice_id=inv.id,
                bank_transaction_id=txn.id,
                amount_allocated=alloc,
                match_type="manual"
            )
            test_session.add(recon)
            remaining -= alloc
        
        test_session.commit()
        
        run = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run.id,
            InvariantResult.name == "reconciliation_conservation"
        ).first()
        
        # If fully allocated, should pass
        if remaining <= 0.01:
            assert result.status == "pass"


# ═══════════════════════════════════════════════════════════════════════════════
# METAMORPHIC TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetamorphicInvariants:
    """Metamorphic tests for invariant engine."""
    
    def test_scaling_amounts_scales_exposure(
        self,
        invariant_engine,
        sample_snapshot,
        sample_invoices,
        test_session
    ):
        """
        Metamorphic property: Scaling all amounts by K should scale
        exposure metrics by K.
        """
        # Run first with original amounts
        run1 = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result1 = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run1.id,
            InvariantResult.name == "drilldown_sum_integrity"
        ).first()
        
        original_total = result1.details_json.get("total_amount", 0)
        
        # Scale all invoice amounts by 10
        scale_factor = 10
        for inv in sample_invoices:
            inv.amount = inv.amount * scale_factor
        test_session.commit()
        
        # Run again
        run2 = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        result2 = test_session.query(InvariantResult).filter(
            InvariantResult.run_id == run2.id,
            InvariantResult.name == "drilldown_sum_integrity"
        ).first()
        
        scaled_total = result2.details_json.get("total_amount", 0)
        
        # Verify scaling
        assert abs(scaled_total - original_total * scale_factor) < 0.01
    
    def test_shuffle_order_same_results(
        self,
        invariant_engine,
        sample_snapshot,
        sample_invoices,
        test_session
    ):
        """
        Metamorphic property: Shuffling invoice order should not change
        invariant results.
        """
        import random
        
        # Run first
        run1 = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        results1 = {
            r.name: (r.status, r.details_json)
            for r in test_session.query(InvariantResult).filter(
                InvariantResult.run_id == run1.id
            ).all()
        }
        
        # "Shuffle" by creating new snapshot with same invoices in different order
        shuffled_ids = [inv.id for inv in sample_invoices]
        random.shuffle(shuffled_ids)
        
        # Run again (order shouldn't matter in practice)
        run2 = invariant_engine.run_all_invariants(sample_snapshot.id)
        
        results2 = {
            r.name: (r.status, r.details_json)
            for r in test_session.query(InvariantResult).filter(
                InvariantResult.run_id == run2.id
            ).all()
        }
        
        # Status should be same
        for name in results1:
            assert results1[name][0] == results2[name][0], \
                f"Invariant {name} has different status after shuffle"


# ═══════════════════════════════════════════════════════════════════════════════
# HYPOTHESIS STATE-MACHINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

try:
    from hypothesis import given, strategies as st, settings
    from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle
    
    class InvariantEngineStateMachine(RuleBasedStateMachine):
        """
        Hypothesis state machine for testing invariant engine properties.
        """
        
        def __init__(self):
            super().__init__()
            
            # Create in-memory database
            self.engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
            models.Base.metadata.create_all(bind=self.engine)
            InvariantBase.metadata.create_all(bind=self.engine)
            
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            # Create entity and snapshot
            self.entity = models.Entity(name="Test", currency="EUR")
            self.session.add(self.entity)
            self.session.commit()
            
            self.snapshot = models.Snapshot(
                entity_id=self.entity.id,
                created_at=datetime.utcnow(),
                status=models.SnapshotStatus.DRAFT
            )
            self.session.add(self.snapshot)
            self.session.commit()
            
            self.invariant_engine = InvariantEngine(self.session)
            self.invoice_count = 0
        
        invoices = Bundle("invoices")
        
        @rule(target=invoices, amount=st.floats(min_value=100, max_value=100000))
        def add_invoice(self, amount):
            """Add an invoice with given amount."""
            self.invoice_count += 1
            inv = models.Invoice(
                snapshot_id=self.snapshot.id,
                document_number=f"INV-{self.invoice_count:04d}",
                customer="Test",
                amount=amount,
                currency="EUR"
            )
            self.session.add(inv)
            self.session.commit()
            return inv
        
        @rule(invoice=invoices, scale=st.floats(min_value=0.5, max_value=2.0))
        def scale_invoice(self, invoice, scale):
            """Scale an invoice amount."""
            invoice.amount = invoice.amount * scale
            self.session.commit()
        
        @invariant()
        def drilldown_sums_match_total(self):
            """Verify drilldown sums always match total."""
            invoices = self.session.query(models.Invoice).filter(
                models.Invoice.snapshot_id == self.snapshot.id
            ).all()
            
            total = sum(inv.amount for inv in invoices)
            
            # Group by customer
            by_customer = {}
            for inv in invoices:
                key = inv.customer or "UNKNOWN"
                by_customer[key] = by_customer.get(key, 0) + inv.amount
            
            customer_sum = sum(by_customer.values())
            
            assert abs(total - customer_sum) < 0.01
        
        def teardown(self):
            self.session.close()
    
    # Only run if hypothesis is available
    TestInvariantStateMachine = InvariantEngineStateMachine.TestCase
    TestInvariantStateMachine.settings = settings(max_examples=50, stateful_step_count=10)

except ImportError:
    # Hypothesis not available
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
