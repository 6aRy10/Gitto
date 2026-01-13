# Changelog

All notable changes to Gitto will be documented in this file.

## [Unreleased]

### Added
- Probabilistic forecast service with CQR-style conformal prediction
- Enhanced reconciliation service with conservation proofs
- Snapshot state machine with amount-weighted gates
- Trust report service for CFO visibility
- Comprehensive test suite with proof tests, metamorphic tests, and round-trip validation
- Bank format validators (MT940, BAI2, camt.053)
- Synthetic data generator with chaos mode
- Database immutability constraints

### Changed
- Reconciliation now uses quality-based LP objective
- Forecast calibration is amount-weighted
- Gate checks use € exposure instead of row counts

### Fixed
- Conservation proofs verify sum(allocations) == txn_amount
- No-overmatch invariants prevent allocation beyond open_amount
- Monotonic quantiles enforced (P25 ≤ P50 ≤ P75 ≤ P90)
- Database triggers prevent modification of locked snapshots

## [0.1.0] - 2026-01-06

### Added
- Initial release
- Core forecasting and reconciliation functionality
- Next.js frontend
- FastAPI backend
