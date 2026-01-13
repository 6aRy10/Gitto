# Gitto Architecture

## System Overview

Gitto is built as a modern full-stack application with a FastAPI backend and Next.js frontend.

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database interactions
- **Pydantic**: Data validation and serialization
- **NumPy/Pandas**: Data processing and statistical analysis
- **SciPy**: Optimization (linear programming for reconciliation)

### Frontend
- **Next.js 16**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first styling
- **Radix UI**: Accessible component primitives
- **Recharts**: Data visualization

### Database
- **SQLite**: Development (can be swapped for PostgreSQL)
- **SQLAlchemy Migrations**: Schema versioning

## Core Components

### 1. Probabilistic Forecast Service

**File**: `backend/probabilistic_forecast_service_enhanced.py`

- Hierarchical fallback strategy
- Recency weighting (90-day half-life)
- Winsorization for outlier robustness
- CQR-style conformal prediction
- Regime shift detection

### 2. Reconciliation Service

**File**: `backend/reconciliation_service_v2_enhanced.py`

- Blocking indexes for candidate generation
- Embedding similarity for suggestions
- Constrained LP solver for many-to-many allocation
- Conservation proofs
- No-overmatch invariants

### 3. Snapshot State Machine

**File**: `backend/snapshot_state_machine_enhanced.py`

- State transitions: DRAFT → READY_FOR_REVIEW → LOCKED
- Amount-weighted gate checks
- CFO override with acknowledgment
- Acknowledged exceptions state

### 4. Trust Report Service

**File**: `backend/trust_report_service.py`

- Cash explained % (amount-weighted)
- Unknown exposure €
- Missing FX exposure €
- Data freshness metrics
- Calibration coverage
- Lock eligibility

## Data Flow

```
User Input → Frontend (Next.js)
    ↓
API Request → Backend (FastAPI)
    ↓
Business Logic → Services
    ↓
Database (SQLAlchemy)
    ↓
Response → Frontend
    ↓
UI Update
```

## Database Schema

Key tables:
- `snapshots`: Financial snapshots
- `invoices`: AR invoices
- `vendor_bills`: AP bills
- `bank_transactions`: Bank statement transactions
- `reconciliation_table`: Matches between transactions and invoices
- `weekly_fx_rates`: FX rate data
- `segment_delay_stats`: Forecast model statistics
- `calibration_stats`: Model calibration metrics
- `workflow_exceptions`: Exception tracking
- `workflow_scenarios`: What-if scenarios
- `workflow_actions`: Treasury actions

## Security

- CORS middleware configured
- Database immutability via triggers
- Application-level snapshot protection
- CFO override requires explicit acknowledgment

## Testing Strategy

- **Unit Tests**: Individual service methods
- **Integration Tests**: End-to-end workflows
- **Proof Tests**: Invariant verification
- **Metamorphic Tests**: Deterministic behavior
- **Round-Trip Tests**: Format validation

## Deployment

### Development
```bash
# Backend
cd backend
python -m uvicorn main:app --reload

# Frontend
npm run dev
```

### Production
- Backend: Deploy FastAPI with uvicorn/gunicorn
- Frontend: Build Next.js static export or SSR
- Database: PostgreSQL recommended for production

## Performance Considerations

- LP solver only runs on small candidate sets (≤50)
- Reconciliation runs as background job
- Database indexes on frequently queried fields
- Caching for FX rates and segment statistics
