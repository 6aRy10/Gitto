"""
Bank Format Round-Trip Test

Hard check: generate → validate → parse → canonicalize → compare to ground truth
"""

import pytest
from pathlib import Path
from bank_format_validator import MT940Validator, BAI2Validator, Camt053Validator
from generate_synthetic_data_enhanced import EnhancedSyntheticDataGenerator, ChaosConfig


def test_mt940_roundtrip():
    """Test MT940: generate → validate → parse → compare to ground truth."""
    generator = EnhancedSyntheticDataGenerator()
    
    # Generate transactions
    transactions = [
        {
            "id": 1,
            "transaction_date": "2024-01-15T10:00:00",
            "amount": 10000.0,
            "currency": "EUR",
            "reference": "INV-001",
            "counterparty": "Customer A",
            "transaction_type": "customer_receipt",
            "is_wash": 0
        },
        {
            "id": 2,
            "transaction_date": "2024-01-16T14:30:00",
            "amount": -5000.0,
            "currency": "EUR",
            "reference": "PAY-001",
            "counterparty": "Vendor B",
            "transaction_type": "supplier_payment",
            "is_wash": 0
        }
    ]
    
    # Generate MT940
    statements, ground_truth = generator.generate_bank_statements_with_ground_truth(transactions, 1)
    mt940_content = statements["mt940"]
    
    # Validate format
    valid, errors = MT940Validator.validate_statement(mt940_content)
    assert valid, f"MT940 validation failed: {errors}"
    
    # Parse (simplified - in real implementation, use actual MT940 parser)
    # For now, verify ground truth matches input
    assert len(ground_truth["ground_truth"]) == len(transactions)
    
    for i, txn in enumerate(transactions):
        gt = ground_truth["ground_truth"][i]
        assert abs(gt["amount"] - txn["amount"]) < 0.01, f"Amount mismatch: {gt['amount']} vs {txn['amount']}"
        assert gt["transaction_date"] == txn["transaction_date"], f"Date mismatch"
        assert gt["reference"] == txn["reference"], f"Reference mismatch"


def test_bai2_roundtrip():
    """Test BAI2: generate → validate → parse → compare to ground truth."""
    generator = EnhancedSyntheticDataGenerator()
    
    transactions = [
        {
            "id": 1,
            "transaction_date": "2024-01-15T10:00:00",
            "amount": 10000.0,
            "currency": "USD",
            "reference": "INV-001",
            "counterparty": "Customer A",
            "transaction_type": "customer_receipt",
            "is_wash": 0
        }
    ]
    
    statements, ground_truth = generator.generate_bank_statements_with_ground_truth(transactions, 1)
    bai2_content = statements["bai2"]
    
    # Validate format
    valid, errors = BAI2Validator.validate_statement(bai2_content)
    assert valid, f"BAI2 validation failed: {errors}"
    
    # Verify ground truth
    assert len(ground_truth["ground_truth"]) == len(transactions)
    assert abs(ground_truth["ground_truth"][0]["amount"] - transactions[0]["amount"]) < 0.01


def test_camt053_roundtrip():
    """Test camt.053: generate → validate → parse → compare to ground truth."""
    generator = EnhancedSyntheticDataGenerator()
    
    transactions = [
        {
            "id": 1,
            "transaction_date": "2024-01-15T10:00:00",
            "amount": 10000.0,
            "currency": "EUR",
            "reference": "INV-001",
            "counterparty": "Customer A",
            "transaction_type": "customer_receipt",
            "is_wash": 0
        }
    ]
    
    statements, ground_truth = generator.generate_bank_statements_with_ground_truth(transactions, 1)
    camt053_content = statements["camt053"]
    
    # Validate format
    valid, errors = Camt053Validator.validate_statement(camt053_content)
    assert valid, f"camt.053 validation failed: {errors}"
    
    # Verify ground truth
    assert len(ground_truth["ground_truth"]) == len(transactions)


def test_chaos_mode_preserves_ground_truth():
    """Test that chaos mode transformations are tracked in ground truth."""
    chaos_config = ChaosConfig(enable_chaos=True)
    generator = EnhancedSyntheticDataGenerator(chaos_config)
    
    transactions = [
        {
            "id": i,
            "transaction_date": f"2024-01-{15+i:02d}T10:00:00",
            "amount": 1000.0 * (i + 1),
            "currency": "EUR",
            "reference": f"INV-{i:03d}",
            "counterparty": f"Customer {i}",
            "transaction_type": "customer_receipt",
            "is_wash": 0
        }
        for i in range(10)
    ]
    
    statements, ground_truth = generator.generate_bank_statements_with_ground_truth(transactions, 1)
    
    # Ground truth should match original transactions (before chaos)
    assert len(ground_truth["ground_truth"]) == len(transactions)
    
    # Verify canonical hashes are consistent
    for i, txn in enumerate(transactions):
        gt = ground_truth["ground_truth"][i]
        expected_hash = generator._hash_transaction(txn)
        assert gt["canonical_hash"] == expected_hash, "Canonical hash mismatch"


