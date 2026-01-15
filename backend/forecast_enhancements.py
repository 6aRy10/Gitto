"""
Forecast Model Enhancements
- Outlier handling (winsorization/capping at P99)
- Regime shift handling (recency weighting, change detection)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


def winsorize_delays(delays: pd.Series, percentile: float = 99.0) -> pd.Series:
    """
    Winsorize delay days at specified percentile to handle outliers.
    Caps extreme values at P99 to prevent single outliers from skewing distributions.
    """
    if delays.empty:
        return delays
    
    cap_value = np.percentile(delays, percentile)
    floor_value = np.percentile(delays, 100 - percentile)
    
    # Cap at P99 and floor at P1
    winsorized = delays.clip(lower=floor_value, upper=cap_value)
    
    return winsorized


def detect_regime_shift(
    delays_by_period: Dict[str, pd.Series],
    threshold_std_devs: float = 2.0
) -> Dict[str, bool]:
    """
    Detect regime shifts in payment behavior.
    Compares recent periods to historical baseline.
    
    Returns: Dict mapping period to whether shift detected
    """
    if not delays_by_period:
        return {}
    
    # Calculate overall baseline
    all_delays = pd.concat(delays_by_period.values())
    baseline_mean = all_delays.mean()
    baseline_std = all_delays.std()
    
    shifts = {}
    for period, delays in delays_by_period.items():
        if len(delays) < 5:  # Need minimum data
            shifts[period] = False
            continue
        
        period_mean = delays.mean()
        z_score = abs((period_mean - baseline_mean) / baseline_std) if baseline_std > 0 else 0
        
        # Shift detected if mean differs by more than threshold standard deviations
        shifts[period] = z_score > threshold_std_devs
    
    return shifts


def apply_recency_weighting(
    delays: pd.Series,
    dates: pd.Series,
    half_life_days: int = 90
) -> pd.Series:
    """
    Apply exponential decay weighting to historical delays.
    More recent payments have higher weight in distribution calculation.
    
    half_life_days: Number of days for weight to decay to 50%
    """
    if delays.empty or dates.empty:
        return delays
    
    # Calculate age of each payment
    now = datetime.utcnow()
    ages_days = (now - pd.to_datetime(dates)).dt.days
    
    # Exponential decay: weight = 2^(-age/half_life)
    weights = np.power(2, -ages_days / half_life_days)
    
    # Return weighted delays (for use in weighted percentile calculations)
    return delays, weights


def calculate_weighted_percentiles(
    delays: pd.Series,
    weights: pd.Series,
    percentiles: List[float] = [25, 50, 75, 90]
) -> Dict[str, float]:
    """
    Calculate percentiles with recency weighting.
    """
    if delays.empty or weights.empty:
        return {f"p{p}": 0.0 for p in percentiles}
    
    # Sort by delay value
    sorted_indices = delays.argsort()
    sorted_delays = delays.iloc[sorted_indices]
    sorted_weights = weights.iloc[sorted_indices]
    
    # Normalize weights
    sorted_weights = sorted_weights / sorted_weights.sum()
    
    # Calculate cumulative weights
    cum_weights = sorted_weights.cumsum()
    
    # Find percentiles
    result = {}
    for p in percentiles:
        target = p / 100.0
        idx = (cum_weights >= target).idxmax() if (cum_weights >= target).any() else len(cum_weights) - 1
        result[f"p{p}"] = float(sorted_delays.iloc[idx])
    
    return result


def enhance_forecast_with_outliers_and_regime(
    paid_df: pd.DataFrame,
    min_sample_size: int = 15
) -> Tuple[pd.DataFrame, Dict[str, bool]]:
    """
    Enhance forecast model with outlier handling and regime shift detection.
    
    Returns:
        - Enhanced paid_df with winsorized delays
        - Regime shift detection results
    """
    if paid_df.empty or 'delay_days' not in paid_df.columns:
        return paid_df, {}
    
    # 1. Winsorize outliers at P99
    if 'delay_days' in paid_df.columns:
        paid_df = paid_df.copy()
        paid_df['delay_days_winsorized'] = winsorize_delays(paid_df['delay_days'], percentile=99.0)
        # Use winsorized for calculations
        paid_df['delay_days'] = paid_df['delay_days_winsorized']
    
    # 2. Detect regime shifts by period (monthly)
    if 'payment_date' in paid_df.columns:
        paid_df['payment_month'] = pd.to_datetime(paid_df['payment_date']).dt.to_period('M')
        delays_by_period = {
            str(month): group['delay_days']
            for month, group in paid_df.groupby('payment_month')
            if len(group) >= min_sample_size
        }
        regime_shifts = detect_regime_shift(delays_by_period)
    else:
        regime_shifts = {}
    
    return paid_df, regime_shifts





