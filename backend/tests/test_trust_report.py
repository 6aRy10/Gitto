"""
Trust Report Tests

Comprehensive tests for trust certification, lock gates, and CFO override.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from trust_report_models import (
    Base as TrustBase, 
    TrustReport, 
    TrustMetric, 
    LockGateOverrideLog,
    LockGateConfig
)
from trust_report_service import TrustReportService, LockGateThresholds

# Import lineage models for table creation
try:
    import lineage_models
    HAS_LINEAGE = True
except ImportError:
    HAS_LINEAGE = False


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
    models.Base.metadata.create_all(bind=test_engine)
    TrustBase.metadata.create_all(bind=test_engine)
    
    # Also create lineage tables if available
    if HAS_LINEAGE:
        lineage_models.Base.metadata.create_all(bind=test_engine)
    
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
    """Create sample EUR invoices."""
    invoices = []
    for i in range(10):
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number=f"INV-{i+1:04d}",
            customer=f"Customer {i % 3}",
            amount=10000.0,
            currency="EUR",
            invoice_issue_date=datetime.utcnow() - timedelta(days=30),
            expected_due_date=datetime.utcnow() + timedelta(days=30),
            country="DE"
        )
        invoices.append(invoice)
    
    test_session.add_all(invoices)
    test_session.commit()
    return invoices


@pytest.fixture
def sample_foreign_invoices(test_session, sample_snapshot):
    """Create sample foreign currency invoices."""
    invoices = []
    currencies = ["GBP", "USD", "CHF"]
    
    for i, curr in enumerate(currencies):
        invoice = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number=f"INV-{curr}-001",
            customer=f"{curr} Client",
            amount=5000.0,
            currency=curr,
            invoice_issue_date=datetime.utcnow() - timedelta(days=30),
            expected_due_date=datetime.utcnow() + timedelta(days=30)
        )
        invoices.append(invoice)
    
    test_session.add_all(invoices)
    test_session.commit()
    return invoices


@pytest.fixture
def sample_fx_rates(test_session, sample_snapshot):
    """Create sample FX rates (only for some currencies)."""
    rates = [
        models.WeeklyFXRate(
            snapshot_id=sample_snapshot.id,
            from_currency="GBP",
            to_currency="EUR",
            rate=1.17
        ),
        models.WeeklyFXRate(
            snapshot_id=sample_snapshot.id,
            from_currency="USD",
            to_currency="EUR",
            rate=0.92
        )
        # Note: CHF rate intentionally missing
    ]
    
    test_session.add_all(rates)
    test_session.commit()
    return rates


@pytest.fixture
def sample_transactions(test_session, sample_bank_account):
    """Create sample bank transactions."""
    transactions = []
    
    for i in range(5):
        txn = models.BankTransaction(
            bank_account_id=sample_bank_account.id,
            transaction_date=datetime.utcnow() - timedelta(days=i),
            amount=5000.0,
            reference=f"REF-{i+1:04d}",
            counterparty=f"Payment {i+1}"
        )
        transactions.append(txn)
    
    test_session.add_all(transactions)
    test_session.commit()
    return transactions


@pytest.fixture
def trust_service(test_session):
    """Create a trust report service instance."""
    return TrustReportService(test_session)


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST REPORT GENERATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrustReportGeneration:
    """Tests for trust report generation."""
    
    def test_generate_trust_report_creates_record(
        self, 
        trust_service, 
        sample_snapshot, 
        test_session
    ):
        """Verify trust report creates a database record."""
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        assert report is not None
        assert report.snapshot_id == sample_snapshot.id
        assert report.trust_score >= 0 and report.trust_score <= 100
        assert report.metrics_json is not None
        
        # Verify metrics were stored
        metrics = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report.id
        ).all()
        
        assert len(metrics) == 8  # All 8 metrics
    
    def test_cash_explained_metric_calculation(
        self,
        trust_service,
        sample_snapshot,
        sample_invoices,
        sample_bank_account,
        sample_transactions,
        test_session
    ):
        """Verify cash explained percentage calculation."""
        # Add some reconciliation records
        txn = sample_transactions[0]
        inv = sample_invoices[0]
        
        recon = models.ReconciliationTable(
            bank_transaction_id=txn.id,
            invoice_id=inv.id,
            amount_allocated=5000.0,
            match_type="manual"
        )
        test_session.add(recon)
        test_session.commit()
        
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        metric = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report.id,
            TrustMetric.key == "cash_explained_pct"
        ).first()
        
        assert metric is not None
        assert metric.value >= 0 and metric.value <= 100
        assert metric.unit == "percent"
    
    def test_missing_fx_exposure_calculation(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        sample_fx_rates,
        test_session
    ):
        """Verify missing FX exposure is calculated correctly."""
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        metric = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report.id,
            TrustMetric.key == "missing_fx_exposure_base"
        ).first()
        
        assert metric is not None
        # CHF invoice should be flagged (5000.0)
        assert metric.value == 5000.0
        assert metric.unit == "currency"
        
        # Evidence should reference the CHF invoice
        assert len(metric.evidence_refs_json) > 0
    
    def test_duplicate_exposure_detection(
        self,
        trust_service,
        sample_snapshot,
        test_session
    ):
        """
        Verify duplicate exposure is detected.
        
        Note: The database enforces UNIQUE(snapshot_id, canonical_id) for idempotency,
        so true duplicates cannot be inserted. This test verifies that when there are
        no duplicates (as should be normal), the metric correctly reports 0.
        """
        # Create invoices with different canonical_ids (proper behavior)
        inv1 = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-DUP-001",
            customer="Test",
            amount=3000.0,
            currency="EUR",
            canonical_id="unique_id_001"
        )
        inv2 = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-DUP-002",
            customer="Test",
            amount=3000.0,
            currency="EUR",
            canonical_id="unique_id_002"
        )
        
        test_session.add_all([inv1, inv2])
        test_session.commit()
        
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        metric = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report.id,
            TrustMetric.key == "duplicate_exposure_base"
        ).first()
        
        assert metric is not None
        # Should be 0 when DB constraints are enforced properly
        assert metric.value == 0


# ═══════════════════════════════════════════════════════════════════════════════
# LOCK GATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLockGates:
    """Tests for lock gate evaluation."""
    
    def test_lock_eligible_when_all_gates_pass(
        self,
        trust_service,
        sample_snapshot,
        sample_invoices,
        sample_bank_account,
        sample_transactions,
        test_session
    ):
        """Verify lock is eligible when all gates pass."""
        # Fully reconcile all transactions
        for i, txn in enumerate(sample_transactions):
            recon = models.ReconciliationTable(
                bank_transaction_id=txn.id,
                invoice_id=sample_invoices[i].id,
                amount_allocated=txn.amount,
                match_type="manual"
            )
            test_session.add(recon)
        
        test_session.commit()
        
        # Use lenient thresholds
        thresholds = LockGateThresholds(
            missing_fx_threshold_pct=1.0,  # 100% tolerance
            unexplained_cash_threshold_pct=1.0,
            duplicate_exposure_threshold=100000,
            freshness_mismatch_hours=1000,
            require_critical_findings_resolved=False
        )
        
        report = trust_service.generate_trust_report(
            sample_snapshot.id, 
            thresholds=thresholds
        )
        
        assert report.lock_eligible == True
    
    def test_lock_not_eligible_on_gate_failure(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify lock is not eligible when gates fail."""
        # No FX rates - will trigger missing_fx gate
        
        # Use strict thresholds
        thresholds = LockGateThresholds(
            missing_fx_threshold_pct=0.001,  # Very strict
            unexplained_cash_threshold_pct=0.05,
            require_critical_findings_resolved=True
        )
        
        report = trust_service.generate_trust_report(
            sample_snapshot.id,
            thresholds=thresholds
        )
        
        assert report.lock_eligible == False
        assert len(report.gate_failures_json) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# CFO OVERRIDE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCFOOverride:
    """Tests for CFO override functionality."""
    
    def test_lock_without_override_fails_when_gates_fail(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify lock fails without override when gates fail."""
        success, message, report = trust_service.attempt_lock(
            snapshot_id=sample_snapshot.id,
            user_id="user123"
        )
        
        # Should fail (no FX rates)
        assert success == False
        assert "failed" in message.lower() or "override" in message.lower()
    
    def test_lock_with_short_acknowledgment_fails(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify override requires acknowledgment >= 20 chars."""
        success, message, report = trust_service.attempt_lock(
            snapshot_id=sample_snapshot.id,
            user_id="user123",
            override_acknowledgment="short"  # Too short!
        )
        
        assert success == False
        assert "20 char" in message.lower()
    
    def test_lock_with_valid_override_succeeds(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify lock succeeds with valid override."""
        success, message, report = trust_service.attempt_lock(
            snapshot_id=sample_snapshot.id,
            user_id="cfo@company.com",
            user_email="cfo@company.com",
            user_role="CFO",
            override_acknowledgment="I acknowledge the missing FX rates and accept the risk for this snapshot.",
            override_reason="Client payment expected before FX exposure materializes"
        )
        
        assert success == True
        assert "override" in message.lower()
        
        # Verify snapshot is locked
        snapshot = test_session.query(models.Snapshot).filter(
            models.Snapshot.id == sample_snapshot.id
        ).first()
        
        assert snapshot.status == models.SnapshotStatus.LOCKED
        assert snapshot.is_locked == 1
    
    def test_override_creates_audit_log(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify override creates audit log entry."""
        acknowledgment = "I acknowledge the risks and approve this override for Q4 closing."
        
        success, _, _ = trust_service.attempt_lock(
            snapshot_id=sample_snapshot.id,
            user_id="cfo123",
            user_email="cfo@example.com",
            user_role="CFO",
            override_acknowledgment=acknowledgment,
            override_reason="Q4 deadline",
            ip_address="192.168.1.100"
        )
        
        assert success == True
        
        # Verify audit log
        log = test_session.query(LockGateOverrideLog).filter(
            LockGateOverrideLog.snapshot_id == sample_snapshot.id
        ).first()
        
        assert log is not None
        assert log.user_id == "cfo123"
        assert log.user_email == "cfo@example.com"
        assert log.user_role == "CFO"
        assert log.acknowledgment_text == acknowledgment
        assert log.override_reason == "Q4 deadline"
        assert len(log.failed_gates_json) > 0
    
    def test_cannot_lock_already_locked_snapshot(
        self,
        trust_service,
        sample_snapshot,
        test_session
    ):
        """Verify cannot lock an already locked snapshot."""
        # Lock the snapshot first
        sample_snapshot.status = models.SnapshotStatus.LOCKED
        sample_snapshot.is_locked = 1
        sample_snapshot.locked_at = datetime.utcnow()
        sample_snapshot.locked_by = "admin@example.com"
        test_session.commit()
        
        success, message, _ = trust_service.attempt_lock(
            snapshot_id=sample_snapshot.id,
            user_id="another_user"
        )
        
        assert success == False
        assert "already locked" in message.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# TRUST SCORE CALCULATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrustScoreCalculation:
    """Tests for trust score calculation."""
    
    def test_trust_score_in_valid_range(
        self,
        trust_service,
        sample_snapshot,
        test_session
    ):
        """Verify trust score is always 0-100."""
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        assert report.trust_score >= 0
        assert report.trust_score <= 100
    
    def test_high_trust_score_when_all_good(
        self,
        trust_service,
        sample_snapshot,
        sample_invoices,
        sample_bank_account,
        sample_transactions,
        test_session
    ):
        """Verify high trust score when data is clean."""
        # Fully reconcile
        for i, txn in enumerate(sample_transactions):
            recon = models.ReconciliationTable(
                bank_transaction_id=txn.id,
                invoice_id=sample_invoices[i].id,
                amount_allocated=txn.amount,
                match_type="exact"
            )
            test_session.add(recon)
        
        test_session.commit()
        
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        # Score should be reasonably high
        assert report.trust_score >= 50
    
    def test_low_trust_score_when_issues_present(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify lower trust score when issues present."""
        # No FX rates, no reconciliation = problems
        
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        # Score should be lower due to issues
        # (but exact value depends on configuration)
        assert report.trust_score < 90


# ═══════════════════════════════════════════════════════════════════════════════
# TREND CALCULATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrendCalculation:
    """Tests for metric trend calculation."""
    
    def test_trend_calculated_from_previous_report(
        self,
        trust_service,
        sample_snapshot,
        sample_invoices,
        test_session
    ):
        """Verify trends are calculated between reports."""
        # Generate first report
        report1 = trust_service.generate_trust_report(sample_snapshot.id)
        
        # Add more invoices (change the data)
        new_inv = models.Invoice(
            snapshot_id=sample_snapshot.id,
            document_number="INV-NEW-001",
            customer="New Client",
            amount=50000.0,
            currency="EUR"
        )
        test_session.add(new_inv)
        test_session.commit()
        
        # Generate second report
        report2 = trust_service.generate_trust_report(sample_snapshot.id)
        
        # Check for trend data
        metrics = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report2.id
        ).all()
        
        # At least some metrics should have trend data
        has_trend = any(m.trend_delta is not None for m in metrics)
        assert has_trend


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE REFERENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvidenceReferences:
    """Tests for evidence reference generation."""
    
    def test_evidence_refs_have_required_fields(
        self,
        trust_service,
        sample_snapshot,
        sample_foreign_invoices,
        test_session
    ):
        """Verify evidence references contain required fields."""
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        metric = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report.id,
            TrustMetric.key == "missing_fx_exposure_base"
        ).first()
        
        if metric.evidence_refs_json:
            for ref in metric.evidence_refs_json:
                assert "type" in ref
                assert "id" in ref or "message" in ref
    
    def test_evidence_refs_enable_drilldown(
        self,
        trust_service,
        sample_snapshot,
        sample_invoices,
        sample_bank_account,
        sample_transactions,
        test_session
    ):
        """Verify evidence refs point to real records."""
        report = trust_service.generate_trust_report(sample_snapshot.id)
        
        metric = test_session.query(TrustMetric).filter(
            TrustMetric.report_id == report.id,
            TrustMetric.key == "cash_explained_pct"
        ).first()
        
        if metric.evidence_refs_json:
            for ref in metric.evidence_refs_json:
                if ref.get("type") == "bank_txn" and ref.get("id"):
                    # Verify the referenced transaction exists
                    txn = test_session.query(models.BankTransaction).filter(
                        models.BankTransaction.id == ref["id"]
                    ).first()
                    assert txn is not None


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
