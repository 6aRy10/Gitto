# Safe Test Running Guide

## Problem
Running full test suites can crash the app and platform. This guide provides safer alternatives.

## Solution: Use Safe Test Runners

### 1. Validate Tests First (No Execution)
```bash
python scripts/validate_tests_safe.py
```
This checks for import errors and syntax issues **without running tests**.

### 2. Run Single Test at a Time
```bash
# Run one test file
python scripts/run_single_test_safe.py backend/tests/test_cfo_trust_killers.py

# Run one specific test
python scripts/run_single_test_safe.py backend/tests/test_cfo_trust_killers.py test_1_cell_sum_truth
```

### 3. Manual Test Validation (Safest)
Instead of running pytest directly, you can:

1. **Check imports manually:**
   ```python
   python -c "from backend.tests.test_cfo_trust_killers import TestCFOTrustKillers; print('OK')"
   ```

2. **Run with timeout:**
   ```bash
   timeout 30 python -m pytest backend/tests/test_cfo_trust_killers.py::TestCFOTrustKillers::test_1_cell_sum_truth -v
   ```

3. **Run with limited output:**
   ```bash
   python -m pytest backend/tests/test_cfo_trust_killers.py -v --tb=line -q
   ```

## Recommended Approach

1. **First**: Validate all test files
   ```bash
   python scripts/validate_tests_safe.py
   ```

2. **Then**: Run tests one at a time
   ```bash
   python scripts/run_single_test_safe.py backend/tests/test_cfo_trust_killers.py test_1_cell_sum_truth
   python scripts/run_single_test_safe.py backend/tests/test_cfo_trust_killers.py test_2_snapshot_immutability
   # etc.
   ```

3. **If crashes persist**: Check for:
   - Database connection issues
   - Circular imports
   - Missing dependencies
   - Memory leaks in test fixtures

## Alternative: API-Based Testing

Instead of running pytest, use the API-based gauntlet runner:

```bash
# Start the API server first
cd backend
python -m uvicorn main:app --reload

# Then in another terminal
python scripts/gauntlet.py --snapshot-id 1 --entity-id 1
```

This tests the actual API endpoints without running pytest, which is safer.

## Troubleshooting

If tests still crash:

1. **Check database**: Ensure test database is separate from production
2. **Check memory**: Large test datasets can cause OOM
3. **Check imports**: Use `validate_tests_safe.py` first
4. **Check fixtures**: Test fixtures might be creating too much data
5. **Use smaller datasets**: Reduce test data size in fixtures




