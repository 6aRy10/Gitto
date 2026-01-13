# CFO Trust Questions: Comprehensive System Answers

This document answers all critical trust, truth, and operational questions about the cash flow forecasting system.

---

## A) Trust, Truth, and "What Would a CFO Bet Payroll On?"

### A1. "Is this number bank-true?" - Bank-true vs Modeled Numbers

**Current Implementation:**
- **Bank-true numbers**: Bank account balances (`BankAccount.balance`), bank transactions (`BankTransaction`), and reconciled invoice-bank matches
- **Modeled numbers**: Forecast predictions (`Invoice.predicted_payment_date`, `confidence_p25`, `confidence_p75`), segment delay statistics (`SegmentDelay`), and probabilistic allocations

**Gap**: There's no explicit visual distinction in the UI between bank-true and modeled numbers. The system tracks this in the data model but doesn't surface it clearly.

**Recommendation**: Add a `data_source` field or badge to all displayed numbers:
- `bank-true`: Direct from bank statements/transactions
- `reconciled`: Matched to invoices with high confidence
- `modeled`: Forecast predictions
- `unknown`: Missing data

**Location**: `backend/models.py` (BankAccount, BankTransaction, Invoice models)

---

### A2. As-of Time and Statement Period Display

**Current Implementation:**
- ✅ Snapshot metadata includes `created_at` timestamp
- ✅ Bank accounts track `balance_as_of`, `statement_start`, `statement_end`, `last_sync_at`
- ✅ API wrapper `wrap_with_metadata()` adds as-of timestamps to responses
- ✅ `get_snapshot_detail()` endpoint returns statement period info

**Gap**: Frontend components may not consistently display this metadata. The `as-of-stamp.tsx` component exists but needs verification of usage.

**Location**: 
- `backend/main.py:wrap_with_metadata()` (lines 25-43)
- `backend/main.py:get_snapshot_detail()` (lines 264-311)
- `src/components/ui/as-of-stamp.tsx`

---

### A3. Bank Data vs ERP Data Age Conflicts

**Current Implementation:**
- Bank accounts track `last_sync_at` and `balance_as_of`
- Snapshots track `created_at` for ERP data
- No explicit conflict resolution logic

**Gap**: **CRITICAL** - No policy for handling stale data conflicts. The system doesn't:
- Compare bank sync time vs ERP snapshot time
- Warn when data ages differ significantly
- Have a "which wins" policy

**Recommendation**: Implement a data freshness check:
```python
def check_data_freshness(db, entity_id):
    bank_sync = max(acc.last_sync_at for acc in bank_accounts)
    erp_snapshot = latest_snapshot.created_at
    age_diff = abs((bank_sync - erp_snapshot).total_seconds() / 3600)
    
    if age_diff > 24:  # More than 24 hours difference
        return {
            "warning": "Data age mismatch",
            "bank_age_hours": (now - bank_sync).total_seconds() / 3600,
            "erp_age_hours": (now - erp_snapshot).total_seconds() / 3600,
            "policy": "Using most recent for each data type"
        }
```

**Location**: Should be added to `backend/bank_service.py` or `backend/main.py`

---

### A4. Unknown / Not Ready Items Surface

**Current Implementation:**
- ✅ `calculate_unknown_bucket()` function explicitly tracks:
  - Missing due dates
  - Held AP bills (`hold_status == 1`)
  - Unmatched bank transactions
  - Missing FX rates for non-EUR invoices
- ✅ Frontend displays "Unknown Bucket" card in `ThirteenWeekWorkspace.tsx`
- ✅ KPI target: <5% unknown

**Status**: **IMPLEMENTED** - This is well-handled.

**Location**: 
- `backend/utils.py:calculate_unknown_bucket()` (lines 735-825, 903-993)
- `src/components/ThirteenWeekWorkspace.tsx` (lines 269-306)

---

### A5. Single Trust Metric: Cash Explained %

**Current Implementation:**
- ✅ `calculate_cash_explained_pct()` computes the primary trust metric
- ✅ Metric: % of bank cash movements that are explained (matched + categorized)
- ✅ Includes breakdown by reconciliation type (deterministic, rules, manual, suggested, unmatched)
- ✅ Tracks week-over-week trend
- ✅ API endpoint: `/entities/{entity_id}/cash-explained`

**What makes it go up:**
- More deterministic matches (Tier 1)
- More rules-based matches (Tier 2)
- Manual reconciliation of unmatched items
- Better bank reference data quality

**What makes it go down:**
- New unmatched transactions
- Poor bank reference data
- Missing invoice data for matching

**Status**: **IMPLEMENTED**

**Location**: 
- `backend/bank_service.py:calculate_cash_explained_pct()` (lines 150-247, 496-593)
- `backend/main.py` endpoint (around line 894)

---

## B) Data Identity & Idempotency (The "Duplicate Nightmare" Test)

### B1. Duplicate Invoice Upload Handling

**Current Implementation:**
- ✅ `canonical_id` is generated using SHA256 hash of:
  - `source_system + entity_id + document_type + document_number + counterparty_id + currency + amount + invoice_date + due_date + line_id`
- ✅ Uses `canonical_id` as the deduplication key
- ✅ If same invoice uploaded twice with different formatting, it should generate the same `canonical_id` if core fields match

**Gap**: **CRITICAL** - The upload process doesn't check for existing `canonical_id` before inserting. It will create duplicate database records if the same file is uploaded twice.

**Current Code Issue** (`backend/main.py:147-188`):
```python
for _, row in df.iterrows():
    cid = generate_canonical_id(row, source="Excel", entity_id=entity_id)
    inv = models.Invoice(...)
    invoices.append(inv)
db.bulk_save_objects(invoices)  # No duplicate check!
```

**Recommendation**: Add idempotency check:
```python
existing_cids = set(db.query(models.Invoice.canonical_id)
    .filter(models.Invoice.snapshot_id == snapshot.id)
    .all())
    
for _, row in df.iterrows():
    cid = generate_canonical_id(row, source="Excel", entity_id=entity_id)
    if cid in existing_cids:
        continue  # Skip duplicate
    # ... create invoice
```

**Location**: `backend/main.py:upload_file()` (lines 147-188)

---

### B2. Document Number Reuse Across Entities/Doc Types

**Current Implementation:**
- `canonical_id` includes `entity_id` and `document_type`, so same `document_number` in different entities/types will have different canonical IDs
- ✅ This is correct behavior - they are treated as different documents

**Status**: **CORRECTLY IMPLEMENTED**

**Location**: `backend/utils.py:generate_canonical_id()` (lines 26-60)

---

### B3. Partial Invoices, Rebills, and Credit Notes

**Current Implementation:**
- ✅ `document_type` field exists (INV, credit note, etc.)
- ✅ `canonical_id` includes `line_id` for multi-line invoices
- ❌ **Gap**: No explicit relationship tracking between:
  - Original invoice and credit note
  - Partial payment and full invoice
  - Rebill and original invoice

**Recommendation**: Add relationship fields:
```python
# In Invoice model
parent_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
related_invoice_ids = Column(JSON)  # Array of related invoice IDs
relationship_type = Column(String)  # "credit_note", "partial", "rebill", "original"
```

**Location**: `backend/models.py:Invoice` class

---

### B4. Idempotent Re-run of Ingestion

**Current Implementation:**
- ❌ **NOT IDEMPOTENT** - Re-running ingestion on the same file will create duplicate records
- The `canonical_id` is generated correctly, but there's no check to prevent duplicates

**Recommendation**: Implement upsert logic:
```python
# Check for existing canonical_id
existing = db.query(models.Invoice).filter(
    models.Invoice.canonical_id == cid,
    models.Invoice.snapshot_id == snapshot.id
).first()

if existing:
    # Update existing record
    for key, value in inv_data.items():
        setattr(existing, key, value)
else:
    # Create new record
    db.add(new_invoice)
```

**Location**: `backend/main.py:upload_file()`

---

### B5. Source of Truth Key: ERP IDs vs Canonical Fingerprints

**Current Implementation:**
- ✅ `canonical_id` is the primary identity key
- ✅ If `external_id` is provided (from ERP), it's used in canonical_id: `f"{source}:{entity_id}:{clean(external_id)}"`
- ✅ Otherwise, generates fingerprint from component fields

**Potential Conflict**: If ERP provides `external_id` but it conflicts with a previously generated fingerprint, the system will treat them as different records.

**Recommendation**: Add a conflict resolution table:
```python
class IdentityConflict(Base):
    canonical_id_1 = Column(String)
    canonical_id_2 = Column(String)
    resolution = Column(String)  # "merge", "separate", "pending"
```

**Status**: **MOSTLY CORRECT** - External IDs take precedence, but no conflict detection

**Location**: `backend/utils.py:generate_canonical_id()` (lines 36-37)

---

## C) Forecast Logic (Probabilistic + Stable, Not "Cool Math")

### C1. Small Sample Size (N=3) Handling

**Current Implementation:**
- ✅ `MIN_SAMPLE_SIZE = 15` threshold
- ✅ Hierarchical fallback: If segment has <15 samples, falls back to parent segment
- ✅ Fallback hierarchy: `customer+country+terms` → `customer+country` → `customer` → `country+terms` → `country` → `Global`
- ✅ If no segment has enough data, uses global baseline

**Status**: **IMPLEMENTED CORRECTLY**

**Location**: `backend/utils.py:run_forecast_model()` (lines 233-340)
- Line 263: `MIN_SAMPLE_SIZE = 15`
- Lines 276-292: Hierarchical segment calculation with N>=15 check

---

### C2. Outlier Protection / Winsorization

**Current Implementation:**
- ✅ Delay days are clipped: `delay_days.clip(-30, 180)` (line 250)
- ❌ **Gap**: No explicit winsorization at percentile level (e.g., cap at P99)
- ❌ **Gap**: No outlier detection before computing percentiles

**Recommendation**: Add winsorization:
```python
def winsorize_delays(delays, lower_pct=1, upper_pct=99):
    lower_bound = np.percentile(delays, lower_pct)
    upper_bound = np.percentile(delays, upper_pct)
    return delays.clip(lower_bound, upper_bound)
```

**Location**: `backend/utils.py:run_forecast_model()` (line 250)

---

### C3. Regime Shift / Behavior Change Adaptation

**Current Implementation:**
- ❌ **Gap**: No explicit regime shift detection
- ❌ **Gap**: No time-weighted or recency-weighted learning
- The model uses all historical data equally

**Recommendation**: Add recency weighting:
```python
# Weight recent payments more heavily
paid_df['recency_weight'] = 1.0 / (1 + (now - paid_df['payment_date']).dt.days / 90)
weighted_delays = paid_df['delay_days'] * paid_df['recency_weight']
```

**Location**: `backend/utils.py:run_forecast_model()` (lines 247-249)

---

### C4. Invoice Allocation Across Weeks

**Current Implementation:**
- ✅ Uses probabilistic allocation: 20% P25 (upside), 50% P50 (expected), 30% P75 (downside)
- ✅ Each invoice can contribute to 1-3 different weeks based on its distribution
- ✅ Allocation logic in `get_forecast_aggregation()`

**CFO Explanation**: "Each invoice has a probability distribution. We allocate 20% of its value to the optimistic week (P25), 50% to the expected week (P50), and 30% to the conservative week (P75). This means a single invoice's value can appear across multiple weeks, reflecting uncertainty."

**Status**: **IMPLEMENTED**

**Location**: `backend/utils.py:get_forecast_aggregation()` (lines 342-425)
- Lines 383-395: Probabilistic allocation logic

---

### C5. Missing/Incorrect Due Dates

**Current Implementation:**
- ✅ Missing due dates are tracked in `calculate_unknown_bucket()`
- ✅ Invoices without `expected_due_date` are excluded from forecast (line 314: `if inv.payment_date is not None: continue`)
- ❌ **Gap**: No default fallback (e.g., use payment terms + document date)
- ❌ **Gap**: No validation of due date reasonableness

**Recommendation**: Add fallback logic:
```python
if inv.expected_due_date is None:
    if inv.payment_terms_days and inv.document_date:
        inv.expected_due_date = inv.document_date + timedelta(days=inv.payment_terms_days)
    else:
        # Put in Unknown bucket
        continue
```

**Location**: `backend/utils.py:run_forecast_model()` (line 314)

---

## D) Bank Reconciliation Ladder (Approval-First Reality)

### D1. Tier 1 Deterministic Qualification

**Current Implementation:**
- ✅ Tier 1 requires: Invoice number in bank reference + amount match (within 0.01 tolerance)
- ❌ **Gap**: Does NOT require counterparty match
- Current logic: `find_deterministic_match()` checks `document_number in reference` and `abs(amount_diff) < 0.01`

**Recommendation**: Make counterparty optional but preferred:
```python
def find_deterministic_match(txn, invoices):
    ref = str(txn.reference or "").upper()
    for inv in invoices:
        inv_num = str(inv.document_number or "").upper()
        if inv_num and inv_num in ref:
            if abs(txn.amount - inv.amount) < 0.01:
                # Optional: Check counterparty similarity
                if txn.counterparty and inv.customer:
                    if similar(txn.counterparty, inv.customer):
                        return inv  # Strong match
                return inv  # Good match even without counterparty
    return None
```

**Location**: `backend/bank_service.py:find_deterministic_match()` (lines 62-71, 408-417)

---

### D2. Many-to-Many Matches

**Current Implementation:**
- ✅ `ReconciliationTable` supports many-to-many via junction table
- ✅ `amount_allocated` field allows partial matching
- ❌ **Gap**: Current matching logic only creates 1:1 matches
- ❌ **Gap**: No UI or logic to handle "one transaction matches multiple invoices" or vice versa

**Recommendation**: Enhance matching to support many-to-many:
```python
def find_multi_invoice_match(txn, invoices):
    # Find all invoices that could match this transaction
    candidates = []
    for inv in invoices:
        if abs(txn.amount - inv.amount) < 0.01:
            candidates.append(inv)
    
    # If sum of candidates equals transaction amount, create multi-match
    if sum(c.amount for c in candidates) == txn.amount:
        return candidates
    return None
```

**Location**: `backend/bank_service.py:generate_match_ladder()` (lines 8-60)

---

### D3. Tolerance Policy

**Current Implementation:**
- ✅ Amount tolerance: Hardcoded `0.01` (1 cent)
- ✅ Date window: Hardcoded `30 days` for Tier 2
- ❌ **Gap**: No configurable tolerance settings
- ❌ **Gap**: No logging of tolerance changes
- ❌ **Gap**: No per-entity or per-currency tolerance rules

**Recommendation**: Add tolerance configuration:
```python
class ReconciliationPolicy(Base):
    entity_id = Column(Integer, ForeignKey("entities.id"))
    amount_tolerance = Column(Float, default=0.01)
    date_window_days = Column(Integer, default=30)
    currency_specific_tolerances = Column(JSON)  # {"USD": 0.10, "EUR": 0.01}
```

**Location**: `backend/bank_service.py:find_rules_match()` (lines 73-82, 419-428)

---

### D4. Fuzzy Match Auto-Reconciliation Prevention

**Current Implementation:**
- ✅ Tier 3 (Suggested) matches are NOT auto-reconciled
- ✅ They are flagged with `reconciliation_type = "Suggested"` and require user approval
- ✅ `get_reconciliation_suggestions()` API returns suggestions for approval

**Status**: **CORRECTLY IMPLEMENTED**

**Location**: 
- `backend/bank_service.py:generate_match_ladder()` (lines 46-54)
- `backend/bank_service.py:get_reconciliation_suggestions()` (lines 249-285, 595-631)

---

### D5. Unmatched Transaction Lifecycle

**Current Implementation:**
- ✅ `BankTransaction.resolution_status`: "Unresolved", "Match Suggested", "Resolved"
- ✅ `BankTransaction.assignee` field for ownership
- ✅ `BankTransaction.reconciliation_type`: "Manual" for unmatched items
- ❌ **Gap**: No explicit workflow states or status transitions
- ❌ **Gap**: No SLA tracking (how long has it been unmatched?)

**Recommendation**: Add lifecycle tracking:
```python
class UnmatchedTransactionLifecycle(Base):
    transaction_id = Column(Integer, ForeignKey("bank_transactions.id"))
    status = Column(String)  # "New", "Assigned", "In_Review", "Resolved", "Escalated"
    assigned_to = Column(String)
    assigned_at = Column(DateTime)
    days_unmatched = Column(Integer)
    escalation_level = Column(Integer, default=0)
```

**Location**: `backend/models.py:BankTransaction` (lines 65-83, 394-412)

---

## E) AP Outflows & Payment Runs (Where Forecasts Often Die)

### E1. Due Dates vs Cash Exit Dates

**Current Implementation:**
- ✅ `VendorBill.due_date` - when bill is due
- ✅ `VendorBill.scheduled_payment_date` - when payment is scheduled
- ✅ `Entity.payment_run_day` - default payment day (e.g., Thursday = 3)
- ❌ **Gap**: Forecast uses `due_date` but should use `scheduled_payment_date` or payment run logic

**Recommendation**: Use cash exit date for forecasting:
```python
def get_cash_exit_date(vendor_bill, entity):
    if vendor_bill.scheduled_payment_date:
        return vendor_bill.scheduled_payment_date
    # Apply payment run logic
    due_date = vendor_bill.due_date
    payment_day = entity.payment_run_day
    # Find next payment run day after due date
    days_until_payment = (payment_day - due_date.weekday()) % 7
    return due_date + timedelta(days=days_until_payment)
```

**Location**: `backend/cash_calendar_service.py` (outflow aggregation logic)

---

### E2. Bills on Hold / Not Approved

**Current Implementation:**
- ✅ `VendorBill.hold_status` field (0=Active, 1=Hold)
- ✅ `VendorBill.approval_date` field
- ❌ **Gap**: Held bills may still be included in cash-out forecast
- ✅ `calculate_unknown_bucket()` includes held bills in unknown category

**Recommendation**: Explicitly exclude held bills from committed cash-out:
```python
def get_committed_outflows(snapshot_id):
    bills = db.query(models.VendorBill).filter(
        models.VendorBill.snapshot_id == snapshot_id,
        models.VendorBill.hold_status == 0,  # Only active bills
        models.VendorBill.approval_date.isnot(None)  # Only approved
    ).all()
    return bills
```

**Location**: `backend/cash_calendar_service.py:get_outflow_summary()`

---

### E3. Payment Run Modeling

**Current Implementation:**
- ✅ `Entity.payment_run_day` - default day of week (0=Mon, 3=Thu)
- ✅ `RecurringOutflow` model with frequency scheduling
- ✅ `project_recurring_outflows()` projects recurring items
- ❌ **Gap**: No explicit "urgent off-cycle payment" handling
- ❌ **Gap**: Payment runs are modeled as "every Thursday" but no exception handling

**Recommendation**: Add payment run exceptions:
```python
class PaymentRunException(Base):
    entity_id = Column(Integer, ForeignKey("entities.id"))
    vendor_bill_id = Column(Integer, ForeignKey("vendor_bills.id"))
    scheduled_date = Column(DateTime)  # Override default payment run day
    reason = Column(String)  # "Urgent", "Vendor Request", etc.
```

**Location**: `backend/cash_calendar_service.py:project_recurring_outflows()` (lines 286-329)

---

### E4. Double Counting Prevention (Recurring Templates vs Real Bills)

**Current Implementation:**
- ✅ `RecurringOutflow` creates `OutflowItem` entries
- ✅ `VendorBill` is separate from recurring templates
- ❌ **Gap**: No deduplication logic to prevent counting both a recurring template AND a real vendor bill for the same payment

**Recommendation**: Add matching logic:
```python
def prevent_double_counting(outflow_items, vendor_bills):
    # Match vendor bills to recurring templates by vendor name + amount + date proximity
    for bill in vendor_bills:
        matching_recurring = find_matching_recurring(bill)
        if matching_recurring:
            # Remove the recurring item, use the real bill instead
            remove_recurring_item(matching_recurring)
```

**Location**: `backend/cash_calendar_service.py:get_outflow_summary()`

---

### E5. Discretionary Outflow Classification

**Current Implementation:**
- ✅ `VendorBill.is_discretionary` field (0=Committed, 1=Delayable)
- ✅ `OutflowItem.is_discretionary` field
- ✅ `RecurringOutflow.is_discretionary` field
- ❌ **Gap**: No clear policy on who decides or how it's classified
- ❌ **Gap**: No audit trail of discretionary classification changes

**Recommendation**: Add classification policy and audit:
```python
class DiscretionaryPolicy(Base):
    entity_id = Column(Integer, ForeignKey("entities.id"))
    vendor_name = Column(String, nullable=True)  # NULL = all vendors
    category = Column(String, nullable=True)  # NULL = all categories
    is_discretionary = Column(Integer)
    set_by = Column(String)
    set_at = Column(DateTime)
```

**Location**: `backend/models.py:VendorBill`, `OutflowItem`, `RecurringOutflow`

---

## F) Snapshots, Variance, and Auditability (The Weekly Meeting Core)

### F1. What Does a Snapshot Freeze?

**Current Implementation:**
- ✅ Snapshot freezes: Raw invoice data, derived segment statistics (`SegmentDelay`), FX rates (`WeeklyFXRate`), outflows (`OutflowItem`)
- ✅ `Snapshot.is_locked` flag prevents modifications
- ❌ **Gap**: No explicit documentation of what's frozen vs what can change
- ❌ **Gap**: Forecast predictions may be recomputed even on locked snapshots

**Recommendation**: Document snapshot contents:
```python
class SnapshotContents(Base):
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"))
    frozen_data = Column(JSON)  # {"invoices": True, "fx_rates": True, "forecasts": False}
    frozen_at = Column(DateTime)
```

**Location**: `backend/models.py:Snapshot` (lines 8-31, 337-360)

---

### F2. FX Rate Updates and Old Snapshots

**Current Implementation:**
- ✅ `WeeklyFXRate` is linked to `snapshot_id` - rates are locked per snapshot
- ✅ `get_snapshot_fx_rate()` fetches snapshot-specific rates
- ✅ Rates are set when snapshot is created via `/snapshots/{id}/fx-rates` endpoint

**Status**: **CORRECTLY IMPLEMENTED** - Old snapshots won't change if new FX rates are added

**Location**: 
- `backend/models.py:WeeklyFXRate` (lines 161-170, 490-499)
- `backend/utils.py:get_snapshot_fx_rate()` (lines 638-668)

---

### F3. Variance Explanation: New Items vs Timing Shifts vs Reconciliation vs Policy

**Current Implementation:**
- ✅ `compare_snapshots()` function exists (referenced in imports)
- ❌ **Gap**: Implementation not found in codebase search
- ❌ **Gap**: No explicit variance categorization

**Recommendation**: Implement variance breakdown:
```python
def explain_variance(current_snapshot, previous_snapshot):
    return {
        "new_items": [...],  # Invoices that appeared
        "timing_shifts": [...],  # Same invoice, different predicted date
        "reconciliation_changes": [...],  # Bank matches changed
        "policy_changes": [...],  # Hold status, discretionary flags changed
        "fx_changes": [...]  # FX rate updates
    }
```

**Location**: Should be in `backend/utils.py` or `backend/reporting_service.py`

---

### F4. Drill-Down to Exact Row IDs

**Current Implementation:**
- ✅ Invoice IDs, bank transaction IDs are tracked
- ✅ `ReconciliationTable` links transactions to invoices
- ❌ **Gap**: No explicit drill-down API that returns row IDs for a variance

**Recommendation**: Add drill-down endpoint:
```python
@app.get("/snapshots/{snapshot_id}/variance-drilldown")
def get_variance_drilldown(snapshot_id, week_index, variance_type):
    # Return exact invoice IDs, bank transaction IDs that caused variance
    return {
        "invoice_ids": [...],
        "bank_transaction_ids": [...],
        "reconciliation_ids": [...]
    }
```

**Location**: Should be in `backend/main.py` or `backend/reporting_service.py`

---

### F5. Minimum Audit Trail for "Why Week 4 Moved by €2M"

**Current Implementation:**
- ✅ `AuditLog` model exists with: `timestamp`, `user`, `action`, `resource_type`, `resource_id`, `changes`
- ✅ `record_audit_log()` function exists
- ❌ **Gap**: Not all critical operations log to audit trail
- ❌ **Gap**: No snapshot comparison audit trail

**Recommendation**: Ensure all critical operations log:
- Snapshot creation/deletion
- Reconciliation matches (especially manual overrides)
- Forecast recomputations
- FX rate changes
- Hold status changes
- Discretionary flag changes

**Location**: 
- `backend/models.py:AuditLog` (lines 172-181, 501-510)
- `backend/utils.py:record_audit_log()` (lines 624-636)

---

## G) Multi-Entity + FX (Silent Errors Are Fatal)

### G1. Currency Mixing Prevention

**Current Implementation:**
- ✅ `Entity.currency` - base currency per entity
- ✅ `Invoice.currency`, `BankTransaction.currency`, `VendorBill.currency` - transaction currencies
- ✅ `convert_currency()` function converts to base currency using snapshot-locked FX rates
- ✅ `get_forecast_aggregation()` converts all amounts to EUR before summing

**Status**: **MOSTLY CORRECT** - Conversion happens, but no explicit validation that all amounts are converted before aggregation

**Recommendation**: Add validation:
```python
def validate_currency_consistency(snapshot_id, target_currency="EUR"):
    invoices = get_invoices(snapshot_id)
    unconverted = [inv for inv in invoices if inv.currency != target_currency and not inv.converted_amount]
    if unconverted:
        raise ValueError(f"{len(unconverted)} invoices not converted to {target_currency}")
```

**Location**: `backend/utils.py:convert_currency()` (lines 705-713, 873-881)

---

### G2. Missing FX Rate Handling

**Current Implementation:**
- ✅ `get_snapshot_fx_rate()` returns 1.0 as fallback if rate not found
- ✅ `calculate_unknown_bucket()` includes invoices with missing FX rates
- ❌ **Gap**: Silent fallback to 1.0 could cause incorrect forecasts
- ❌ **Gap**: No warning when FX rate is missing

**Recommendation**: Make missing FX explicit:
```python
def convert_currency(db, snapshot_id, amount, from_curr, to_curr="EUR"):
    if from_curr == to_curr:
        return amount
    
    rate = get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr)
    if rate == 1.0 and from_curr != to_curr:
        # Rate not found - this is an error
        raise ValueError(f"FX rate not found: {from_curr} -> {to_curr} for snapshot {snapshot_id}")
    return amount * rate
```

**Location**: `backend/utils.py:get_snapshot_fx_rate()` (lines 638-668)

---

### G3. FX Conversion Date: Invoice Date vs Due Date vs Bank Date vs Snapshot Date

**Current Implementation:**
- ✅ FX rates are locked to snapshot via `WeeklyFXRate.snapshot_id`
- ✅ `effective_week_start` field exists but may not be used correctly
- ❌ **Gap**: No clear policy on which date to use for conversion
- ❌ **Gap**: Uses snapshot date, not invoice/due/bank date

**Recommendation**: Implement date-specific conversion:
```python
def convert_currency_at_date(db, snapshot_id, amount, from_curr, to_curr, conversion_date):
    # Try to get rate for the specific date
    rate = get_fx_rate_for_date(db, snapshot_id, from_curr, to_curr, conversion_date)
    if not rate:
        # Fallback to snapshot date
        rate = get_snapshot_fx_rate(db, snapshot_id, from_curr, to_curr)
    return amount * rate

# Policy:
# - For forecasts: Use snapshot date (locked rate)
# - For historical: Use invoice date or bank date
# - For due date forecasts: Use due date (if rate available)
```

**Location**: `backend/utils.py:convert_currency()` (lines 705-713)

---

### G4. Intercompany Transfer Detection

**Current Implementation:**
- ✅ `detect_intercompany_washes()` function exists
- ✅ Logic: Transaction counterparty matches another entity name
- ✅ `BankTransaction.is_wash` flag
- ✅ `approve_wash_service()` for manual approval
- ❌ **Gap**: Detection is heuristic-based (name matching), not account-based
- ❌ **Gap**: No known internal accounts list

**Recommendation**: Add internal accounts configuration:
```python
class InternalAccount(Base):
    entity_id = Column(Integer, ForeignKey("entities.id"))
    account_number = Column(String)
    account_name = Column(String)
    is_intercompany = Column(Integer, default=1)
```

**Location**: 
- `backend/bank_service.py:detect_intercompany_washes()` (lines 125-148, 471-494)
- `backend/bank_service.py:approve_wash_service()` (lines 332-347, 678-693)

---

## H) Performance & Scale (50 Invoices Becomes 50k Quickly)

### H1. O(n²) Operations with 200k Rows

**Current Implementation:**
- ❌ **CRITICAL GAP**: `generate_match_ladder()` loops through all unreconciled transactions and for each, loops through all open invoices
- This is O(n*m) where n=transactions, m=invoices
- With 200k invoices and 50k transactions, this could be 10 billion comparisons

**Current Code** (`backend/bank_service.py:31-60`):
```python
for txn in unreconciled_txns:  # O(n)
    for inv in open_invoices:  # O(m)
        # Matching logic
```

**Recommendation**: Use indexed lookups:
```python
# Build index by document_number
invoice_index = {inv.document_number.upper(): inv for inv in open_invoices if inv.document_number}

# Build index by amount (with tolerance buckets)
amount_index = {}
for inv in open_invoices:
    bucket = round(inv.amount, 2)  # 0.01 precision
    if bucket not in amount_index:
        amount_index[bucket] = []
    amount_index[bucket].append(inv)

# Now matching is O(1) lookup instead of O(m) scan
for txn in unreconciled_txns:
    # Check index instead of scanning all invoices
    candidates = invoice_index.get(txn.reference.upper(), [])
```

**Location**: `backend/bank_service.py:generate_match_ladder()` (lines 8-60, 354-406)

---

### H2. Per-Row DB Queries in Loops

**Current Implementation:**
- ✅ `bulk_save_objects()` used for invoice insertion (good)
- ❌ **Gap**: `generate_match_ladder()` may have N+1 query issues
- ✅ Uses `.all()` to fetch all invoices at once, not per-transaction

**Status**: **MOSTLY OK** - Fetches are batched, but matching logic could be optimized

**Location**: `backend/bank_service.py:generate_match_ladder()` (lines 16-27)

---

### H3. Synchronous vs Background Jobs

**Current Implementation:**
- ❌ **Gap**: All operations appear to be synchronous
- ❌ **Gap**: No background job system for:
  - Forecast computation
  - Reconciliation matching
  - Large file uploads

**Recommendation**: Add background jobs:
```python
# Use Celery or similar
@celery.task
def run_forecast_async(snapshot_id):
    # Long-running forecast computation
    run_forecast_model(db, snapshot_id)

@celery.task
def reconcile_async(entity_id):
    # Long-running reconciliation
    generate_match_ladder(db, entity_id)
```

**Location**: Should be added to `backend/main.py` endpoints

---

### H4. Segment Stats Caching

**Current Implementation:**
- ✅ `SegmentDelay` table stores pre-computed segment statistics
- ❌ **Gap**: No caching layer (Redis/Memcached) for frequently accessed stats
- ❌ **Gap**: Stats are recomputed on every forecast run

**Recommendation**: Add caching:
```python
@cache.memoize(timeout=3600)
def get_segment_stats(snapshot_id, segment_type, segment_key):
    # Check cache first, then DB
    cache_key = f"segment:{snapshot_id}:{segment_type}:{segment_key}"
    return cache.get(cache_key) or compute_and_cache(...)
```

**Location**: `backend/utils.py:run_forecast_model()` (lines 294-308)

---

### H5. Response Time Targets

**Current Implementation:**
- ❌ **Gap**: No documented response time targets
- ❌ **Gap**: No performance monitoring

**Recommendation**: Set targets:
- `/workspace-13w`: < 2 seconds
- `/ask-insights`: < 5 seconds (if AI-powered)
- `/upload`: < 10 seconds for <10k rows, async for larger

**Location**: Should be documented in API specification

---

## I) Grounded AI Analyst (No Hallucinations, Ever)

### I1. Exact Computation and Evidence Rows

**Current Implementation:**
- ❌ **Gap**: No AI analyst implementation found in codebase
- ❌ **Gap**: No "ask-insights" endpoint implementation

**Recommendation**: Implement grounded AI:
```python
@app.post("/ask-insights")
def ask_insights(question: str, snapshot_id: int):
    # 1. Parse question to identify what data is needed
    # 2. Query database for exact data
    # 3. Perform deterministic calculations
    # 4. Generate narrative from results
    # 5. Return with evidence row IDs
    
    results = query_database(question, snapshot_id)
    narrative = generate_narrative(results, question)
    
    return {
        "answer": narrative,
        "evidence": {
            "invoice_ids": results.invoice_ids,
            "computation": results.formula,
            "source_data": results.raw_data
        }
    }
```

**Location**: Should be added to `backend/main.py`

---

### I2. Refusing vs Guessing for Unknown Data

**Current Implementation:**
- ❌ **Gap**: No AI analyst to test this

**Recommendation**: Implement strict schema validation:
```python
ALLOWED_FIELDS = {
    "invoices": ["amount", "due_date", "customer", "currency", ...],
    "bank_transactions": ["amount", "date", "counterparty", ...],
    # Explicit list of all queryable fields
}

def validate_query(question):
    requested_fields = extract_fields(question)
    unknown_fields = [f for f in requested_fields if f not in ALLOWED_FIELDS]
    if unknown_fields:
        return {
            "error": "Unknown fields requested",
            "unknown_fields": unknown_fields,
            "available_fields": ALLOWED_FIELDS
        }
```

**Location**: Should be in AI analyst implementation

---

### I3. Canonical Schema Rule

**Current Implementation:**
- ✅ Canonical schema exists in `models.py`
- ❌ **Gap**: No AI analyst to enforce this rule

**Recommendation**: Create schema registry:
```python
CANONICAL_SCHEMA = {
    "Invoice": {
        "amount": "Float",
        "due_date": "DateTime",
        "customer": "String",
        # ... all fields from Invoice model
    },
    # ... other models
}

def ai_can_only_speak_about(schema=CANONICAL_SCHEMA):
    # Enforce that AI only references these fields
    pass
```

**Location**: Should be in AI analyst implementation

---

### I4. Separating Retrieval + Arithmetic from Narrative

**Current Implementation:**
- ❌ **Gap**: No AI analyst implementation

**Recommendation**: Two-stage pipeline:
```python
# Stage 1: Deterministic retrieval and calculation
def retrieve_and_calculate(question, snapshot_id):
    # SQL queries, pandas operations, etc.
    # Returns structured data
    return {
        "numbers": [...],
        "formulas": [...],
        "row_ids": [...]
    }

# Stage 2: LLM narrative generation (only from Stage 1 results)
def generate_narrative(structured_results, question):
    prompt = f"""
    Question: {question}
    Data: {structured_results}
    
    Generate a narrative explanation using ONLY the provided data.
    Do not invent numbers or facts.
    """
    return llm.generate(prompt)
```

**Location**: Should be in AI analyst implementation

---

## J) Security & Blast Radius (Finance Buyers Care)

### J1. Connector Credential Leak Blast Radius

**Current Implementation:**
- ✅ `SnowflakeConfig` stores credentials
- ❌ **Gap**: Passwords stored as plain text: `password = Column(String)`
- ❌ **Gap**: No encryption at rest
- ❌ **Gap**: No secrets manager integration
- ❌ **Gap**: No credential rotation policy

**Recommendation**: 
1. Use environment variables or secrets manager (AWS Secrets Manager, Azure Key Vault)
2. Encrypt at rest
3. Implement credential rotation
4. Add audit logging for credential access

**Location**: `backend/models.py:SnowflakeConfig` (lines 217-234, 546-563)

---

### J2. Liquidity Lever Execution and Logging

**Current Implementation:**
- ✅ `TreasuryAction` model tracks actions
- ✅ `LeverPolicy` model defines guardrails
- ✅ `record_audit_log()` function exists
- ❌ **Gap**: Not all lever actions may be logged
- ❌ **Gap**: No explicit approval workflow

**Recommendation**: Ensure all lever actions log:
```python
@app.post("/entities/{entity_id}/execute-lever")
def execute_lever(action_type, target_id, user):
    # Check policy
    policy = get_lever_policy(entity_id)
    if action.amount > policy.approval_threshold:
        # Require approval
        return {"status": "approval_required"}
    
    # Execute action
    result = perform_action(action_type, target_id)
    
    # Log to audit trail
    record_audit_log(db, user, "ExecuteLever", "TreasuryAction", result.id, {
        "action_type": action_type,
        "amount": result.expected_impact
    })
    
    return result
```

**Location**: 
- `backend/models.py:TreasuryAction` (lines 280-293, 609-621)
- `backend/models.py:LeverPolicy` (lines 294-308, 623-637)

---

### J3. Snapshot Immutability

**Current Implementation:**
- ✅ `Snapshot.is_locked` flag exists
- ❌ **Gap**: Immutability is "by convention" - no database constraints
- ❌ **Gap**: Code can still modify locked snapshots if not checked

**Recommendation**: Add database constraints and application-level checks:
```python
# Application-level check
def update_snapshot(snapshot_id, updates):
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if snapshot.is_locked:
        raise ValueError("Cannot modify locked snapshot")
    # ... proceed with update

# Database-level constraint (if using triggers)
# CREATE TRIGGER prevent_locked_snapshot_update
# BEFORE UPDATE ON snapshots
# WHEN is_locked = 1
# BEGIN
#     RAISE(ABORT, 'Cannot update locked snapshot');
# END;
```

**Location**: `backend/models.py:Snapshot` (lines 8-31)

---

## Summary: Critical Gaps to Address

### High Priority (CFO Trust Blockers)
1. **Idempotency**: Duplicate upload prevention (B1, B4)
2. **Data Age Conflicts**: Bank vs ERP staleness handling (A3)
3. **FX Missing Rates**: Silent fallback to 1.0 (G2)
4. **Performance**: O(n²) reconciliation matching (H1)
5. **Security**: Plain text password storage (J1)

### Medium Priority (Operational Issues)
6. **Many-to-Many Matches**: Reconciliation support (D2)
7. **Tolerance Policy**: Configurable and logged (D3)
8. **Payment Run Logic**: Cash exit date vs due date (E1)
9. **Variance Explanation**: Detailed breakdown (F3)
10. **Background Jobs**: Async processing for scale (H3)

### Low Priority (Enhancements)
11. **Regime Shift Detection**: Recency weighting (C3)
12. **Outlier Winsorization**: Percentile capping (C2)
13. **AI Analyst**: Grounded implementation (I1-I4)
14. **Caching**: Segment stats caching (H4)

---

## Implementation Priority Matrix

| Issue | Impact | Effort | Priority |
|-------|--------|--------|----------|
| Idempotency (B1, B4) | High | Low | **P0** |
| Data Age Conflicts (A3) | High | Medium | **P0** |
| FX Missing Rates (G2) | High | Low | **P0** |
| O(n²) Performance (H1) | High | Medium | **P1** |
| Plain Text Passwords (J1) | High | Medium | **P1** |
| Many-to-Many Matches (D2) | Medium | High | **P2** |
| Tolerance Policy (D3) | Medium | Low | **P2** |
| Cash Exit Date (E1) | Medium | Low | **P2** |
| Variance Explanation (F3) | Medium | Medium | **P2** |
| Background Jobs (H3) | Medium | High | **P3** |

---

*Document generated: 2024*
*Last updated: Based on codebase analysis*

