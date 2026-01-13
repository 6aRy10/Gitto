# Reconciliation Service V2 Implementation

## Overview

Rebuilt reconciliation system with:
- **Blocking indexes** for O(n*k) candidate generation (not O(n*m))
- **Embedding similarity** for suggested matches (never auto-applies)
- **Constrained solver** for many-to-many allocation with proper constraints
- **Performance optimized** for 50k+ transactions

## Architecture

### 1. Blocking Index System

**Purpose**: Efficient candidate generation using multi-block filtering.

**Blocks**:
- **Extracted Invoice Refs**: Regex patterns extract invoice numbers from transaction references
- **Amount Buckets**: Rounded to configurable bucket size (default: 100)
- **Counterparty Key**: Normalized counterparty names for matching
- **Date Window**: Week-based indexing with adjacent week tolerance

**Performance**: O(n*k) where k is average candidates per block (typically < 10)

### 2. Embedding Similarity Matcher

**Purpose**: Generate suggested matches using semantic similarity.

**Implementation**:
- Uses TF-IDF vectors and cosine similarity
- Only used for suggestion queue (never auto-applies)
- Requires approval before applying

**Fallback**: If sklearn not available, uses simple text matching

### 3. Constrained Allocation Solver

**Purpose**: Solve many-to-many allocation with proper constraints.

**Constraints**:
1. `sum(allocations) + fees + writeoffs = txn_amount`
2. `allocation[i] <= open_amount[i]` for each invoice
3. `allocation[i] >= 0` for each invoice

**Solver**:
- Uses `scipy.optimize.linprog` for linear programming
- Falls back to greedy allocation if scipy unavailable
- Handles fees and writeoffs explicitly

**Objective**: Maximize total allocation (prefer larger matches)

## API Changes

### POST `/entities/{entity_id}/reconcile?use_v2=true`

Use new reconciliation service V2.

**Response**:
```json
{
  "deterministic": 1500,
  "rule_based": 800,
  "suggested": 200,
  "manual": 100,
  "many_to_many": 50,
  "matches": [...]
}
```

### Async Reconciliation

The async reconciliation endpoint (`/async/reconciliation`) now uses V2 by default.

## Performance Tests

**Location**: `backend/tests/test_reconciliation_performance.py`

**Tests**:
1. `test_reconciliation_performance`: 50k txns + 200k invoices, < 60s threshold
2. `test_blocking_index_performance`: Index build and query performance
3. `test_constrained_solver_performance`: Solver performance with 100 candidates
4. `test_many_to_many_allocation_constraints`: Validates constraint satisfaction
5. `test_embedding_similarity_suggestions`: Ensures suggestions never auto-apply

**Run tests**:
```bash
pytest backend/tests/test_reconciliation_performance.py -v
```

## Key Improvements

### Performance
- **Blocking indexes**: Reduces candidate set from O(n) to O(k) where k << n
- **Set intersection**: Multi-block filtering uses efficient set operations
- **Bulk operations**: Minimizes database queries

### Accuracy
- **Embedding similarity**: Better semantic matching for noisy references
- **Constrained solver**: Optimal allocation respecting all constraints
- **Open amount tracking**: Prevents over-allocation

### Safety
- **Suggested matches never auto-apply**: Requires explicit approval
- **Constraint validation**: Solver ensures allocations are valid
- **Fee/writeoff handling**: Explicitly tracked and allocated

## Migration

The new service is opt-in via `use_v2=true` parameter. Old service remains as fallback.

To migrate:
1. Test with `use_v2=true` on staging
2. Monitor performance and accuracy
3. Switch default to V2 once validated
4. Deprecate old service

## Dependencies

- `scipy>=1.16.3` (for constrained solver)
- `scikit-learn>=1.8.0` (for embedding similarity)

Both are already in `requirements.txt`.

## Example Usage

```python
from reconciliation_service_v2 import ReconciliationServiceV2

service = ReconciliationServiceV2(db)
results = service.reconcile_entity(entity_id)

print(f"Deterministic: {results['deterministic']}")
print(f"Rule-based: {results['rule_based']}")
print(f"Suggested: {results['suggested']}")
print(f"Many-to-many: {results['many_to_many']}")
```


