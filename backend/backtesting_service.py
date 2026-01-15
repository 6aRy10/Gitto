"""
Forecast Backtesting & Calibration Service

Key Metrics:
- Calibration: P25-P75 should contain ~50% of actuals
- Accuracy: Mean/median prediction error
- Bias: Systematic over/under prediction
- Reliability: Consistent accuracy over time

"Probabilities that behave like probabilities."
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import models


@dataclass
class ForecastPrediction:
    """A single forecast prediction for backtesting."""
    invoice_id: int
    snapshot_id: int
    forecast_date: datetime  # When forecast was made
    predicted_week: datetime  # Week predicted for payment
    
    # Percentile predictions
    p25: float  # 25th percentile delay
    p50: float  # Median delay
    p75: float  # 75th percentile delay
    p90: float  # 90th percentile delay
    
    # Segment info
    segment_type: str
    segment_key: str
    sample_size: int
    
    # Actuals (filled in after payment)
    actual_payment_date: Optional[datetime] = None
    actual_delay: Optional[int] = None


@dataclass
class CalibrationMetrics:
    """Calibration metrics for forecast accuracy."""
    total_predictions: int = 0
    
    # Calibration (should be ~25%, ~50%, ~75%)
    within_p25: int = 0
    within_p50: int = 0
    within_p75: int = 0
    within_p90: int = 0
    
    # Accuracy
    mean_error: float = 0.0  # Mean (actual - predicted)
    median_error: float = 0.0
    mean_abs_error: float = 0.0  # MAE
    
    # Bias (positive = consistently late, negative = consistently early)
    bias: float = 0.0
    
    # Time trends
    weekly_accuracy: Dict[str, float] = field(default_factory=dict)


@dataclass
class SegmentCalibration:
    """Calibration for a specific segment."""
    segment_type: str
    segment_key: str
    metrics: CalibrationMetrics
    sample_size: int
    recommendation: str = ""  # "well_calibrated", "over_confident", "under_confident"


class BacktestingService:
    """
    Service for backtesting forecast predictions.
    
    Usage:
        service = BacktestingService(db)
        service.record_predictions(snapshot_id)  # When forecast is made
        service.update_actuals(snapshot_id)       # When payments arrive
        metrics = service.get_calibration_report(snapshot_id)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_predictions(self, snapshot_id: int) -> int:
        """
        Record forecast predictions for later backtesting.
        
        Call this when a snapshot is locked to preserve predictions.
        """
        snapshot = self.db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
        if not snapshot:
            return 0
        
        # Get all invoices with forecasts
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.payment_date.is_(None),  # Only unpaid
            models.Invoice.prob_arrival_week.isnot(None)
        ).all()
        
        count = 0
        for inv in invoices:
            # Get segment delay stats
            delay_stats = self._get_delay_stats(inv)
            
            backtest = models.ForecastBacktest(
                snapshot_id=snapshot_id,
                invoice_id=inv.id,
                forecast_date=datetime.utcnow(),
                predicted_week=inv.prob_arrival_week,
                predicted_p25=delay_stats.get('p25', 0),
                predicted_p50=delay_stats.get('p50', 0),
                predicted_p75=delay_stats.get('p75', 0),
                predicted_p90=delay_stats.get('p90', 0),
                segment_type=delay_stats.get('segment_type', 'global'),
                segment_key=delay_stats.get('segment_key', 'all'),
                sample_size=delay_stats.get('sample_size', 0)
            )
            self.db.add(backtest)
            count += 1
        
        self.db.commit()
        return count
    
    def update_actuals(self, snapshot_id: int = None) -> int:
        """
        Update backtest records with actual payment data.
        
        Call periodically to update as payments arrive.
        """
        query = self.db.query(models.ForecastBacktest).filter(
            models.ForecastBacktest.actual_date.is_(None)
        )
        
        if snapshot_id:
            query = query.filter(models.ForecastBacktest.snapshot_id == snapshot_id)
        
        backtests = query.all()
        
        count = 0
        for bt in backtests:
            # Find the actual invoice payment
            invoice = self.db.query(models.Invoice).filter(
                models.Invoice.id == bt.invoice_id
            ).first()
            
            if invoice and invoice.payment_date:
                bt.actual_date = invoice.payment_date
                
                # Calculate actual delay
                if invoice.expected_due_date:
                    try:
                        due = invoice.expected_due_date
                        if isinstance(due, str):
                            due = datetime.fromisoformat(due.replace('Z', '+00:00'))
                        paid = invoice.payment_date
                        if isinstance(paid, str):
                            paid = datetime.fromisoformat(paid.replace('Z', '+00:00'))
                        
                        bt.actual_delay = (paid - due).days
                        
                        # Check if within percentile ranges
                        bt.in_p25_p75 = bt.predicted_p25 <= bt.actual_delay <= bt.predicted_p75
                        bt.in_p10_p90 = bt.predicted_p25 * 0.5 <= bt.actual_delay <= bt.predicted_p90
                        
                    except Exception:
                        pass
                
                count += 1
        
        self.db.commit()
        return count
    
    def get_calibration_report(
        self, 
        snapshot_id: int = None,
        since_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive calibration report.
        
        The key insight: P25-P75 range should contain ~50% of actuals.
        """
        query = self.db.query(models.ForecastBacktest).filter(
            models.ForecastBacktest.actual_date.isnot(None)
        )
        
        if snapshot_id:
            query = query.filter(models.ForecastBacktest.snapshot_id == snapshot_id)
        if since_date:
            query = query.filter(models.ForecastBacktest.forecast_date >= since_date)
        
        backtests = query.all()
        
        if not backtests:
            return {
                'total_predictions': 0,
                'calibration': None,
                'accuracy': None,
                'message': 'No completed forecasts to analyze'
            }
        
        # Calculate metrics
        metrics = self._calculate_metrics(backtests)
        
        # Segment-level breakdown
        segment_metrics = self._calculate_segment_metrics(backtests)
        
        # Time trends
        weekly_trends = self._calculate_weekly_trends(backtests)
        
        # Overall calibration assessment
        calibration_status = self._assess_calibration(metrics)
        
        return {
            'total_predictions': metrics.total_predictions,
            'calibration': {
                'within_p25_pct': round(metrics.within_p25 / metrics.total_predictions * 100, 1),
                'within_p50_pct': round(metrics.within_p50 / metrics.total_predictions * 100, 1),
                'within_p75_pct': round(metrics.within_p75 / metrics.total_predictions * 100, 1),
                'within_p90_pct': round(metrics.within_p90 / metrics.total_predictions * 100, 1),
                'target_p25_p75': '~50%',
                'actual_p25_p75': round((metrics.within_p75 - metrics.within_p25) / metrics.total_predictions * 100, 1),
            },
            'accuracy': {
                'mean_error_days': round(metrics.mean_error, 2),
                'median_error_days': round(metrics.median_error, 2),
                'mae_days': round(metrics.mean_abs_error, 2),
                'bias': round(metrics.bias, 2),
                'bias_direction': 'late' if metrics.bias > 0 else 'early' if metrics.bias < 0 else 'neutral',
            },
            'calibration_status': calibration_status,
            'segment_breakdown': segment_metrics,
            'weekly_trends': weekly_trends,
            'recommendations': self._generate_recommendations(metrics, segment_metrics)
        }
    
    def _get_delay_stats(self, invoice: models.Invoice) -> Dict[str, Any]:
        """Get delay statistics for an invoice's segment."""
        # Try to find cached segment stats
        segment_delay = self.db.query(models.SegmentDelay).filter(
            models.SegmentDelay.snapshot_id == invoice.snapshot_id,
            models.SegmentDelay.segment_key.like(f"%{invoice.customer_name or ''}%")
        ).first()
        
        if segment_delay:
            return {
                'p25': segment_delay.p25_delay or 0,
                'p50': segment_delay.p50_delay or 0,
                'p75': segment_delay.p75_delay or 0,
                'p90': segment_delay.p90_delay or 30,
                'segment_type': segment_delay.segment_type or 'customer',
                'segment_key': segment_delay.segment_key or invoice.customer_name or 'unknown',
                'sample_size': segment_delay.count or 0
            }
        
        # Fallback to global defaults
        return {
            'p25': 0,
            'p50': 15,
            'p75': 30,
            'p90': 45,
            'segment_type': 'global',
            'segment_key': 'fallback',
            'sample_size': 0
        }
    
    def _calculate_metrics(self, backtests: List[models.ForecastBacktest]) -> CalibrationMetrics:
        """Calculate overall calibration metrics."""
        metrics = CalibrationMetrics(total_predictions=len(backtests))
        
        errors = []
        abs_errors = []
        
        for bt in backtests:
            if bt.actual_delay is None:
                continue
            
            # Calculate prediction error
            error = bt.actual_delay - bt.predicted_p50
            errors.append(error)
            abs_errors.append(abs(error))
            
            # Check percentile containment
            if bt.actual_delay <= bt.predicted_p25:
                metrics.within_p25 += 1
            if bt.actual_delay <= bt.predicted_p50:
                metrics.within_p50 += 1
            if bt.actual_delay <= bt.predicted_p75:
                metrics.within_p75 += 1
            if bt.actual_delay <= bt.predicted_p90:
                metrics.within_p90 += 1
        
        if errors:
            metrics.mean_error = statistics.mean(errors)
            metrics.median_error = statistics.median(errors)
            metrics.mean_abs_error = statistics.mean(abs_errors)
            metrics.bias = metrics.mean_error
        
        return metrics
    
    def _calculate_segment_metrics(self, backtests: List[models.ForecastBacktest]) -> List[Dict]:
        """Calculate metrics by segment."""
        by_segment = defaultdict(list)
        
        for bt in backtests:
            key = f"{bt.segment_type}:{bt.segment_key}"
            by_segment[key].append(bt)
        
        results = []
        for key, segment_bts in by_segment.items():
            if len(segment_bts) < 5:  # Minimum sample
                continue
            
            metrics = self._calculate_metrics(segment_bts)
            segment_type, segment_key = key.split(':', 1)
            
            # Assess segment calibration
            p25_p75_pct = (metrics.within_p75 - metrics.within_p25) / metrics.total_predictions * 100
            if 40 <= p25_p75_pct <= 60:
                recommendation = 'well_calibrated'
            elif p25_p75_pct > 60:
                recommendation = 'under_confident'  # Range too wide
            else:
                recommendation = 'over_confident'  # Range too narrow
            
            results.append({
                'segment_type': segment_type,
                'segment_key': segment_key,
                'sample_size': len(segment_bts),
                'p25_p75_pct': round(p25_p75_pct, 1),
                'mae_days': round(metrics.mean_abs_error, 1),
                'bias': round(metrics.bias, 1),
                'recommendation': recommendation
            })
        
        # Sort by sample size
        return sorted(results, key=lambda x: -x['sample_size'])
    
    def _calculate_weekly_trends(self, backtests: List[models.ForecastBacktest]) -> List[Dict]:
        """Calculate accuracy trends by week."""
        by_week = defaultdict(list)
        
        for bt in backtests:
            if bt.forecast_date:
                week_key = bt.forecast_date.strftime('%Y-W%W')
                by_week[week_key].append(bt)
        
        results = []
        for week, week_bts in sorted(by_week.items()):
            metrics = self._calculate_metrics(week_bts)
            results.append({
                'week': week,
                'predictions': len(week_bts),
                'mae_days': round(metrics.mean_abs_error, 1),
                'p25_p75_pct': round(
                    (metrics.within_p75 - metrics.within_p25) / max(metrics.total_predictions, 1) * 100, 1
                )
            })
        
        return results[-12:]  # Last 12 weeks
    
    def _assess_calibration(self, metrics: CalibrationMetrics) -> Dict[str, Any]:
        """Assess overall calibration quality."""
        if metrics.total_predictions == 0:
            return {'status': 'insufficient_data', 'message': 'No completed predictions'}
        
        p25_p75_pct = (metrics.within_p75 - metrics.within_p25) / metrics.total_predictions * 100
        
        if 45 <= p25_p75_pct <= 55:
            status = 'excellent'
            message = 'Forecasts are well-calibrated. P25-P75 contains ~50% of actuals.'
        elif 40 <= p25_p75_pct <= 60:
            status = 'good'
            message = 'Forecasts are reasonably calibrated.'
        elif p25_p75_pct > 60:
            status = 'under_confident'
            message = 'Forecast ranges are too wide. Consider narrowing percentile estimates.'
        else:
            status = 'over_confident'
            message = 'Forecast ranges are too narrow. Predictions are overconfident.'
        
        return {
            'status': status,
            'message': message,
            'p25_p75_actual': round(p25_p75_pct, 1),
            'p25_p75_target': 50.0
        }
    
    def _generate_recommendations(
        self, 
        metrics: CalibrationMetrics, 
        segment_metrics: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recs = []
        
        # Overall calibration
        p25_p75_pct = (metrics.within_p75 - metrics.within_p25) / max(metrics.total_predictions, 1) * 100
        if p25_p75_pct < 40:
            recs.append("Widen percentile ranges - current forecasts are overconfident")
        elif p25_p75_pct > 60:
            recs.append("Narrow percentile ranges - current forecasts are too conservative")
        
        # Bias correction
        if metrics.bias > 3:
            recs.append(f"Systematic late payment bias detected ({metrics.bias:.1f} days). Consider adjusting base delay estimates.")
        elif metrics.bias < -3:
            recs.append(f"Systematic early payment bias detected ({metrics.bias:.1f} days). Consider adjusting base delay estimates.")
        
        # Segment-specific issues
        problematic_segments = [s for s in segment_metrics if s['recommendation'] != 'well_calibrated']
        if problematic_segments:
            worst = max(problematic_segments, key=lambda x: abs(x['bias']))
            recs.append(f"Segment '{worst['segment_key']}' has calibration issues (bias: {worst['bias']} days)")
        
        if not recs:
            recs.append("Forecasts are well-calibrated. Continue monitoring for drift.")
        
        return recs


# Add ForecastBacktest model if not exists
def ensure_backtest_table(db: Session):
    """Ensure the forecast backtest table exists."""
    # This would be handled by models.py, but here for reference
    pass
