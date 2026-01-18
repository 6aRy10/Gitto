"""
Variance Models

Data structures for structured variance analysis using industry-standard
categories: Timing, Volume, Price/Rate, Mix, One-time, Error.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


class VarianceCategory(str, Enum):
    """
    Industry-standard variance categories.
    
    Every variance should be categorized into one of these buckets
    to provide meaningful root cause analysis.
    """
    TIMING = "timing"          # Same transaction, different date (shifted)
    VOLUME = "volume"          # Count of transactions changed
    PRICE_RATE = "price_rate"  # Same volume, different amount (FX, pricing)
    MIX = "mix"               # Composition of sources changed
    ONE_TIME = "one_time"     # Non-recurring item
    ERROR = "error"           # Data quality issue


class VarianceDirection(str, Enum):
    """Direction of variance"""
    FAVORABLE = "favorable"      # Better than expected
    UNFAVORABLE = "unfavorable"  # Worse than expected
    NEUTRAL = "neutral"          # No material impact


@dataclass
class RootCause:
    """
    A single root cause contributing to a variance.
    
    Each variance can have multiple root causes that sum to the total.
    """
    category: VarianceCategory
    amount: Decimal
    currency: str
    description: str
    
    # Evidence
    related_entity: Optional[str] = None  # Customer, vendor, account
    related_ids: List[int] = field(default_factory=list)  # Invoice IDs, txn IDs
    
    # For TIMING variances
    original_date: Optional[date] = None
    new_date: Optional[date] = None
    
    # For VOLUME variances
    count_change: Optional[int] = None
    
    # For PRICE_RATE variances
    original_rate: Optional[float] = None
    new_rate: Optional[float] = None
    
    # For ONE_TIME variances
    is_recurring: bool = False
    
    # Confidence in this attribution
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "related_entity": self.related_entity,
            "related_ids": self.related_ids,
            "original_date": self.original_date.isoformat() if self.original_date else None,
            "new_date": self.new_date.isoformat() if self.new_date else None,
            "count_change": self.count_change,
            "original_rate": self.original_rate,
            "new_rate": self.new_rate,
            "is_recurring": self.is_recurring,
            "confidence": self.confidence,
        }


@dataclass
class VarianceItem:
    """
    A single variance that needs explanation.
    
    Could be:
    - Actual vs Forecast
    - Actual vs Budget
    - Current Forecast vs Previous Forecast
    """
    id: str
    variance_type: str  # "actual_vs_forecast", "forecast_drift", "actual_vs_budget"
    period: str  # "week_12", "month_jan", etc.
    
    # Amounts
    expected_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    variance_pct: float
    currency: str
    
    # Direction
    direction: VarianceDirection
    
    # Materiality
    is_material: bool  # Based on thresholds
    materiality_threshold: Decimal
    
    # Context
    entity_id: int
    category: Optional[str] = None  # e.g., "AR", "AP", "Payroll"
    subcategory: Optional[str] = None
    
    # Root causes (populated by analysis)
    root_causes: List[RootCause] = field(default_factory=list)
    
    # Explanation (LLM-generated)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "variance_type": self.variance_type,
            "period": self.period,
            "expected_amount": str(self.expected_amount),
            "actual_amount": str(self.actual_amount),
            "variance_amount": str(self.variance_amount),
            "variance_pct": self.variance_pct,
            "currency": self.currency,
            "direction": self.direction.value,
            "is_material": self.is_material,
            "materiality_threshold": str(self.materiality_threshold),
            "entity_id": self.entity_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "explanation": self.explanation,
        }


@dataclass
class CategorizedVariance:
    """
    A variance with fully categorized root causes.
    
    The sum of all category amounts should equal the total variance.
    """
    variance_item: VarianceItem
    
    # Category totals
    timing_total: Decimal = Decimal("0")
    volume_total: Decimal = Decimal("0")
    price_rate_total: Decimal = Decimal("0")
    mix_total: Decimal = Decimal("0")
    one_time_total: Decimal = Decimal("0")
    error_total: Decimal = Decimal("0")
    unexplained: Decimal = Decimal("0")  # Should be near zero
    
    # Individual root causes
    root_causes: List[RootCause] = field(default_factory=list)
    
    # Validation
    @property
    def is_fully_explained(self) -> bool:
        """Check if variance is fully attributed to root causes"""
        total_explained = (
            self.timing_total + self.volume_total + self.price_rate_total +
            self.mix_total + self.one_time_total + self.error_total
        )
        return abs(self.variance_item.variance_amount - total_explained) < Decimal("0.01")
    
    @property
    def explanation_coverage_pct(self) -> float:
        """Percentage of variance that is explained"""
        if self.variance_item.variance_amount == 0:
            return 100.0
        total_explained = (
            abs(self.timing_total) + abs(self.volume_total) + abs(self.price_rate_total) +
            abs(self.mix_total) + abs(self.one_time_total) + abs(self.error_total)
        )
        return float(total_explained / abs(self.variance_item.variance_amount) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variance_item": self.variance_item.to_dict(),
            "timing_total": str(self.timing_total),
            "volume_total": str(self.volume_total),
            "price_rate_total": str(self.price_rate_total),
            "mix_total": str(self.mix_total),
            "one_time_total": str(self.one_time_total),
            "error_total": str(self.error_total),
            "unexplained": str(self.unexplained),
            "root_causes": [rc.to_dict() for rc in self.root_causes],
            "is_fully_explained": self.is_fully_explained,
            "explanation_coverage_pct": self.explanation_coverage_pct,
        }


@dataclass
class ForecastDrift:
    """
    Week-over-week change in forecast for a specific future period.
    
    Answers: "Last week we forecasted €500k for Week 12, now we're 
    forecasting €450k. What changed?"
    """
    target_week: int
    target_date: date
    
    # Forecasts
    previous_forecast_date: date
    previous_forecast_amount: Decimal
    current_forecast_date: date
    current_forecast_amount: Decimal
    
    # Drift
    drift_amount: Decimal
    drift_pct: float
    
    # Categorized explanation
    categorized: Optional[CategorizedVariance] = None
    
    # Summary
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_week": self.target_week,
            "target_date": self.target_date.isoformat(),
            "previous_forecast_date": self.previous_forecast_date.isoformat(),
            "previous_forecast_amount": str(self.previous_forecast_amount),
            "current_forecast_date": self.current_forecast_date.isoformat(),
            "current_forecast_amount": str(self.current_forecast_amount),
            "drift_amount": str(self.drift_amount),
            "drift_pct": self.drift_pct,
            "categorized": self.categorized.to_dict() if self.categorized else None,
            "summary": self.summary,
        }


@dataclass
class VarianceReport:
    """
    Complete variance analysis report for a period.
    """
    id: str
    entity_id: int
    snapshot_id: int
    report_type: str  # "weekly", "monthly", "ad_hoc"
    generated_at: datetime
    
    # Period
    period_start: date
    period_end: date
    
    # All variances
    variances: List[CategorizedVariance]
    
    # Aggregates
    total_favorable: Decimal
    total_unfavorable: Decimal
    net_variance: Decimal
    
    # By category
    by_category: Dict[str, Decimal] = field(default_factory=dict)
    
    # Material items only
    material_variances: List[CategorizedVariance] = field(default_factory=list)
    
    # Executive summary (LLM-generated)
    executive_summary: str = ""
    key_drivers: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "snapshot_id": self.snapshot_id,
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "variances": [v.to_dict() for v in self.variances],
            "total_favorable": str(self.total_favorable),
            "total_unfavorable": str(self.total_unfavorable),
            "net_variance": str(self.net_variance),
            "by_category": {k: str(v) for k, v in self.by_category.items()},
            "material_variances": [v.to_dict() for v in self.material_variances],
            "executive_summary": self.executive_summary,
            "key_drivers": self.key_drivers,
            "recommended_actions": self.recommended_actions,
        }
