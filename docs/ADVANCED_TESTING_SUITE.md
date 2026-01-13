# Advanced Testing Suite - OpenAI Engineer Requirements

This document describes the comprehensive testing suite that addresses the requirements specified by an OpenAI engineer. **Failure in these tests means the product is still not ready.**

## Test Categories

### 1. State-Machine Testing (Workflow, Not Functions)

**File**: `backend/tests/test_state_machine_workflow.py`

Instead of isolated tests, these model the actual finance workflow as a sequence:
- `upload → forecast → reconcile → lock snapshot → upload again → compare → apply lever → lock again`

**Key Tests**:
- `test_complete_workflow_with_invariants`: Tests the full workflow with invariant checks after each step
- `test_workflow_reconciliation_preserves_historical_totals`: Critical invariant - reconciliation should not change historical forecast totals

**What It Catches**:
- "Locking doesn't really freeze" bugs
- "Reconciliation changes historical totals" bugs
- Workflow-level issues that unit tests miss

### 2. Mutation Testing (Are Your Tests Actually Strong?)

**File**: `backend/tests/test_mutation_testing.py`

Intentionally introduces tiny code changes and verifies tests fail:
- Flip a sign in `convert_currency`
- Widen tolerance in reconciliation
- Change FX fallback from error to 1.0

**Setup**: Uses `mutmut` (install with `pip install mutmut`)

**Run**: `mutmut run --paths-to-mutate=backend/utils.py backend/bank_service.py`

**What It Detects**: "We have tests but not trust" - tests that don't actually protect you

### 3. Contract Tests (API Truth vs UI Truth)

**File**: `backend/tests/test_contract_api_consistency.py`

Verifies that:
- The grid number returned by `/workspace-13w` equals the sum of items returned by `/workspace-13w/drilldown`
- The UI renders the same totals as the backend

**Key Tests**:
- `test_workspace_grid_equals_drilldown_sum`: Grid totals = drilldown sums
- `test_week_drilldown_invoice_ids_sum_to_grid_cell`: **Critical CFO trust test** - "Can I click Week 4 cash-in and see invoice IDs that sum exactly?"

**What It Prevents**: "Backend says X, UI shows Y" drift

### 4. Precision/Recall Metrics for Reconciliation

**File**: `backend/tests/test_precision_recall_reconciliation.py`

Not just "it matches" - measures actual accuracy:
- Deterministic match precision ≈ 100%
- Rules match precision (should still be very high)
- Suggested match acceptance rate + false positives

**Key Tests**:
- `test_deterministic_match_precision`: Measures precision of Tier 1 matching
- `test_rules_match_precision`: Measures precision of Tier 2 matching
- `test_suggested_match_acceptance_rate`: Verifies suggested matches aren't auto-reconciled

**What It Provides**: Real metrics on reconciliation accuracy, not just "it works"

### 5. Backtesting + Calibration Checks

**File**: `backend/tests/test_backtesting_calibration.py`

Proves probabilistic forecasts aren't theater:
- Does actual cash land between P25–P75 about ~50% of the time?
- Is the forecast systematically optimistic?

**Key Tests**:
- `test_p25_p75_calibration`: Verifies ~50% of payments fall in P25-P75 range
- `test_forecast_not_systematically_optimistic`: Checks for systematic bias
- `test_p50_exists_and_is_reasonable`: Verifies P50 is actually meaningful

**What It Proves**: Forecasts are well-calibrated, not just "P50 exists"

### 6. Chaos / Failure Injection

**File**: `backend/tests/test_chaos_failure_injection.py`

Simulates real-world breaks:
- Bank feed missing a day
- Duplicate statement imports
- Partial upload failures
- FX table missing for one currency

**Key Tests**:
- `test_missing_bank_feed_day`: Detects stale data and warns
- `test_fx_table_missing_for_one_currency`: Fails loudly, routes to Unknown bucket
- `test_system_fails_loudly_not_silently`: Critical - system should warn, not guess

**What It Confirms**: System fails loudly with "Unknown bucket / stale data" warnings instead of making stuff up

### 7. DB-Level Guarantees (Not Just Code Promises)

**File**: `backend/tests/test_db_constraints.py`
**Migration**: `backend/migrations/add_db_constraints.py`

Finance systems should not rely on "developer discipline":
- `UNIQUE(snapshot_id, canonical_id)` - enforced at DB level
- "Locked snapshot cannot be updated" - enforced at DB layer
- Referential integrity for match allocations
- Allocation amounts cannot exceed transaction amount

**Key Tests**:
- `test_unique_snapshot_canonical_id_constraint`: DB enforces uniqueness
- `test_allocation_amount_constraint`: Trigger prevents over-allocation
- `test_invoice_amount_positive_constraint`: Trigger prevents negative amounts

**What It Guarantees**: Data integrity at the database level, not just application code

## Running the Tests

### Run All Advanced Tests
```bash
cd backend
pytest tests/test_state_machine_workflow.py tests/test_contract_api_consistency.py tests/test_precision_recall_reconciliation.py tests/test_backtesting_calibration.py tests/test_chaos_failure_injection.py tests/test_db_constraints.py -v
```

### Run Mutation Testing
```bash
pip install mutmut
mutmut run --paths-to-mutate=backend/utils.py backend/bank_service.py
mutmut results
```

### Run Specific Test Category
```bash
# State machine tests
pytest tests/test_state_machine_workflow.py -v

# Contract tests
pytest tests/test_contract_api_consistency.py -v

# Precision/recall
pytest tests/test_precision_recall_reconciliation.py -v
```

## Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| State-Machine Workflow | 2 | ✅ Implemented |
| Mutation Testing | 1 | ✅ Framework ready |
| Contract Tests | 3 | ✅ Implemented |
| Precision/Recall | 3 | ✅ Implemented |
| Backtesting/Calibration | 3 | ✅ Implemented |
| Chaos/Failure Injection | 6 | ✅ Implemented |
| DB Constraints | 6 | ✅ Implemented |

**Total**: 24 advanced tests covering all requirements

## Critical Invariants Tested

1. **Workflow Integrity**: Complete workflow preserves data integrity at each step
2. **Historical Immutability**: Locked snapshots cannot be modified
3. **API Consistency**: Backend totals = UI totals = drilldown sums
4. **Reconciliation Accuracy**: High precision/recall metrics
5. **Forecast Calibration**: P25-P75 contains ~50% of actuals
6. **Graceful Degradation**: System fails loudly, not silently
7. **DB-Level Guarantees**: Constraints enforced at database level

## Next Steps

1. **Run all tests** to verify they pass
2. **Set up CI/CD** to run these tests on every commit
3. **Run mutation testing** periodically to verify test strength
4. **Monitor precision/recall** metrics in production
5. **Track calibration** of forecasts over time

## Notes

- These tests are **not optional** - they are required for CFO-grade trust
- Failure in any category means the product is "still a demo"
- These tests catch bugs that unit tests miss
- They prove the system is trustworthy, not just functional






