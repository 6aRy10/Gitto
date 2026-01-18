"""
Forecast Worker

Wraps the probabilistic forecast service for FP&A workflows.
Provides forecast generation, comparison, and accuracy metrics.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from ..models.briefings import ForecastComparison

logger = logging.getLogger(__name__)


class ForecastWorker:
    """
    Wraps probabilistic_forecast_service_enhanced for FP&A workflows.
    
    Provides:
    - Forecast generation
    - Week-over-week comparison
    - Forecast accuracy metrics
    - Regime shift detection
    """
    
    def __init__(self, db: Session, entity_id: int):
        self.db = db
        self.entity_id = entity_id
    
    def generate_forecast(
        self,
        snapshot_id: int,
        weeks: int = 13,
    ) -> Dict[str, Any]:
        """
        Generate a probabilistic cash forecast.
        
        Args:
            snapshot_id: Snapshot to forecast from
            weeks: Number of weeks to forecast
        
        Returns:
            Forecast with P25/P50/P75/P90 for each week
        """
        try:
            from probabilistic_forecast_service_enhanced import EnhancedProbabilisticForecastService
            
            service = EnhancedProbabilisticForecastService(self.db)
            forecast = service.generate_forecast(
                snapshot_id=snapshot_id,
                weeks_ahead=weeks,
            )
            
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "weeks": forecast,
                "generated_at": datetime.utcnow().isoformat(),
            }
        except ImportError:
            logger.warning("Enhanced forecast service not available")
            # Return mock forecast for development
            return self._generate_mock_forecast(snapshot_id, weeks)
        except Exception as e:
            logger.exception("Error generating forecast")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _generate_mock_forecast(self, snapshot_id: int, weeks: int) -> Dict[str, Any]:
        """Generate mock forecast for development/testing"""
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        base_amount = Decimal("500000")  # Default
        if snapshot and snapshot.forecast_total_amount:
            base_amount = Decimal(str(snapshot.forecast_total_amount)) / weeks
        
        forecast_weeks = []
        today = date.today()
        
        for i in range(weeks):
            week_start = today + timedelta(weeks=i)
            # Add some variation
            variation = Decimal(str(1 + (i % 3 - 1) * 0.05))
            amount = base_amount * variation
            
            forecast_weeks.append({
                "week": i + 1,
                "week_start": week_start.isoformat(),
                "p25": str(amount * Decimal("0.85")),
                "p50": str(amount),
                "p75": str(amount * Decimal("1.15")),
                "p90": str(amount * Decimal("1.30")),
                "expected_inflows": str(amount * Decimal("0.6")),
                "expected_outflows": str(amount * Decimal("0.4")),
            })
        
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "weeks": forecast_weeks,
            "generated_at": datetime.utcnow().isoformat(),
            "is_mock": True,
        }
    
    def compare_forecasts(
        self,
        current_snapshot_id: int,
        previous_snapshot_id: int,
    ) -> List[ForecastComparison]:
        """
        Compare forecasts from two snapshots (week-over-week drift).
        
        Args:
            current_snapshot_id: Current forecast snapshot
            previous_snapshot_id: Previous forecast snapshot
        
        Returns:
            List of ForecastComparison for each week
        """
        current = self.generate_forecast(current_snapshot_id)
        previous = self.generate_forecast(previous_snapshot_id)
        
        if not current.get("success") or not previous.get("success"):
            return []
        
        comparisons = []
        current_weeks = {w["week"]: w for w in current.get("weeks", [])}
        previous_weeks = {w["week"]: w for w in previous.get("weeks", [])}
        
        for week_num in sorted(set(current_weeks.keys()) & set(previous_weeks.keys())):
            curr = current_weeks[week_num]
            prev = previous_weeks[week_num]
            
            curr_amount = Decimal(curr["p50"])
            prev_amount = Decimal(prev["p50"])
            variance = curr_amount - prev_amount
            variance_pct = float(variance / prev_amount * 100) if prev_amount != 0 else 0
            
            comparisons.append(ForecastComparison(
                week_number=week_num,
                week_start_date=date.fromisoformat(curr["week_start"]),
                previous_forecast=prev_amount,
                current_forecast=curr_amount,
                variance=variance,
                variance_pct=variance_pct,
            ))
        
        return comparisons
    
    def get_forecast_accuracy(
        self,
        lookback_weeks: int = 12,
    ) -> Dict[str, Any]:
        """
        Calculate forecast accuracy metrics.
        
        Compares historical forecasts to actual results.
        """
        # Get historical snapshots
        snapshots = self.db.query(models.Snapshot).filter(
            models.Snapshot.entity_id == self.entity_id,
        ).order_by(models.Snapshot.created_at.desc()).limit(lookback_weeks).all()
        
        if len(snapshots) < 2:
            return {
                "accuracy_pct": None,
                "error": "Insufficient historical data",
            }
        
        # Calculate MAPE (Mean Absolute Percentage Error)
        errors = []
        for i in range(1, len(snapshots)):
            current = snapshots[i-1]
            previous = snapshots[i]
            
            if current.actual_total_amount and previous.forecast_total_amount:
                actual = Decimal(str(current.actual_total_amount))
                forecast = Decimal(str(previous.forecast_total_amount))
                if forecast != 0:
                    error = abs((actual - forecast) / forecast)
                    errors.append(float(error))
        
        if not errors:
            return {"accuracy_pct": None, "error": "No comparable forecasts"}
        
        mape = sum(errors) / len(errors)
        accuracy = (1 - mape) * 100
        
        # Determine trend
        recent_errors = errors[:4] if len(errors) >= 4 else errors
        older_errors = errors[4:8] if len(errors) >= 8 else errors[len(errors)//2:]
        
        recent_avg = sum(recent_errors) / len(recent_errors) if recent_errors else 0
        older_avg = sum(older_errors) / len(older_errors) if older_errors else 0
        
        if recent_avg < older_avg * 0.9:
            trend = "improving"
        elif recent_avg > older_avg * 1.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "accuracy_pct": round(accuracy, 1),
            "mape": round(mape * 100, 2),
            "sample_size": len(errors),
            "trend": trend,
            "trend_detail": f"Recent MAPE: {recent_avg*100:.1f}%, Historical: {older_avg*100:.1f}%",
        }
    
    def detect_regime_shift(self, snapshot_id: int) -> Dict[str, Any]:
        """
        Detect if there's been a regime shift in payment behavior.
        
        A regime shift indicates fundamental change in patterns,
        not just normal variance.
        """
        try:
            from probabilistic_forecast_service_enhanced import EnhancedProbabilisticForecastService
            
            service = EnhancedProbabilisticForecastService(self.db)
            result = service.detect_regime_shift(snapshot_id)
            
            return {
                "regime_shift_detected": result.get("detected", False),
                "confidence": result.get("confidence", 0),
                "description": result.get("description", ""),
                "affected_segments": result.get("affected_segments", []),
            }
        except (ImportError, AttributeError):
            # Service doesn't have this method or not available
            return {
                "regime_shift_detected": False,
                "confidence": 0,
                "description": "Regime shift detection not available",
            }
    
    def get_runway(self, snapshot_id: int, min_cash_threshold: Decimal = Decimal("0")) -> Dict[str, Any]:
        """
        Calculate cash runway in weeks.
        
        Args:
            snapshot_id: Snapshot to analyze
            min_cash_threshold: Minimum acceptable cash level
        
        Returns:
            Runway information
        """
        forecast = self.generate_forecast(snapshot_id, weeks=52)
        
        if not forecast.get("success"):
            return {"runway_weeks": None, "error": forecast.get("error")}
        
        weeks = forecast.get("weeks", [])
        
        # Find week where P50 falls below threshold
        runway_weeks = len(weeks)
        min_cash_week = 0
        min_cash_amount = Decimal("999999999")
        
        for week in weeks:
            p50 = Decimal(week["p50"])
            if p50 < min_cash_amount:
                min_cash_amount = p50
                min_cash_week = week["week"]
            
            if p50 <= min_cash_threshold and runway_weeks == len(weeks):
                runway_weeks = week["week"] - 1
        
        return {
            "runway_weeks": runway_weeks,
            "min_cash_week": min_cash_week,
            "min_cash_amount": str(min_cash_amount),
            "threshold": str(min_cash_threshold),
            "is_healthy": runway_weeks >= 13,
        }
    
    def get_weekly_forecast(self, snapshot_id: int, week_number: int) -> Dict[str, Any]:
        """Get forecast for a specific week"""
        forecast = self.generate_forecast(snapshot_id)
        
        if not forecast.get("success"):
            return forecast
        
        weeks = forecast.get("weeks", [])
        for week in weeks:
            if week["week"] == week_number:
                return {
                    "success": True,
                    **week,
                }
        
        return {"success": False, "error": f"Week {week_number} not found"}
