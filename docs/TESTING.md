# Testing Guide

## Test Structure

```
backend/tests/
├── test_reconciliation_conservation_hard.py    # Conservation proofs
├── test_forecast_calibration_hard.py          # Calibration tests
├── test_snapshot_immutability_comprehensive.py # Immutability tests
├── test_metamorphic.py                        # Metamorphic tests
└── ...

fixtures/
├── test_bank_format_roundtrip.py              # Format validation
└── test_golden_manifest_assertions.py         # Golden dataset tests
```

## Running Tests

### All Tests
```bash
pytest backend/tests/ -v
```

### Specific Test Suites
```bash
# Conservation proofs
pytest backend/tests/test_reconciliation_conservation_hard.py -v

# Calibration
pytest backend/tests/test_forecast_calibration_hard.py -v

# Immutability
pytest backend/tests/test_snapshot_immutability_comprehensive.py -v

# Metamorphic
pytest backend/tests/test_metamorphic.py -v

# Round-trip validation
pytest fixtures/test_bank_format_roundtrip.py -v
```

## Test Types

### 1. Proof Tests

Tests that verify mathematical invariants and will fail when broken.

**Example**: Conservation proof
```python
def test_conservation_txn_amount_exceeds_total_open():
    # Txn > total open → remainder as unallocated, not "create money"
    proof = solver.verify_conservation(solution, txn_amount)
    assert proof["is_conserved"]
```

### 2. Metamorphic Tests

Tests that verify deterministic behavior under transformations.

**Example**: Shuffle row order
```python
def test_shuffle_row_order_outputs_identical():
    # Shuffle → outputs identical
    solution1 = solver.solve(txn_amount, candidates_original)
    solution2 = solver.solve(txn_amount, candidates_shuffled)
    assert solution1.allocations == solution2.allocations
```

### 3. Round-Trip Tests

Tests that verify format validation and parsing.

**Example**: MT940 round-trip
```python
def test_mt940_roundtrip():
    # generate → validate → parse → compare to ground truth
    statements, ground_truth = generator.generate_bank_statements_with_ground_truth(...)
    valid, errors = MT940Validator.validate_statement(statements["mt940"])
    assert valid
```

## Test Coverage

Current coverage includes:
- ✅ Conservation proofs
- ✅ No-overmatch invariants
- ✅ Calibration (amount-weighted)
- ✅ Monotonic quantiles
- ✅ Regime shift detection
- ✅ Database immutability
- ✅ Format validation
- ✅ Metamorphic properties

## Writing New Tests

### Test Naming Convention
- `test_<feature>_<scenario>()`: Descriptive test names
- Use docstrings to explain what is being tested

### Example Test Structure
```python
def test_feature_scenario():
    """
    Hard check: Description of what this test verifies.
    """
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = service.method(setup_data)
    
    # Assert
    assert result.property == expected_value
    assert invariant_holds(result)
```

## Continuous Integration

Tests should be run in CI/CD pipeline:
- On every pull request
- Before merging to main
- On scheduled basis (nightly)

## Test Data

Use `fixtures/generate_synthetic_data_enhanced.py` to generate test data:
```bash
python fixtures/generate_synthetic_data_enhanced.py
```

This generates:
- AR invoices
- AP vendor bills
- Bank transactions (CSV, MT940, BAI2, camt.053)
- FX rates
- Intercompany transfers

## Golden Dataset

The `fixtures/golden_dataset_manifest.json` contains known numeric results for regression testing.

Run golden dataset tests:
```bash
pytest fixtures/test_golden_manifest_assertions.py -v
```
