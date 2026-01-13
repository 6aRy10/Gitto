# Gitto - CFO Cash Command Center

> Enterprise-grade cash flow forecasting and reconciliation platform with probabilistic modeling, automated reconciliation, and workflow management.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16.1-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

## 🎯 Overview

Gitto is a comprehensive treasury management platform that provides:

- **Probabilistic Cash Forecasting** with CQR-style conformal prediction
- **Automated Reconciliation** with many-to-many allocation and conservation proofs
- **Workflow Management** with state machines and meeting mode
- **Trust Reports** with amount-weighted metrics for CFO visibility
- **Multi-Entity Support** with intercompany transfer handling
- **Bank Statement Parsing** (MT940, BAI2, camt.053 ISO 20022)

## 🏗️ Architecture

```
Gitto/
├── backend/              # FastAPI backend
│   ├── main.py          # API endpoints
│   ├── models.py        # SQLAlchemy models
│   ├── probabilistic_forecast_service_enhanced.py
│   ├── reconciliation_service_v2_enhanced.py
│   ├── snapshot_state_machine_enhanced.py
│   ├── trust_report_service.py
│   └── tests/           # Comprehensive test suite
│
├── src/                 # Next.js frontend
│   ├── app/             # App router pages
│   ├── components/      # React components
│   └── lib/             # Utilities & API client
│
├── fixtures/            # Synthetic data generator
│   ├── generate_synthetic_data_enhanced.py
│   ├── bank_format_validator.py
│   └── golden_dataset_manifest.json
│
└── docs/               # Documentation
    ├── ARCHITECTURE.md
    ├── API.md
    └── TESTING.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (or SQLite for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/gitto.git
   cd gitto
   ```

2. **Backend Setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **Frontend Setup**
   ```bash
   npm install
   npm run dev
   ```

4. **Generate Test Data** (Optional)
   ```bash
   python fixtures/generate_synthetic_data_enhanced.py
   ```

## 📚 Key Features

### 1. Probabilistic Forecasting

- **Hierarchical Fallback**: customer+country+terms → customer+country → customer → country → global
- **Recency Weighting**: Last 90 days weighted higher
- **Outlier Robustness**: Winsorized delays
- **CQR-Style Conformal Prediction**: Calibrated P25/P50/P75/P90 distributions
- **Regime Shift Detection**: Alerts when payment behavior changes

### 2. Reconciliation Engine

- **Blocking Indexes**: Efficient candidate generation (by ref, amount, counterparty, date)
- **Embedding Similarity**: TF-IDF cosine similarity for suggestions
- **Constrained Solver**: Many-to-many allocation with LP optimization
- **Conservation Proofs**: Verifies sum(allocations) + fees + writeoffs == txn_amount
- **No-Overmatch Invariants**: Never allocates beyond open_amount

### 3. Workflow Management

- **State Machine**: DRAFT → READY_FOR_REVIEW → LOCKED
- **Amount-Weighted Gates**: € exposure thresholds (not row counts)
- **CFO Override**: Explicit acknowledgment required
- **Acknowledged Exceptions**: Lock with unresolved but reviewed exceptions
- **Database Immutability**: Triggers prevent modification of locked snapshots

### 4. Trust Reports

- **Cash Explained %** (amount-weighted)
- **Unknown Exposure €**
- **Missing FX Exposure €**
- **Data Freshness** (hours since last update)
- **Calibration Coverage** (amount-weighted)
- **Suggested Matches Pending**
- **Lock Eligibility** with reasons

## 🧪 Testing

### Run All Tests

```bash
# Backend tests
pytest backend/tests/ -v

# Specific test suites
pytest backend/tests/test_reconciliation_conservation_hard.py -v
pytest backend/tests/test_forecast_calibration_hard.py -v
pytest backend/tests/test_snapshot_immutability_comprehensive.py -v
pytest backend/tests/test_metamorphic.py -v

# Round-trip validation
pytest fixtures/test_bank_format_roundtrip.py -v

# Golden manifest assertions
pytest fixtures/test_golden_manifest_assertions.py -v
```

### Test Coverage

- ✅ **Proof Tests**: Fail when invariants are broken
- ✅ **Metamorphic Tests**: Verify deterministic behavior
- ✅ **Round-Trip Validation**: Generate → validate → parse → compare
- ✅ **Conservation Proofs**: Mathematical verification
- ✅ **Immutability Tests**: Database-level enforcement

## 📖 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Testing Guide](docs/TESTING.md)
- [Enterprise Fixes](docs/ENTERPRISE_READY_FIXES.md)
- [Verification Protocol](docs/VERIFICATION_PROTOCOL.md)

## 🔒 Enterprise Features

### Data Quality

- **Format Validation**: MT940/BAI2/camt.053 validated against specs
- **Chaos Mode**: Duplicate imports, missing days, timezone shifts, reversals
- **Ground Truth**: Canonical transactions alongside raw statements
- **Amount-Weighted Metrics**: € exposure, not row counts

### Model Quality

- **CQR-Style Calibration**: True conformal prediction (not residual adjustment)
- **Amount-Weighted Coverage**: Big invoices matter more
- **Monotonic Quantiles**: P25 ≤ P50 ≤ P75 ≤ P90 enforced
- **Regime Shift Alarms**: Detects behavior changes

### System Integrity

- **Database Immutability**: Triggers prevent modification of locked snapshots
- **Conservation Proofs**: Mathematical verification of allocations
- **No-Overmatch Invariants**: Never allocates beyond open_amount
- **CFO Override**: Explicit acknowledgment required

## 🛠️ Development

### Project Structure

```
backend/
├── main.py                          # FastAPI app
├── models.py                         # SQLAlchemy models
├── probabilistic_forecast_service_enhanced.py
├── reconciliation_service_v2_enhanced.py
├── snapshot_state_machine_enhanced.py
├── trust_report_service.py
├── db_constraints.py                 # Database immutability
└── tests/
    ├── test_reconciliation_conservation_hard.py
    ├── test_forecast_calibration_hard.py
    ├── test_snapshot_immutability_comprehensive.py
    └── test_metamorphic.py

src/
├── app/                              # Next.js pages
│   ├── page.tsx                      # Landing page
│   ├── app/                          # Dashboard
│   └── components/                   # React components
└── lib/
    └── api.ts                        # API client

fixtures/
├── generate_synthetic_data_enhanced.py
├── bank_format_validator.py
├── test_bank_format_roundtrip.py
├── test_golden_manifest_assertions.py
└── golden_dataset_manifest.json
```

## 📊 API Endpoints

### Core Endpoints

- `GET /snapshots/{id}` - Get snapshot details
- `POST /snapshots/{id}/lock` - Lock snapshot (with CFO override)
- `GET /snapshots/{id}/trust-report` - Generate trust report
- `POST /forecast/run` - Run probabilistic forecast
- `POST /reconciliation/run` - Run reconciliation
- `GET /forecast/diagnostics` - Get calibration diagnostics

See [API.md](docs/API.md) for complete reference.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

Proprietary - All rights reserved

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Frontend powered by [Next.js](https://nextjs.org/)
- UI components from [Radix UI](https://www.radix-ui.com/)

## 📧 Contact

For questions or support, please open an issue or contact the development team.

---

**Status**: Production-ready with comprehensive test coverage and enterprise-grade features.
