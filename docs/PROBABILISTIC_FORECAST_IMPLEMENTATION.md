# Probabilistic Forecast Implementation

## Overview

Replaced the simple percentile-from-delays forecasting model with a sophisticated probabilistic model using conformal prediction for calibrated distributions.

## Key Features

### 1. Hierarchical Fallback
- **Order**: customer+country+terms → customer+country → customer → country → global
- **Minimum Sample Size**: N ≥ 15 required for segment to be used
- **Fallback Logic**: Automatically falls back to next level if insufficient data

### 2. Recency Weighting
- **Half-life**: 90 days (configurable)
- **Weight Formula**: `weight = 2^(-age_days / 90)`
- **Effect**: Recent payments (last 90 days) have exponentially higher weight
- **Purpose**: Adapts to regime shifts and recent behavior changes

### 3. Outlier Robustness
- **Winsorization**: Caps delays at P99 percentile
- **Purpose**: Prevents single extreme outliers from skewing distributions
- **Applied**: Before recency weighting and percentile calculation

### 4. Calibrated Distributions
- **Percentiles**: P25, P50, P75, P90
- **Method**: Conformal prediction with 5-fold cross-validation
- **Calibration**: Adjusts percentiles to achieve proper coverage
- **Target Coverage**: 
  - P25-P75 interval: ~50% of actuals
  - P50: ~50% of actuals
  - P75: ~75% of actuals
  - P90: ~90% of actuals

### 5. Model Artifacts Storage
- **SegmentDelayStats**: Enhanced segment statistics per snapshot
  - Sample size, percentiles (P25/P50/P75/P90), mean, std, min, max
  - Flags for recency weighting and winsorization
- **CalibrationStats**: Calibration metrics per segment
  - Coverage metrics for each percentile
  - Calibration error (deviation from expected coverage)
  - Backtest split information

## Implementation Details

### New Service: `ProbabilisticForecastService`

**Location**: `backend/probabilistic_forecast_service.py`

**Key Methods**:
- `run_forecast(snapshot_id)`: Main forecast execution
- `_build_segment_statistics()`: Builds hierarchical segment stats with recency weighting
- `_calibrate_with_conformal_prediction()`: Calibrates distributions using split-conformal prediction
- `_apply_predictions()`: Applies predictions to open invoices using hierarchical fallback
- `get_diagnostics()`: Returns diagnostic metrics

### Database Models

#### Enhanced `SegmentDelay` Model
```python
class SegmentDelay(Base):
    # Existing fields
    segment_type, segment_key, count
    median_delay, p25_delay, p75_delay, p90_delay, std_delay
    
    # New fields
    mean_delay, min_delay, max_delay
    recency_weighted, winsorized
```

#### New `CalibrationStats` Model
```python
class CalibrationStats(Base):
    snapshot_id, segment_type, segment_key
    coverage_p25, coverage_p50, coverage_p75, coverage_p90
    calibration_error, sample_size, backtest_splits
    calibrated_at
```

### API Endpoints

#### GET `/forecast/diagnostics?snapshot_id=...`

Returns comprehensive forecast diagnostics:

```json
{
  "snapshot_id": 1,
  "total_segments": 15,
  "segments_with_sufficient_data": 12,
  "segments_with_insufficient_data": 3,
  "calibration": {
    "average_coverage_p25_p75": 0.52,
    "average_calibration_error": 0.02,
    "expected_coverage": 0.50,
    "calibrated_segments": 12
  },
  "sample_sizes": {
    "minimum": 5,
    "maximum": 150,
    "median": 45.0,
    "minimum_required": 15
  },
  "drift_warnings": [
    {
      "segment": "customer+country::Acme Corp+US",
      "issue": "coverage_out_of_range",
      "coverage_p25_p75": 0.35,
      "expected": 0.50,
      "deviation": 0.15
    }
  ],
  "insufficient_data_segments": [
    {
      "segment_type": "customer+country+terms",
      "segment_key": "Acme Corp+US+Net 30",
      "sample_size": 8,
      "minimum_required": 15
    }
  ],
  "model_config": {
    "recency_half_life_days": 90,
    "winsorize_percentile": 99.0,
    "min_sample_size": 15,
    "hierarchy_levels": [
      ["customer", "country", "terms_of_payment"],
      ["customer", "country"],
      ["customer"],
      ["country"],
      []
    ]
  }
}
```

## Migration from Old Model

The new probabilistic model is automatically used when:
1. A snapshot is created/updated
2. Forecast is run via `/async/forecast` endpoint

**Fallback**: If the new model fails, it automatically falls back to the old `run_forecast_model()` function.

## Configuration

Model parameters can be adjusted in `ProbabilisticForecastService.__init__()`:

```python
self.MIN_SAMPLE_SIZE = 15
self.RECENCY_HALF_LIFE_DAYS = 90
self.WINSORIZE_PERCENTILE = 99.0
self.HIERARCHY_LEVELS = [
    ['customer', 'country', 'terms_of_payment'],
    ['customer', 'country'],
    ['customer'],
    ['country'],
    []  # Global fallback
]
```

## Diagnostics Usage

### Check Forecast Quality
```bash
GET /forecast/diagnostics?snapshot_id=1
```

### Key Metrics to Monitor:
1. **Coverage P25-P75**: Should be ~0.50 (50% of actuals within P25-P75 interval)
2. **Calibration Error**: Should be < 0.10 (10% deviation from expected)
3. **Sample Sizes**: Segments with < 15 samples will use fallback
4. **Drift Warnings**: Indicates segments with poor calibration

### Drift Warning Interpretation:
- **coverage_out_of_range**: P25-P75 coverage is < 40% or > 60%
  - **Action**: Review segment data quality, consider regime shift
- **high_calibration_error**: Calibration error > 10%
  - **Action**: Segment may need more data or different hierarchy level

## Benefits Over Old Model

1. **Calibrated Predictions**: Percentiles are calibrated to achieve proper coverage
2. **Recency Adaptation**: Automatically adapts to recent behavior changes
3. **Outlier Robustness**: Winsorization prevents extreme outliers from skewing results
4. **Diagnostics**: Comprehensive diagnostics for model quality assessment
5. **Transparency**: All model artifacts stored per snapshot for audit trail

## Testing

The new model maintains backward compatibility:
- Existing forecast aggregation endpoints work unchanged
- Old model available as fallback
- New diagnostics endpoint provides additional insights

## Future Enhancements

1. Add P90 predictions to Invoice model (`confidence_p90` field)
2. Real-time drift detection alerts
3. Automatic hierarchy level optimization
4. Segment-specific recency half-lives
5. Multi-entity hierarchical learning


