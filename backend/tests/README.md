# Gitto Test Suite

Comprehensive test suite covering invariants, property-based testing, metamorphic tests, performance, and differential baselines.

## Test Structure

### 1. Invariant Tests (`test_invariants.py`)
Tests that critical invariants are never violated:
- **Weekly Cash Math**: Forecast totals must sum correctly
- **Snapshot Immutability**: Locked snapshots cannot be modified
- **FX Conversion Safety**: Missing FX rates never silently default to 1.0
- **Reconciliation Conservation**: Allocations must sum to transaction amounts
- **Drilldown Sums**: Invoice IDs in drilldown must match grid cell totals

### 2. Property-Based Tests (`test_property_based.py`)
Uses Hypothesis to generate messy data and verify invariants hold:
- **Messy Invoice Data**: Random amounts, missing due dates, duplicate rows
- **Missing FX Handling**: Ensures missing FX routes to Unknown bucket
- **Messy Bank Data**: Random references, partial payments

### 3. Metamorphic Tests (`test_metamorphic.py`)
Tests that transformations don't change outputs incorrectly:
- **Row Order Invariance**: Shuffling rows produces same forecast
- **Idempotency**: Re-uploading same file is idempotent
- **Scaling Invariance**: Scaling amounts scales totals linearly
- **Noise Invariance**: Harmless noise doesn't break matching

### 4. Performance Tests (`test_performance.py`)
Performance regression tests:
- **Reconciliation Performance**: 50k txns + 200k invoices completes under threshold
- **Index Building**: Fast index construction even with large datasets

### 5. Differential Baseline Tests (`test_differential_baseline.py`)
Compare Gitto against simple baseline models:
- **Baseline Comparison**: Gitto matches or improves upon due-date model
- **Impossible Timing**: Never predicts payment before invoice date
- **Constant Behavior**: Handles constant payment behavior correctly

## Running Tests

### Install Dependencies
```bash
pip install -r requirements-test.txt
```

### Run All Tests
```bash
pytest backend/tests/ -v
```

### Run Specific Test Suites
```bash
# Invariant tests only
pytest backend/tests/test_invariants.py -v

# Property-based tests
pytest backend/tests/test_property_based.py -v

# Metamorphic tests
pytest backend/tests/test_metamorphic.py -v

# Performance tests (may take longer)
pytest backend/tests/test_performance.py -v -m performance

# Differential baseline tests
pytest backend/tests/test_differential_baseline.py -v
```

### Skip Performance Tests
```bash
pytest backend/tests/ -v -m "not performance"
```

## Test Markers

- `@pytest.mark.performance`: Performance regression tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.invariant`: Invariant tests

## Expected Results

All tests should pass. If any fail, it indicates:
1. **Invariant violation**: Critical business rule broken
2. **Performance regression**: System slowed down
3. **Data corruption**: Outputs don't match inputs
4. **Logic error**: Algorithm producing incorrect results

## Continuous Integration

These tests should be run:
- Before every commit
- In CI/CD pipeline
- Before production deployments
- After major refactoring







