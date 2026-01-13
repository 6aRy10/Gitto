# Gitto API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, authentication is handled via session/user context. In production, implement JWT or OAuth2.

## Endpoints

### Snapshots

#### Get Snapshot
```http
GET /snapshots/{snapshot_id}
```

#### Lock Snapshot
```http
POST /snapshots/{snapshot_id}/lock
Content-Type: application/json

{
  "lock_type": "Meeting",
  "cfo_override": false,
  "override_acknowledgment": null
}
```

#### Get Trust Report
```http
GET /snapshots/{snapshot_id}/trust-report
```

Returns:
```json
{
  "snapshot_id": 1,
  "cash_explained": {
    "explained_pct": 95.5,
    "unknown_pct": 4.5,
    "explained_amount": 1000000.0,
    "unknown_amount": 45000.0
  },
  "unknown_exposure": {
    "unknown_amount": 45000.0,
    "unknown_pct": 4.5,
    "kpi_target_met": true
  },
  "missing_fx_exposure": {
    "exposure_amount": 50000.0,
    "exposure_pct": 3.2,
    "threshold_met": true
  },
  "data_freshness": {
    "freshness_hours": 12.5,
    "freshness_status": "fresh"
  },
  "calibration_coverage": {
    "amount_weighted_coverage_p25_p75": 0.48,
    "well_calibrated": true
  },
  "suggested_matches_pending": {
    "pending_count": 5,
    "pending_amount": 25000.0
  },
  "lock_eligibility": {
    "eligible": true,
    "reasons": []
  },
  "overall_trust_score": {
    "score": 92.5,
    "level": "high"
  }
}
```

### Forecasting

#### Run Forecast
```http
POST /forecast/run
Content-Type: application/json

{
  "snapshot_id": 1
}
```

#### Get Diagnostics
```http
GET /forecast/diagnostics?snapshot_id=1
```

### Reconciliation

#### Run Reconciliation
```http
POST /reconciliation/run
Content-Type: application/json

{
  "snapshot_id": 1
}
```

#### Verify Conservation
```http
POST /reconciliation/verify-conservation
Content-Type: application/json

{
  "transaction_id": 123,
  "solution": {
    "allocations": {1: 10000.0},
    "fees": 50.0,
    "writeoffs": 0.0
  }
}
```

### Workflow

#### Get Exceptions
```http
GET /snapshots/{snapshot_id}/exceptions?status=open
```

#### Acknowledge Exceptions
```http
POST /snapshots/{snapshot_id}/acknowledge-exceptions
Content-Type: application/json

{
  "exception_ids": [1, 2, 3],
  "acknowledgment_note": "Reviewed and accepted for weekly meeting"
}
```

## Error Responses

```json
{
  "detail": "Error message here"
}
```

Status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error
