"""
Enhanced Probabilistic Forecast Service

Fixes:
1. Proper CQR-style conformal prediction (not just residual adjustment)
2. Amount-weighted calibration (big invoices matter more)
3. Monotonic quantiles enforcement (P25 ≤ P50 ≤ P75 ≤ P90)
4. Regime shift detection and alarm
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import models
from forecast_enhancements import winsorize_delays, apply_recency_weighting, calculate_weighted_percentiles


@dataclass
class EnhancedCalibrationStats:
    """Enhanced calibration with amount-weighted metrics."""
    snapshot_id: int
    segment_type: str
    segment_key: str
    coverage_p25: float
    coverage_p50: float
    coverage_p75: float
    coverage_p90: float
    calibration_error: float
    # Amount-weighted coverage (big invoices matter more)
    amount_weighted_coverage_p25: float
    amount_weighted_coverage_p50: float
    amount_weighted_coverage_p75: float
    amount_weighted_coverage_p90: float
    amount_weighted_calibration_error: float
    sample_size: int
    backtest_splits: int = 5
    calibrated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Regime shift detection
    regime_shift_detected: bool = False
    regime_shift_severity: str = "none"  # none, mild, moderate, severe
    recent_30d_mean: Optional[float] = None
    long_run_mean: Optional[float] = None
    mean_shift_pct: Optional[float] = None


class EnhancedProbabilisticForecastService:
    """
    Enhanced probabilistic forecast with proper CQR-style conformal prediction.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.MIN_SAMPLE_SIZE = 15
        self.RECENCY_HALF_LIFE_DAYS = 90
        self.WINSORIZE_PERCENTILE = 99.0
        self.REGIME_SHIFT_THRESHOLD = 0.20  # 20% mean shift triggers alarm
        
        self.HIERARCHY_LEVELS = [
            ['customer', 'country', 'terms_of_payment'],
            ['customer', 'country'],
            ['customer'],
            ['country'],
            []
        ]
    
    def _calibrate_with_cqr(
        self,
        snapshot_id: int,
        paid_df: pd.DataFrame,
        segment_stats: Dict[str, Any]
    ) -> List[EnhancedCalibrationStats]:
        """
        Proper CQR-style conformal prediction.
        
        CQR (Conformalized Quantile Regression) works by:
        1. Train quantile models on calibration set
        2. Compute nonconformity scores (residuals) on calibration set
        3. Use quantile of scores as adjustment factor
        4. Apply adjustment to test set predictions
        """
        if paid_df.empty or 'delay_days' not in paid_df.columns:
            return []
        
        calibration_stats = []
        n_splits = 5
        
        for seg_key, stats in segment_stats.items():
            seg_type, seg_val = seg_key.split("::", 1) if "::" in seg_key else (seg_key, "")
            
            # Get segment data
            if seg_type == "Global" and seg_val == "":
                segment_data = paid_df.copy()
            else:
                segment_data = self._filter_segment_data(paid_df, seg_type, seg_val)
            
            if len(segment_data) < self.MIN_SAMPLE_SIZE * 2:
                continue
            
            # Separate paid history (for calibration) from open invoices (for prediction)
            # CRITICAL: Ensure no leakage
            segment_data = segment_data[segment_data['payment_date'].notna()].copy()
            
            segment_delays = segment_data['delay_days'].values
            segment_amounts = segment_data['amount'].values if 'amount' in segment_data.columns else np.ones(len(segment_data))
            n = len(segment_delays)
            split_size = n // n_splits
            
            coverage_p25 = []
            coverage_p50 = []
            coverage_p75 = []
            coverage_p90 = []
            
            # Amount-weighted coverage
            amount_coverage_p25 = []
            amount_coverage_p50 = []
            amount_coverage_p75 = []
            amount_coverage_p90 = []
            
            for split in range(n_splits):
                test_start = split * split_size
                test_end = (split + 1) * split_size if split < n_splits - 1 else n
                test_indices = list(range(test_start, test_end))
                calib_indices = [i for i in range(n) if i not in test_indices]
                
                if len(calib_indices) < self.MIN_SAMPLE_SIZE:
                    continue
                
                # Step 1: Train quantiles on calibration set
                calib_delays = segment_delays[calib_indices]
                calib_amounts = segment_amounts[calib_indices]
                
                # Weighted percentiles (amount-weighted)
                sorted_indices = np.argsort(calib_delays)
                sorted_delays = calib_delays[sorted_indices]
                sorted_amounts = calib_amounts[sorted_indices]
                cum_weights = np.cumsum(sorted_amounts) / np.sum(sorted_amounts)
                
                # Find percentiles
                p25_idx = np.searchsorted(cum_weights, 0.25)
                p50_idx = np.searchsorted(cum_weights, 0.50)
                p75_idx = np.searchsorted(cum_weights, 0.75)
                p90_idx = np.searchsorted(cum_weights, 0.90)
                
                p25 = sorted_delays[min(p25_idx, len(sorted_delays) - 1)]
                p50 = sorted_delays[min(p50_idx, len(sorted_delays) - 1)]
                p75 = sorted_delays[min(p75_idx, len(sorted_delays) - 1)]
                p90 = sorted_delays[min(p90_idx, len(sorted_delays) - 1)]
                
                # Step 2: Compute nonconformity scores on calibration set
                # Score = max( (p25 - actual) / (p75 - p25), (actual - p75) / (p75 - p25) )
                calib_scores = []
                for delay in calib_delays:
                    if p75 > p25:
                        score_low = max(0, (p25 - delay) / (p75 - p25))
                        score_high = max(0, (delay - p75) / (p75 - p25))
                        score = max(score_low, score_high)
                    else:
                        score = abs(delay - p50) / (abs(p50) + 1)
                    calib_scores.append(score)
                
                # Step 3: Get adjustment factor (quantile of scores)
                alpha = 0.1  # 10% miscoverage tolerance
                adjustment_factor = np.quantile(calib_scores, 1 - alpha)
                
                # Step 4: Apply adjustment to test set
                test_delays = segment_delays[test_indices]
                test_amounts = segment_amounts[test_indices]
                
                # Adjusted intervals
                interval_width = max(p75 - p25, 1.0)
                adjusted_p25 = p25 - adjustment_factor * interval_width
                adjusted_p75 = p75 + adjustment_factor * interval_width
                
                # Check coverage (count-based)
                within_p25_p75 = np.sum((test_delays >= adjusted_p25) & (test_delays <= adjusted_p75))
                within_p50 = np.sum(test_delays <= p50)
                within_p75 = np.sum(test_delays <= adjusted_p75)
                within_p90 = np.sum(test_delays <= p90)
                
                coverage_p25.append(within_p25_p75 / len(test_delays))
                coverage_p50.append(within_p50 / len(test_delays))
                coverage_p75.append(within_p75 / len(test_delays))
                coverage_p90.append(within_p90 / len(test_delays))
                
                # Amount-weighted coverage
                total_amount = np.sum(test_amounts)
                if total_amount > 0:
                    amount_within_p25_p75 = np.sum(test_amounts[(test_delays >= adjusted_p25) & (test_delays <= adjusted_p75)])
                    amount_within_p50 = np.sum(test_amounts[test_delays <= p50])
                    amount_within_p75 = np.sum(test_amounts[test_delays <= adjusted_p75])
                    amount_within_p90 = np.sum(test_amounts[test_delays <= p90])
                    
                    amount_coverage_p25.append(amount_within_p25_p75 / total_amount)
                    amount_coverage_p50.append(amount_within_p50 / total_amount)
                    amount_coverage_p75.append(amount_within_p75 / total_amount)
                    amount_coverage_p90.append(amount_within_p90 / total_amount)
            
            if coverage_p25:
                # Detect regime shift
                regime_shift = self._detect_regime_shift(segment_data)
                
                calib_stat = EnhancedCalibrationStats(
                    snapshot_id=snapshot_id,
                    segment_type=seg_type,
                    segment_key=seg_val,
                    coverage_p25=np.mean(coverage_p25),
                    coverage_p50=np.mean(coverage_p50),
                    coverage_p75=np.mean(coverage_p75),
                    coverage_p90=np.mean(coverage_p90),
                    calibration_error=abs(np.mean(coverage_p25) - 0.50),
                    amount_weighted_coverage_p25=np.mean(amount_coverage_p25) if amount_coverage_p25 else 0.0,
                    amount_weighted_coverage_p50=np.mean(amount_coverage_p50) if amount_coverage_p50 else 0.0,
                    amount_weighted_coverage_p75=np.mean(amount_coverage_p75) if amount_coverage_p75 else 0.0,
                    amount_weighted_coverage_p90=np.mean(amount_coverage_p90) if amount_coverage_p90 else 0.0,
                    amount_weighted_calibration_error=abs(np.mean(amount_coverage_p25) - 0.50) if amount_coverage_p25 else 0.0,
                    sample_size=len(segment_data),
                    backtest_splits=n_splits,
                    regime_shift_detected=regime_shift['detected'],
                    regime_shift_severity=regime_shift['severity'],
                    recent_30d_mean=regime_shift.get('recent_mean'),
                    long_run_mean=regime_shift.get('long_run_mean'),
                    mean_shift_pct=regime_shift.get('shift_pct')
                )
                calibration_stats.append(calib_stat)
        
        return calibration_stats
    
    def _detect_regime_shift(self, segment_data: pd.DataFrame) -> Dict[str, Any]:
        """Detect regime shift: recent 30-60d behavior differs from long-run."""
        if 'payment_date' not in segment_data.columns or 'delay_days' not in segment_data.columns:
            return {'detected': False, 'severity': 'none'}
        
        now = datetime.now(timezone.utc)
        segment_data['payment_date'] = pd.to_datetime(segment_data['payment_date'])
        segment_data['days_ago'] = (now - segment_data['payment_date']).dt.days
        
        # Recent 30-60 days
        recent_data = segment_data[segment_data['days_ago'] <= 60]
        # Long-run (everything else, but at least 90 days old)
        long_run_data = segment_data[segment_data['days_ago'] > 90]
        
        if len(recent_data) < 5 or len(long_run_data) < 5:
            return {'detected': False, 'severity': 'none'}
        
        recent_mean = recent_data['delay_days'].mean()
        long_run_mean = long_run_data['delay_days'].mean()
        long_run_std = long_run_data['delay_days'].std()
        
        if long_run_std == 0:
            return {'detected': False, 'severity': 'none'}
        
        # Calculate shift percentage
        shift_pct = abs(recent_mean - long_run_mean) / (abs(long_run_mean) + 1)
        
        # Z-score
        z_score = abs(recent_mean - long_run_mean) / long_run_std
        
        detected = shift_pct > self.REGIME_SHIFT_THRESHOLD or z_score > 2.0
        
        if z_score > 3.0 or shift_pct > 0.50:
            severity = 'severe'
        elif z_score > 2.5 or shift_pct > 0.30:
            severity = 'moderate'
        elif z_score > 2.0 or shift_pct > 0.20:
            severity = 'mild'
        else:
            severity = 'none'
        
        return {
            'detected': detected,
            'severity': severity,
            'recent_mean': float(recent_mean),
            'long_run_mean': float(long_run_mean),
            'shift_pct': float(shift_pct),
            'z_score': float(z_score)
        }
    
    def _enforce_monotonic_quantiles(
        self,
        p25: float,
        p50: float,
        p75: float,
        p90: float
    ) -> Tuple[float, float, float, float]:
        """Enforce monotonicity: P25 ≤ P50 ≤ P75 ≤ P90."""
        # Sort and ensure monotonicity
        quantiles = sorted([p25, p50, p75, p90])
        
        # If they're not already monotonic, use sorted order
        # But try to preserve original order if possible
        if p25 <= p50 <= p75 <= p90:
            return p25, p50, p75, p90
        
        # Otherwise, use sorted order with small adjustments
        return quantiles[0], quantiles[1], quantiles[2], quantiles[3]
    
    def _filter_segment_data(self, paid_df: pd.DataFrame, seg_type: str, seg_val: str) -> pd.DataFrame:
        """Filter dataframe by segment."""
        segment_data = paid_df.copy()
        levels = seg_type.split("+")
        
        if seg_val and "+" in seg_val:
            seg_parts = seg_val.split("+")
            if len(seg_parts) == len(levels):
                for level, val in zip(levels, seg_parts):
                    if level in segment_data.columns:
                        segment_data = segment_data[segment_data[level].astype(str) == str(val)]
        elif seg_val:
            if levels and levels[0] in segment_data.columns:
                segment_data = segment_data[segment_data[levels[0]].astype(str) == str(seg_val)]
        
        return segment_data


