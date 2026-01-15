"""
Golden Test Fixtures for Health Report

Verifies that health reports produce exact expected metrics
for known datasets.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lineage_models import Base as LineageBase, LineageDataset, CanonicalRecord, generate_dataset_id
from health_report_models import Base as HealthBase, DataHealthReportRecord, HealthFinding
from health_report_service import HealthReportService


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN DATASET DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

# This golden dataset has known characteristics that produce exact metrics
GOLDEN_DATASET = {
    "name": "Golden Test Dataset",
    "description": "Dataset with known health metrics for testing",
    "records": [
        # 5 perfect invoices
        {"type": "Invoice", "amount": 1000.0, "currency": "EUR", "due_date": "2026-02-15", "counterparty": "Customer A", "doc_num": "INV001"},
        {"type": "Invoice", "amount": 2000.0, "currency": "EUR", "due_date": "2026-02-20", "counterparty": "Customer B", "doc_num": "INV002"},
        {"type": "Invoice", "amount": 3000.0, "currency": "EUR", "due_date": "2026-02-25", "counterparty": "Customer C", "doc_num": "INV003"},
        {"type": "Invoice", "amount": 4000.0, "currency": "EUR", "due_date": "2026-03-01", "counterparty": "Customer D", "doc_num": "INV004"},
        {"type": "Invoice", "amount": 5000.0, "currency": "EUR", "due_date": "2026-03-05", "counterparty": "Customer E", "doc_num": "INV005"},
        
        # 2 invoices missing due dates (exposure: 1500 + 2500 = 4000)
        {"type": "Invoice", "amount": 1500.0, "currency": "EUR", "due_date": None, "counterparty": "Customer F", "doc_num": "INV006"},
        {"type": "Invoice", "amount": 2500.0, "currency": "EUR", "due_date": None, "counterparty": "Customer G", "doc_num": "INV007"},
        
        # 3 invoices with foreign currency (exposure: 500 + 1000 + 1500 = 3000)
        {"type": "Invoice", "amount": 500.0, "currency": "USD", "due_date": "2026-02-28", "counterparty": "US Customer", "doc_num": "INV008"},
        {"type": "Invoice", "amount": 1000.0, "currency": "GBP", "due_date": "2026-02-28", "counterparty": "UK Customer", "doc_num": "INV009"},
        {"type": "Invoice", "amount": 1500.0, "currency": "CHF", "due_date": "2026-02-28", "counterparty": "CH Customer", "doc_num": "INV010"},
        
        # 1 invoice missing currency
        {"type": "Invoice", "amount": 750.0, "currency": None, "due_date": "2026-02-28", "counterparty": "Unknown Curr", "doc_num": "INV011"},
        
        # 2 negative amounts (credit notes)
        {"type": "Invoice", "amount": -200.0, "currency": "EUR", "due_date": "2026-02-15", "counterparty": "Customer A", "doc_num": "CN001"},
        {"type": "Invoice", "amount": -300.0, "currency": "EUR", "due_date": "2026-02-20", "counterparty": "Customer B", "doc_num": "CN002"},
        
        # 1 outlier amount (much larger than others)
        {"type": "Invoice", "amount": 100000.0, "currency": "EUR", "due_date": "2026-03-15", "counterparty": "Big Customer", "doc_num": "INV012"},
        
        # 2 vendor bills
        {"type": "VendorBill", "amount": 800.0, "currency": "EUR", "due_date": "2026-02-10", "counterparty": "Vendor X", "doc_num": "BILL001"},
        {"type": "VendorBill", "amount": 1200.0, "currency": "EUR", "due_date": None, "counterparty": "Vendor Y", "doc_num": "BILL002"},
        
        # 2 bank transactions
        {"type": "BankTxn", "amount": 5000.0, "currency": "EUR", "due_date": None, "counterparty": "Transfer In", "doc_num": "TXN001"},
        {"type": "BankTxn", "amount": -3000.0, "currency": "EUR", "due_date": None, "counterparty": "Payment Out", "doc_num": "TXN002"},
    ],
    # Expected metrics (exact values)
    "expected_metrics": {
        "total_rows": 19,
        "total_amount": 129750.0,  # Sum of abs(all amounts)
        
        # Missing due dates (AR/AP only, excluding bank txns which don't have due dates)
        # INV006, INV007, BILL002 = 3 records with exposure 1500 + 2500 + 1200 = 5200
        "missing_due_date_count": 3,
        "missing_due_date_exposure": 5200.0,
        
        # Missing/invalid currency: INV011 = 1 record, exposure 750
        "missing_currency_count": 1,
        "missing_currency_exposure": 750.0,
        
        # Foreign currency (missing FX): INV008, INV009, INV010 = 3 records, exposure 3000
        "foreign_currency_count": 3,
        "foreign_currency_exposure": 3000.0,
        
        # Negative amounts: CN001, CN002, TXN002 = 3 records, exposure 200 + 300 + 3000 = 3500
        "negative_amount_count": 3,
        "negative_amount_exposure": 3500.0,
        
        # Outliers: INV012 (100000) is clearly an outlier
        "outlier_count_min": 1,  # At least 1 outlier
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    LineageBase.metadata.create_all(engine)
    HealthBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def golden_dataset(db_session):
    """Create the golden dataset."""
    # Create dataset
    dataset = LineageDataset(
        dataset_id=generate_dataset_id(),
        entity_id=1,
        source_type="test_golden",
        source_summary_json={"name": GOLDEN_DATASET["name"]},
        schema_fingerprint="golden_test_fingerprint",
        row_count=len(GOLDEN_DATASET["records"])
    )
    db_session.add(dataset)
    db_session.flush()
    
    # Create canonical records
    for idx, rec in enumerate(GOLDEN_DATASET["records"]):
        # Generate canonical ID
        import hashlib
        canonical_id = hashlib.sha256(
            f"{rec['type']}|{rec['doc_num']}|{rec['amount']}".encode()
        ).hexdigest()
        
        # Parse due date
        due_date = None
        if rec["due_date"]:
            due_date = datetime.strptime(rec["due_date"], "%Y-%m-%d").date()
        
        canonical = CanonicalRecord(
            dataset_id=dataset.id,
            record_type=rec["type"],
            canonical_id=canonical_id,
            payload_json=rec,
            amount=rec["amount"],
            currency=rec["currency"],
            record_date=date(2026, 1, 15),  # Fixed date for all
            due_date=due_date,
            counterparty=rec["counterparty"],
            external_id=rec["doc_num"]
        )
        db_session.add(canonical)
    
    db_session.commit()
    db_session.refresh(dataset)
    return dataset


# ═══════════════════════════════════════════════════════════════════════════════
# GOLDEN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoldenHealthReport:
    """Golden tests that verify exact expected metrics."""
    
    def test_total_rows(self, db_session, golden_dataset):
        """Verify total row count matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        summary = report.summary_json
        expected = GOLDEN_DATASET["expected_metrics"]["total_rows"]
        
        assert summary["total_rows"] == expected, \
            f"Total rows: expected {expected}, got {summary['total_rows']}"
    
    def test_missing_due_date_count(self, db_session, golden_dataset):
        """Verify missing due date count matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        # Find the missing_due_date finding
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_due_date"),
            None
        )
        
        expected_count = GOLDEN_DATASET["expected_metrics"]["missing_due_date_count"]
        
        assert finding is not None, "Missing due date finding not found"
        assert finding.count_rows == expected_count, \
            f"Missing due date count: expected {expected_count}, got {finding.count_rows}"
    
    def test_missing_due_date_exposure(self, db_session, golden_dataset):
        """Verify missing due date exposure matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_due_date"),
            None
        )
        
        expected_exposure = GOLDEN_DATASET["expected_metrics"]["missing_due_date_exposure"]
        
        assert finding is not None, "Missing due date finding not found"
        assert abs(finding.exposure_amount_base - expected_exposure) < 0.01, \
            f"Missing due date exposure: expected {expected_exposure}, got {finding.exposure_amount_base}"
    
    def test_missing_currency_count(self, db_session, golden_dataset):
        """Verify missing currency count matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_invalid_currency"),
            None
        )
        
        expected_count = GOLDEN_DATASET["expected_metrics"]["missing_currency_count"]
        
        assert finding is not None, "Missing currency finding not found"
        assert finding.count_rows == expected_count, \
            f"Missing currency count: expected {expected_count}, got {finding.count_rows}"
    
    def test_missing_currency_exposure(self, db_session, golden_dataset):
        """Verify missing currency exposure matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_invalid_currency"),
            None
        )
        
        expected_exposure = GOLDEN_DATASET["expected_metrics"]["missing_currency_exposure"]
        
        assert finding is not None, "Missing currency finding not found"
        assert abs(finding.exposure_amount_base - expected_exposure) < 0.01, \
            f"Missing currency exposure: expected {expected_exposure}, got {finding.exposure_amount_base}"
    
    def test_foreign_currency_count(self, db_session, golden_dataset):
        """Verify foreign currency count matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_fx_rate"),
            None
        )
        
        expected_count = GOLDEN_DATASET["expected_metrics"]["foreign_currency_count"]
        
        assert finding is not None, "Missing FX rate finding not found"
        assert finding.count_rows == expected_count, \
            f"Foreign currency count: expected {expected_count}, got {finding.count_rows}"
    
    def test_foreign_currency_exposure(self, db_session, golden_dataset):
        """Verify foreign currency exposure matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_fx_rate"),
            None
        )
        
        expected_exposure = GOLDEN_DATASET["expected_metrics"]["foreign_currency_exposure"]
        
        assert finding is not None, "Missing FX rate finding not found"
        assert abs(finding.exposure_amount_base - expected_exposure) < 0.01, \
            f"Foreign currency exposure: expected {expected_exposure}, got {finding.exposure_amount_base}"
    
    def test_negative_amount_count(self, db_session, golden_dataset):
        """Verify negative amount count matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "negative_amounts"),
            None
        )
        
        expected_count = GOLDEN_DATASET["expected_metrics"]["negative_amount_count"]
        
        assert finding is not None, "Negative amounts finding not found"
        assert finding.count_rows == expected_count, \
            f"Negative amount count: expected {expected_count}, got {finding.count_rows}"
    
    def test_negative_amount_exposure(self, db_session, golden_dataset):
        """Verify negative amount exposure matches expected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "negative_amounts"),
            None
        )
        
        expected_exposure = GOLDEN_DATASET["expected_metrics"]["negative_amount_exposure"]
        
        assert finding is not None, "Negative amounts finding not found"
        assert abs(finding.exposure_amount_base - expected_exposure) < 0.01, \
            f"Negative amount exposure: expected {expected_exposure}, got {finding.exposure_amount_base}"
    
    def test_outlier_detection(self, db_session, golden_dataset):
        """Verify outliers are detected."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        finding = next(
            (f for f in report.findings if f.metric_key == "outlier_amount"),
            None
        )
        
        expected_min = GOLDEN_DATASET["expected_metrics"]["outlier_count_min"]
        
        assert finding is not None, "Outlier finding not found"
        assert finding.count_rows >= expected_min, \
            f"Outlier count: expected at least {expected_min}, got {finding.count_rows}"
        
        # The 100000 invoice should be in outliers
        evidence = finding.sample_evidence_json or []
        outlier_amounts = [e.get("amount") for e in evidence]
        assert 100000.0 in outlier_amounts, \
            f"100000 outlier not detected. Found: {outlier_amounts}"
    
    def test_severity_score_reasonable(self, db_session, golden_dataset):
        """Verify severity score is within reasonable range."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        # With the issues in our golden dataset, severity should be > 0
        assert report.severity_score > 0, "Severity score should be > 0 with issues present"
        # But not maximum (100) since issues are not catastrophic
        assert report.severity_score < 100, "Severity score should be < 100"
    
    def test_quality_level_appropriate(self, db_session, golden_dataset):
        """Verify quality level is appropriate for dataset."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        summary = report.summary_json
        quality = summary.get("quality_level")
        
        # With warnings but no critical issues, quality should be fair or good
        assert quality in ["fair", "good", "poor"], \
            f"Quality level should be fair/good/poor, got {quality}"
    
    def test_findings_have_evidence(self, db_session, golden_dataset):
        """Verify all findings have sample evidence."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        for finding in report.findings:
            if finding.count_rows > 0:
                assert finding.sample_evidence_json, \
                    f"Finding {finding.metric_key} has {finding.count_rows} rows but no evidence"
    
    def test_report_is_idempotent(self, db_session, golden_dataset):
        """Verify generating report twice produces same metrics."""
        service = HealthReportService(db_session)
        
        report1 = service.generate_report(golden_dataset.id)
        report2 = service.generate_report(golden_dataset.id)
        
        # Summaries should match
        assert report1.summary_json["total_rows"] == report2.summary_json["total_rows"]
        assert report1.summary_json["total_amount"] == report2.summary_json["total_amount"]
        
        # Finding counts should match
        assert len(report1.findings) == len(report2.findings)
        
        # Exposures should match
        for f1, f2 in zip(
            sorted(report1.findings, key=lambda f: f.metric_key),
            sorted(report2.findings, key=lambda f: f.metric_key)
        ):
            assert f1.metric_key == f2.metric_key
            assert f1.count_rows == f2.count_rows
            assert abs(f1.exposure_amount_base - f2.exposure_amount_base) < 0.01


class TestGoldenHealthReportAmountWeighting:
    """Tests that verify amount-weighted calculations."""
    
    def test_exposure_is_amount_weighted(self, db_session, golden_dataset):
        """Verify exposures are calculated from amounts, not row counts."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        # Missing due date exposure should be sum of amounts, not count
        finding = next(
            (f for f in report.findings if f.metric_key == "missing_due_date"),
            None
        )
        
        # 3 records but exposure is 5200, not 3
        assert finding.exposure_amount_base == 5200.0
        assert finding.count_rows == 3
        
        # Exposure != count (proving it's amount-weighted)
        assert finding.exposure_amount_base != finding.count_rows
    
    def test_total_amount_is_absolute_sum(self, db_session, golden_dataset):
        """Verify total amount uses absolute values."""
        service = HealthReportService(db_session)
        report = service.generate_report(golden_dataset.id)
        
        summary = report.summary_json
        
        # Total should be sum of abs(amounts), not algebraic sum
        # We have negatives (-200, -300, -3000) that should be counted as positive
        expected_total = GOLDEN_DATASET["expected_metrics"]["total_amount"]
        
        assert abs(summary["total_amount"] - expected_total) < 1.0, \
            f"Total amount: expected {expected_total}, got {summary['total_amount']}"


# ═══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
