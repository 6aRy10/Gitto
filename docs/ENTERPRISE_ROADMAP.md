# Gitto Enterprise Roadmap
## From "Looks Enterprise" to "Is Enterprise"

---

## Current State (What Actually Exists)

### ✅ Implemented
- Excel upload with column mapping
- Snapshot creation and locking
- Basic invoice storage with canonical IDs
- Simple forecasting (delay-based)
- 13-week grid visualization
- Basic truth labeling (Bank-True/Reconciled/Modeled/Unknown)
- Audit logging (basic)
- Single-entity support

### ❌ Not Yet Implemented
- Real-time connectors (banks, ERP, AP systems)
- Many-to-many reconciliation allocations
- Probabilistic forecasting with backtesting
- Multi-tenant isolation
- RBAC with proper permissions
- Secrets management
- SSO/SCIM
- Warehouse sync (Snowflake/BigQuery)

---

## Phase 1: Connectivity Layer (Foundation)
**Goal:** No manual Excel dependence; data flows continuously.

### 1.1 Connector SDK Architecture
```
models/
  connector.py          # Connector, Connection, SyncRun, SourceProfile
  
connectors/
  base.py               # BaseConnector (test/extract/normalize interface)
  bank_mt940.py         # SWIFT MT940 parser
  bank_bai2.py          # BAI2 parser
  erp_netsuite.py       # NetSuite SuiteTalk
  erp_quickbooks.py     # QuickBooks OAuth
  erp_xero.py           # Xero API
  warehouse_snowflake.py # Snowflake read/writeback
  
services/
  sync_service.py       # Background job orchestration
  freshness_service.py  # Data freshness monitoring
```

### 1.2 Database Schema Additions
```sql
-- Connectors
CREATE TABLE connectors (
    id INTEGER PRIMARY KEY,
    type VARCHAR(50) NOT NULL,  -- 'bank_mt940', 'erp_netsuite', etc.
    name VARCHAR(100) NOT NULL,
    config_encrypted TEXT,       -- Encrypted connection config
    entity_id INTEGER REFERENCES entities(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Connections (specific endpoint instances)
CREATE TABLE connections (
    id INTEGER PRIMARY KEY,
    connector_id INTEGER REFERENCES connectors(id),
    endpoint_url VARCHAR(500),
    credentials_ref VARCHAR(100),  -- Reference to secrets manager
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(20),  -- 'idle', 'running', 'failed', 'success'
    sync_cursor TEXT,  -- For incremental sync
    created_at TIMESTAMP
);

-- Sync Runs (audit trail)
CREATE TABLE sync_runs (
    id INTEGER PRIMARY KEY,
    connection_id INTEGER REFERENCES connections(id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20),
    rows_extracted INTEGER,
    rows_created INTEGER,
    rows_updated INTEGER,
    rows_skipped INTEGER,
    error_message TEXT,
    dataset_id INTEGER REFERENCES datasets(id)
);

-- Source Profiles (field mappings)
CREATE TABLE source_profiles (
    id INTEGER PRIMARY KEY,
    connector_id INTEGER REFERENCES connectors(id),
    name VARCHAR(100),
    field_mappings JSONB,  -- {"source_field": "canonical_field", ...}
    transform_rules JSONB,  -- Date formats, currency codes, etc.
    is_active BOOLEAN DEFAULT TRUE
);

-- Datasets (versioned imports)
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY,
    sync_run_id INTEGER REFERENCES sync_runs(id),
    source_type VARCHAR(50),
    as_of_timestamp TIMESTAMP,
    row_count INTEGER,
    checksum VARCHAR(64),
    raw_payload_ref VARCHAR(200),  -- S3/blob reference for raw data
    created_at TIMESTAMP
);
```

### 1.3 Implementation Priority
1. **MT940/BAI2 Parser** (banks) - Most common format
2. **QuickBooks/Xero** (SMB accounting) - Quick wins
3. **NetSuite** (enterprise ERP) - High value
4. **Snowflake** (warehouse) - Bidirectional sync

---

## Phase 2: Canonical Data Platform
**Goal:** "Same input → same output" with full traceability.

### 2.1 Canonical Models
```python
# Core entities with stable identity
class BankAccount:
    id, entity_id, bank_name, account_number_hash, currency, is_active

class BankTxn:
    id, bank_account_id, txn_ref, amount, currency, value_date, 
    booking_date, counterparty_name, counterparty_account_hash,
    remittance_info, canonical_id, dataset_id

class Invoice:
    id, entity_id, invoice_number, customer_id, amount, currency,
    issue_date, due_date, payment_date, canonical_id, dataset_id,
    source_system, source_id

class VendorBill:
    id, entity_id, bill_number, vendor_id, amount, currency,
    invoice_date, due_date, payment_date, approval_status,
    canonical_id, dataset_id

class MatchAllocation:
    id, bank_txn_id, invoice_id, vendor_bill_id, allocated_amount,
    match_tier, confidence_score, approved_by, approved_at,
    created_at

class Snapshot:
    id, name, entity_id, as_of_timestamp, dataset_ids[], 
    assumption_set_id, fx_rate_version, is_locked, locked_at,
    locked_by, checksum
```

### 2.2 Lineage Graph
- Every forecast number → drill to row IDs → source system → sync run
- Stored as `lineage_edges` table with (parent_type, parent_id, child_type, child_id)

### 2.3 Data Quality Engine
```python
class DataQualityEngine:
    def run_checks(self, snapshot_id) -> DataQualityReport:
        return {
            "unknown_bucket": self.get_unknown_items(),
            "duplicates": self.find_duplicates(),
            "missing_fx": self.check_fx_coverage(),
            "stale_sources": self.check_freshness(),
            "currency_mismatches": self.check_currencies(),
            "missing_due_dates": self.check_required_fields()
        }
```

---

## Phase 3: Bank Truth + Reconciliation Cockpit
**Goal:** CFO can reconcile reality with systems—and explain deltas.

### 3.1 Matching Engine (O(n*k) not O(n*m))
```python
class MatchingEngine:
    def find_candidates(self, bank_txn: BankTxn) -> List[MatchCandidate]:
        # 1. Extract invoice refs from remittance_info
        refs = self.extract_refs(bank_txn.remittance_info)
        
        # 2. Index lookup by amount bucket + date window
        candidates = self.index.query(
            amount_range=(bank_txn.amount * 0.98, bank_txn.amount * 1.02),
            date_range=(bank_txn.value_date - 7, bank_txn.value_date + 7),
            counterparty=bank_txn.counterparty_name
        )
        
        # 3. Score candidates by match tier
        for c in candidates:
            c.tier = self.classify_tier(bank_txn, c)
            c.confidence = self.calculate_confidence(bank_txn, c)
        
        return sorted(candidates, key=lambda x: (x.tier, -x.confidence))
    
    def classify_tier(self, txn, candidate) -> int:
        if self.exact_ref_match(txn, candidate):
            return 1  # Deterministic
        if self.rule_match(txn, candidate):
            return 2  # Rules-based
        if candidate.confidence > 0.7:
            return 3  # Suggested (needs approval)
        return 4  # Manual
```

### 3.2 Allocation UI Support
- Split amounts across multiple invoices
- Mark write-offs, fees, chargebacks
- Allocation conservation: sum(allocations) == txn.amount

### 3.3 Exception Workflow
```sql
CREATE TABLE exceptions (
    id INTEGER PRIMARY KEY,
    bank_txn_id INTEGER,
    status VARCHAR(20),  -- 'new', 'assigned', 'in_review', 'resolved', 'escalated'
    assignee_id INTEGER,
    sla_due_at TIMESTAMP,
    resolution_type VARCHAR(50),
    resolution_notes TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Phase 4: Forecasting Intelligence
**Goal:** Probabilities that behave like probabilities.

### 4.1 Segment Hierarchy with Fallbacks
```python
SEGMENT_HIERARCHY = [
    ("customer", "payment_terms", "country"),  # Most specific
    ("customer", "payment_terms"),
    ("customer",),
    ("country", "payment_terms"),
    ("payment_terms",),
    ("entity",),  # Fallback
]

MIN_SAMPLE_SIZE = 15

def get_delay_distribution(invoice, history_df):
    for segment_keys in SEGMENT_HIERARCHY:
        segment_data = filter_by_segment(history_df, invoice, segment_keys)
        if len(segment_data) >= MIN_SAMPLE_SIZE:
            return compute_percentiles(segment_data['delay_days'])
    return DEFAULT_DISTRIBUTION
```

### 4.2 Recency Weighting + Regime Shift
```python
def apply_recency_weights(delays, half_life_days=90):
    ages = (datetime.now() - delays['payment_date']).dt.days
    weights = np.exp(-ages / half_life_days)
    return delays, weights

def detect_regime_shift(delays, window=30):
    recent = delays[delays['payment_date'] > datetime.now() - timedelta(days=window)]
    historical = delays[delays['payment_date'] <= datetime.now() - timedelta(days=window)]
    
    if len(recent) < 10:
        return None
    
    # Kolmogorov-Smirnov test
    stat, pvalue = ks_2samp(recent['delay_days'], historical['delay_days'])
    if pvalue < 0.05:
        return {"shift_detected": True, "recent_mean": recent.mean(), "historical_mean": historical.mean()}
    return None
```

### 4.3 Backtesting & Calibration
```sql
CREATE TABLE forecast_backtests (
    id INTEGER PRIMARY KEY,
    snapshot_id INTEGER,
    forecast_week DATE,
    invoice_id INTEGER,
    predicted_p25 DECIMAL,
    predicted_p50 DECIMAL,
    predicted_p75 DECIMAL,
    actual_date DATE,
    actual_delay INTEGER,
    in_p25_p75 BOOLEAN,
    created_at TIMESTAMP
);

-- Calibration query: P25-P75 should contain ~50% of actuals
SELECT 
    forecast_week,
    COUNT(*) as total,
    SUM(CASE WHEN in_p25_p75 THEN 1 ELSE 0 END) as in_range,
    SUM(CASE WHEN in_p25_p75 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as calibration_pct
FROM forecast_backtests
GROUP BY forecast_week;
```

---

## Phase 5: CFO Weekly Cash Meeting OS
**Goal:** Gitto becomes the meeting, not a dashboard.

### 5.1 Meeting Mode Agenda
1. **Cash Today** - Bank truth balances
2. **13-Week Runway** - Base + downside scenarios
3. **Red Weeks** - Weeks below threshold
4. **Variance Analysis** - Drivers since last snapshot
5. **Top Risks** - Largest uncertain items
6. **Actions + Owners** - Assigned tasks with expected impact
7. **Last Week Review** - Actions taken → realized impact

### 5.2 Action Loop
```python
class TreasuryAction:
    id: int
    snapshot_id: int
    action_type: str  # 'collection_push', 'ap_hold', 'ap_release', 'revolver_draw', 'factoring'
    target_id: int  # invoice_id or vendor_bill_id
    expected_impact: Decimal
    expected_date: date
    owner_id: int
    status: str  # 'proposed', 'approved', 'executed', 'realized'
    realized_impact: Optional[Decimal]
    realized_date: Optional[date]
```

### 5.3 Weekly Cash Pack Export
- Auto-generated PDF with all meeting sections
- Version-controlled per snapshot
- Email distribution to leadership

---

## Phase 6: Enterprise Readiness
**Goal:** Procurement + security review doesn't kill you.

### 6.1 Multi-Tenant Isolation
- Row-level security on all tables
- `tenant_id` on every model
- Connection pool per tenant

### 6.2 RBAC
```python
ROLES = {
    'cfo': ['view_all', 'lock_snapshot', 'approve_actions', 'manage_scenarios'],
    'fpa': ['view_all', 'create_scenarios', 'propose_actions'],
    'treasury': ['view_own_entity', 'manage_matches', 'execute_actions'],
    'analyst': ['view_own_entity', 'view_forecasts'],
    'auditor': ['view_all', 'view_audit_logs', 'export_data'],
}
```

### 6.3 Secrets Management
- No plaintext credentials in DB
- Environment variable retrieval
- AWS Secrets Manager / HashiCorp Vault integration

### 6.4 SSO + SCIM
- SAML 2.0 / OIDC integration
- User provisioning via SCIM

### 6.5 Observability
- Structured logging with correlation IDs
- Metrics (sync latency, match rate, forecast accuracy)
- Alerts on data drift, stale sources, failed syncs

---

## Test Strategy (Proving It Works)

### Invariant Tests
- [ ] Cash math: close = open + inflows - outflows
- [ ] Drilldown sums match totals
- [ ] Allocation conservation: sum(allocations) == txn_amount
- [ ] Missing FX never silent (routes to Unknown)
- [ ] Locked snapshots are immutable

### State Machine Tests
- [ ] upload → reconcile → lock → compare → scenario → lock

### Metamorphic Tests
- [ ] Shuffle rows → same result
- [ ] Duplicate import → idempotent
- [ ] Scale amounts → proportional output

### Chaos Tests
- [ ] Missing bank day
- [ ] Duplicate statements
- [ ] Partial sync failures

### Performance Tests
- [ ] Reconciliation is O(n*k) not O(n*m)
- [ ] 100K invoices loads in < 5s

---

## Implementation Priority

### Month 1: Foundation
1. Connector SDK base classes
2. MT940/BAI2 bank parsers
3. Dataset versioning tables
4. Data freshness dashboard

### Month 2: Reconciliation
1. Matching engine with indexing
2. Many-to-many allocations
3. Exception workflow
4. Cash Explained % KPI

### Month 3: Forecasting
1. Segment hierarchy with fallbacks
2. Recency weighting
3. Backtesting infrastructure
4. Calibration metrics

### Month 4: Enterprise
1. RBAC implementation
2. Audit log coverage
3. SSO integration
4. Meeting Mode UI

---

## Next Immediate Steps

1. **Create Connector SDK base classes** (today)
2. **Add MT940 bank statement parser** (this week)
3. **Implement Dataset/SyncRun tables** (this week)
4. **Build data freshness monitoring** (next week)

This transforms Gitto from "demo product" to "enterprise-ready."




