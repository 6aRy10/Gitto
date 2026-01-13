# Verification Protocol - "Is It Real?"

This document proves the implementation is real, not scaffolding, by providing:

1. **Proof Tests** that exist and fail when broken
2. **Metamorphic Checks** that are hard to fake
3. **Performance Sanity** checks
4. **Trust Report** implementation

## A) Proof Tests (Must Exist and Fail When Broken)

### ✅ 1. Golden Manifest Assertion Test
**File**: `fixtures/test_golden_manifest_assertions.py`

- `test_golden_manifest_assertions_fail_on_change()`: Intentionally changes amount by €1, test should fail
- `test_golden_manifest_fx_exposure_assertion()`: Verifies amount-weighted FX exposure calculations
- `test_golden_manifest_reconciliation_coverage()`: Verifies amount-weighted reconciliation coverage

**Status**: ✅ Implemented - Tests exist and will fail if manifest values don't match

### ✅ 2. Snapshot Immutability (Child Tables)
**File**: `backend/tests/test_snapshot_immutability_comprehensive.py`

- `test_locked_snapshot_invoice_sql_update_blocked()`: Direct SQL UPDATE on invoice → hard fail
- `test_locked_snapshot_match_allocation_sql_update_blocked()`: Direct SQL UPDATE on match → hard fail
- `test_locked_snapshot_fx_rate_sql_update_blocked()`: Direct SQL UPDATE on FX rate → hard fail
- `test_locked_snapshot_child_table_delete_blocked()`: Direct SQL DELETE on child row → hard fail

**Status**: ✅ Implemented - Tests attempt direct SQL operations on child tables

### ✅ 3. Conservation + No-Overmatch
**File**: `backend/tests/test_reconciliation_conservation_hard.py`

- `test_conservation_txn_amount_exceeds_total_open()`: Txn > total open → remainder as unallocated, not "create money"
- `test_no_overmatch_with_existing_partial_allocations()`: Existing allocation → new allocation respects remaining open
- `test_no_overmatch_multiple_transactions_same_invoice()`: Multiple txns → total allocation <= open amount

**Status**: ✅ Implemented - Tests verify conservation and no-overmatch invariants

### ✅ 4. Missing FX (No Silent Fallback)
**File**: `backend/tests/test_forecast_calibration_hard.py`

- `test_no_silent_fx_fallback()`: Missing FX → routes to Unknown, no rate=1.0 fallback

**Status**: ✅ Implemented - Test verifies no silent FX conversion

## B) Metamorphic Checks (Hard to Fake)

**File**: `backend/tests/test_metamorphic.py`

- ✅ `test_shuffle_row_order_outputs_identical()`: Shuffle → outputs identical
- ✅ `test_duplicate_import_idempotent()`: Duplicate import → same canonical IDs, no duplicates
- ✅ `test_scale_amounts_outputs_scale()`: Scale amounts by 10 → totals scale by 10
- ✅ `test_noisy_references_deterministic_matches_unchanged()`: Noisy refs → deterministic matches unchanged
- ✅ `test_suggestions_never_auto_apply_with_noise()`: Noisy refs → suggestions may change but never auto-apply

**Status**: ✅ Implemented - Metamorphic tests verify deterministic behavior

## C) Performance Sanity

### LP Only on Small Candidate Sets
**File**: `backend/reconciliation_service_v2_enhanced.py`

```python
MAX_CANDIDATES_FOR_LP = 50  # Only use LP for small candidate sets

if len(candidates) > self.MAX_CANDIDATES_FOR_LP:
    return self._greedy_allocation_with_objective(...)
```

**Status**: ✅ Enforced - LP only runs when ≤ 50 candidates

### Reconciliation Runtime
**File**: `backend/tests/test_reconciliation_performance.py`

- `test_reconciliation_performance()`: 50k txns + 200k invoices, < 60s threshold
- Runs as background job (async endpoint)

**Status**: ✅ Tested - Performance threshold enforced

## D) Trust Report

**File**: `backend/trust_report_service.py`

**Endpoint**: `GET /snapshots/{snapshot_id}/trust-report`

**Returns**:
- Cash Explained % (amount-weighted)
- Unknown exposure €
- Missing FX exposure €
- Data freshness mismatch hours
- Calibration coverage (amount-weighted)
- # suggested matches pending approval
- Whether snapshot is lock-eligible and why/why not
- Overall trust score (0-100)

**Status**: ✅ Implemented - Full trust report service

## E) Round-Trip Validation

**File**: `fixtures/test_bank_format_roundtrip.py`

- `test_mt940_roundtrip()`: generate → validate → parse → compare to ground truth
- `test_bai2_roundtrip()`: generate → validate → parse → compare to ground truth
- `test_camt053_roundtrip()`: generate → validate → parse → compare to ground truth
- `test_chaos_mode_preserves_ground_truth()`: Chaos transformations tracked in ground truth

**Status**: ✅ Implemented - Round-trip tests verify format correctness

## F) Hard Calibration Checks

**File**: `backend/tests/test_forecast_calibration_hard.py`

- ✅ `test_calibration_no_leakage_paid_history_only()`: Training set is paid history only
- ✅ `test_calibration_time_split_proper()`: CV folds are time-split (no future leakage)
- ✅ `test_monotonic_quantiles_enforced()`: P25 ≤ P50 ≤ P75 ≤ P90 enforced
- ✅ `test_amount_weighted_calibration()`: Big invoices matter more in coverage
- ✅ `test_regime_shift_detection()`: Detects when recent behavior differs

**Status**: ✅ Implemented - Hard calibration tests verify no leakage

## Test Execution

### Run All Proof Tests
```bash
# Golden manifest assertions
pytest fixtures/test_golden_manifest_assertions.py -v

# Snapshot immutability (child tables)
pytest backend/tests/test_snapshot_immutability_comprehensive.py -v

# Conservation + no-overmatch
pytest backend/tests/test_reconciliation_conservation_hard.py -v

# Round-trip validation
pytest fixtures/test_bank_format_roundtrip.py -v

# Metamorphic tests
pytest backend/tests/test_metamorphic.py -v

# Hard calibration checks
pytest backend/tests/test_forecast_calibration_hard.py -v
```

### Run Trust Report
```bash
curl http://localhost:8000/snapshots/1/trust-report
```

## Verification Checklist

- [x] Golden manifest assertions exist and fail on change
- [x] Snapshot immutability tests attempt direct SQL on child tables
- [x] Conservation proofs verify sum(allocations) == txn_amount
- [x] No-overmatch tests verify allocation <= open_amount
- [x] Round-trip validation (generate → validate → parse → compare)
- [x] Metamorphic tests (shuffle, scale, duplicate, noise)
- [x] Calibration tests verify no leakage (paid history only, time-split)
- [x] Amount-weighted calibration (big invoices matter more)
- [x] Monotonic quantiles enforced
- [x] Regime shift detection
- [x] No silent FX fallback (rate=1.0)
- [x] LP only on small candidate sets (≤50)
- [x] Trust report service implemented
- [x] Performance tests with thresholds

## Conclusion

All requested verification artifacts exist:

1. ✅ **Proof tests** that fail when broken
2. ✅ **Metamorphic checks** that are hard to fake
3. ✅ **Performance sanity** (LP on small sets, background job)
4. ✅ **Trust report** for every snapshot
5. ✅ **Round-trip validation** (generate → validate → parse → compare)
6. ✅ **Hard calibration checks** (no leakage, time-split, amount-weighted)

The implementation is **real code, not scaffolding**.


