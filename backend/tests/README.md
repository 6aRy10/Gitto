# Gitto CI Trust Gauntlet Test Suite

Comprehensive test suite for validating the Gitto Trust Certification system.

## Test Categories

### Markers

| Marker | Description | Run Command |
|--------|-------------|-------------|
| `unit` | Fast unit tests (~1s each) | `pytest -m unit` |
| `property` | Property-based tests (Hypothesis) | `pytest -m property` |
| `metamorphic` | Metamorphic relation tests | `pytest -m metamorphic` |
| `golden` | Golden dataset regression tests | `pytest -m golden` |
| `roundtrip` | Round-trip format validation | `pytest -m roundtrip` |
| `integration` | Full stack integration tests | `pytest -m integration` |
| `slow` | Performance tests (excluded by default) | `pytest -m slow --run-slow` |
| `mutation` | Mutation testing harness | `pytest -m mutation` |

## Running Tests

### Quick Test (unit tests only)
```bash
pytest -m unit
```

### Full Test Suite (excluding slow)
```bash
pytest
```

### Full Test Suite (including slow)
```bash
pytest --run-slow
```

### CI Pipeline Recommended
```bash
pytest -m "not slow" --junitxml=test-results.xml
```

### Performance Tests
```bash
pytest -m slow --run-slow --perf-threshold=30
```

## Test Files

### `test_ci_trust_gauntlet.py`
The main CI Trust Gauntlet test suite containing:

1. **Golden Dataset Tests** (`TestGoldenDatasetIngestion`, `TestGoldenTrustReport`, `TestGoldenInvariants`)
   - Validate ingestion produces expected counts
   - Trust report metrics match manifest ranges
   - All 7 invariants pass for golden data

2. **Round-Trip Bank Format Tests** (`TestBankFormatRoundTrip`)
   - MT940 → validate → parse → canonicalize → verify
   - BAI2 → validate → parse → canonicalize → verify
   - camt.053 → validate → parse → canonicalize → verify
   - Canonical ID determinism across re-parsing

3. **Regression Tests** (`TestRegressionMutation`)
   - €1 amount mutation detection
   - Duplicate import detection
   - FX rate removal exposure increase

4. **Performance Tests** (`TestPerformanceBlocking`)
   - O(n*k) blocking verification (50k txns + 200k invoices)
   - Trust report generation under threshold
   - Invariant run under threshold

5. **Mutation Test Harness** (`TestMutationHarness`)
   - FX fallback 1.0 mutation caught by fx_safety
   - Immutability bypass mutation caught
   - Over-allocation caught by no_overmatch

6. **Metamorphic Tests** (`TestMetamorphicRelations`)
   - Shuffle preserves totals
   - Scale amounts scales exposure
   - Noise to refs doesn't alter deterministic matches

## Fixtures

### `fixtures/golden_manifest.json`
Expected results for golden dataset assertions:
- Invoice counts and amounts by currency
- Transaction inflows/outflows
- Reconciliation match rates
- Trust report metric ranges
- Invariant expected statuses
- Performance thresholds

### Key Fixtures in `conftest.py`
- `db_session` - Fresh in-memory DB for each test
- `full_db_session` - DB with all models (lineage, trust, invariants)
- `golden_manifest` - Loaded manifest JSON
- `golden_entity`, `golden_snapshot`, `golden_bank_account` - Golden test data
- `golden_dataset` - Full dataset with invoices, transactions, reconciliations, FX rates

## Performance Thresholds

| Test | Threshold | Data Size |
|------|-----------|-----------|
| Reconciliation candidate generation | 30s | 50k txns + 200k invoices |
| Trust report generation | 5s | Golden dataset |
| Invariant run | 10s | Golden dataset |

## Adding New Tests

### 1. Golden Dataset Test
```python
@pytest.mark.golden
def test_new_golden_check(self, golden_dataset, golden_manifest, full_db_session):
    expected = golden_manifest["new_section"]["expected_value"]
    actual = # compute from golden_dataset
    assert actual == expected
```

### 2. Regression Test
```python
@pytest.mark.unit
def test_mutation_detected(self, golden_dataset, golden_snapshot, full_db_session):
    # Save original state
    original = object.value
    
    # Apply mutation
    object.value = mutated_value
    full_db_session.commit()
    
    # Run check that should fail
    result = run_invariant_or_metric()
    
    # Restore
    object.value = original
    full_db_session.commit()
    
    assert result.status == "fail"
```

### 3. Performance Test
```python
@pytest.mark.slow
def test_performance_check(self, full_db_session, perf_threshold):
    start = time.time()
    
    # Do expensive operation
    
    elapsed = time.time() - start
    assert elapsed < perf_threshold
```

## CI Integration

### GitHub Actions
```yaml
- name: Run Tests
  run: |
    cd backend
    pip install -r requirements.txt
    pytest -m "not slow" --junitxml=test-results.xml

- name: Run Performance Tests
  if: github.event_name == 'schedule'
  run: |
    pytest -m slow --run-slow --perf-threshold=60
```

### Pre-commit Hook
```bash
#!/bin/bash
cd backend
pytest -m "unit or golden" --tb=short -q
```

## Troubleshooting

### Import Errors
If tests skip due to missing imports:
```bash
cd backend
pip install -e .
```

### Slow Test Timeout
Increase timeout in `pytest.ini`:
```ini
timeout = 600
```

### Performance Test Failures
Adjust threshold:
```bash
pytest -m slow --run-slow --perf-threshold=60
```
