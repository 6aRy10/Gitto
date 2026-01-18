"""
Briefing Models

Data structures for Morning Briefings and Weekly Meeting Packs.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


class MovementType(str, Enum):
    """Type of cash movement"""
    INFLOW = "inflow"
    OUTFLOW = "outflow"


class AttentionSeverity(str, Enum):
    """Severity level for attention items"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CashMovement:
    """A single cash movement (inflow or outflow)"""
    movement_type: MovementType
    amount: Decimal
    currency: str
    description: str
    counterparty: Optional[str]
    transaction_id: Optional[int]
    timestamp: datetime
    expected: bool = True  # Was this expected?
    variance_from_expected: Decimal = Decimal("0")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "movement_type": self.movement_type.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "counterparty": self.counterparty,
            "transaction_id": self.transaction_id,
            "timestamp": self.timestamp.isoformat(),
            "expected": self.expected,
            "variance_from_expected": str(self.variance_from_expected),
        }


@dataclass
class CashPosition:
    """Current cash position with breakdown"""
    as_of: datetime
    opening_balance: Decimal
    total_inflows: Decimal
    total_outflows: Decimal
    current_balance: Decimal
    expected_balance: Decimal
    variance_from_expected: Decimal
    currency: str
    
    # Breakdown
    inflows: List[CashMovement] = field(default_factory=list)
    outflows: List[CashMovement] = field(default_factory=list)
    
    # By account
    by_account: Dict[str, Decimal] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "opening_balance": str(self.opening_balance),
            "total_inflows": str(self.total_inflows),
            "total_outflows": str(self.total_outflows),
            "current_balance": str(self.current_balance),
            "expected_balance": str(self.expected_balance),
            "variance_from_expected": str(self.variance_from_expected),
            "currency": self.currency,
            "inflows": [m.to_dict() for m in self.inflows],
            "outflows": [m.to_dict() for m in self.outflows],
            "by_account": {k: str(v) for k, v in self.by_account.items()},
        }


@dataclass 
class AttentionItem:
    """Something that needs attention"""
    severity: AttentionSeverity
    title: str
    description: str
    amount: Optional[Decimal]
    recommended_action: str
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Optional: link to decision queue
    decision_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "amount": str(self.amount) if self.amount else None,
            "recommended_action": self.recommended_action,
            "evidence_refs": self.evidence_refs,
            "decision_id": self.decision_id,
        }


@dataclass
class ExpectedMovement:
    """An expected cash movement for today/upcoming"""
    movement_type: MovementType
    amount: Decimal
    currency: str
    description: str
    counterparty: Optional[str]
    expected_date: date
    invoice_id: Optional[int] = None
    bill_id: Optional[int] = None
    confidence: float = 1.0  # Probability this will happen
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "movement_type": self.movement_type.value,
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "counterparty": self.counterparty,
            "expected_date": self.expected_date.isoformat(),
            "invoice_id": self.invoice_id,
            "bill_id": self.bill_id,
            "confidence": self.confidence,
        }


@dataclass
class MorningBriefing:
    """
    Daily morning briefing - the first thing FP&A checks every day.
    
    Contains:
    - Current cash position vs expected
    - Overnight activity
    - Surprises (unexpected items)
    - Today's expected movements
    - Items needing attention
    """
    id: str
    entity_id: int
    briefing_date: date
    generated_at: datetime
    
    # Cash position
    cash_position: CashPosition
    
    # Overnight activity
    overnight_inflows: List[CashMovement]
    overnight_outflows: List[CashMovement]
    
    # Surprises
    surprises: List[AttentionItem]
    
    # Today's expected
    expected_inflows: List[ExpectedMovement]
    expected_outflows: List[ExpectedMovement]
    total_expected_inflows: Decimal
    total_expected_outflows: Decimal
    
    # Attention needed
    attention_items: List[AttentionItem]
    
    # Summary metrics
    position_vs_forecast_pct: float  # e.g., -3.4 means 3.4% below forecast
    inflow_count_overnight: int
    outflow_count_overnight: int
    
    # Narrative (LLM-generated summary)
    executive_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "briefing_date": self.briefing_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "cash_position": self.cash_position.to_dict(),
            "overnight_inflows": [m.to_dict() for m in self.overnight_inflows],
            "overnight_outflows": [m.to_dict() for m in self.overnight_outflows],
            "surprises": [s.to_dict() for s in self.surprises],
            "expected_inflows": [m.to_dict() for m in self.expected_inflows],
            "expected_outflows": [m.to_dict() for m in self.expected_outflows],
            "total_expected_inflows": str(self.total_expected_inflows),
            "total_expected_outflows": str(self.total_expected_outflows),
            "attention_items": [a.to_dict() for a in self.attention_items],
            "position_vs_forecast_pct": self.position_vs_forecast_pct,
            "inflow_count_overnight": self.inflow_count_overnight,
            "outflow_count_overnight": self.outflow_count_overnight,
            "executive_summary": self.executive_summary,
        }


@dataclass
class TalkingPoint:
    """A talking point for CFO/leadership meetings"""
    order: int
    headline: str
    detail: str
    supporting_data: Dict[str, Any]
    severity: AttentionSeverity = AttentionSeverity.INFO
    action_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "headline": self.headline,
            "detail": self.detail,
            "supporting_data": self.supporting_data,
            "severity": self.severity.value,
            "action_required": self.action_required,
        }


@dataclass
class ForecastComparison:
    """Week-over-week forecast comparison"""
    week_number: int
    week_start_date: date
    previous_forecast: Decimal
    current_forecast: Decimal
    variance: Decimal
    variance_pct: float
    
    # Root cause breakdown (filled by variance analysis)
    timing_variance: Decimal = Decimal("0")
    volume_variance: Decimal = Decimal("0")
    price_rate_variance: Decimal = Decimal("0")
    mix_variance: Decimal = Decimal("0")
    one_time_variance: Decimal = Decimal("0")
    error_variance: Decimal = Decimal("0")
    
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "week_number": self.week_number,
            "week_start_date": self.week_start_date.isoformat(),
            "previous_forecast": str(self.previous_forecast),
            "current_forecast": str(self.current_forecast),
            "variance": str(self.variance),
            "variance_pct": self.variance_pct,
            "timing_variance": str(self.timing_variance),
            "volume_variance": str(self.volume_variance),
            "price_rate_variance": str(self.price_rate_variance),
            "mix_variance": str(self.mix_variance),
            "one_time_variance": str(self.one_time_variance),
            "error_variance": str(self.error_variance),
            "explanation": self.explanation,
        }


@dataclass
class WeeklyPack:
    """
    Weekly meeting preparation pack.
    
    Contains:
    - 13-week rolling forecast
    - Week-over-week changes with root cause
    - CFO talking points
    - Decisions needed
    - Forecast accuracy metrics
    """
    id: str
    entity_id: int
    snapshot_id: int
    pack_date: date
    generated_at: datetime
    
    # Forecast data
    forecast_weeks: List[Dict[str, Any]]  # 13 weeks of forecast data
    forecast_comparisons: List[ForecastComparison]
    
    # Key metrics
    current_cash: Decimal
    min_cash_week: int  # Which week has minimum cash
    min_cash_amount: Decimal
    runway_weeks: int
    
    # Accuracy
    forecast_accuracy_pct: float  # e.g., 94.0
    accuracy_trend: str  # "improving", "stable", "declining"
    accuracy_vs_last_month: float  # e.g., +3.0 means 3% better
    
    # CFO materials
    talking_points: List[TalkingPoint]
    decisions_pending: List[str]  # Decision IDs
    
    # Narrative
    executive_summary: str = ""
    key_risks: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "snapshot_id": self.snapshot_id,
            "pack_date": self.pack_date.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "forecast_weeks": self.forecast_weeks,
            "forecast_comparisons": [fc.to_dict() for fc in self.forecast_comparisons],
            "current_cash": str(self.current_cash),
            "min_cash_week": self.min_cash_week,
            "min_cash_amount": str(self.min_cash_amount),
            "runway_weeks": self.runway_weeks,
            "forecast_accuracy_pct": self.forecast_accuracy_pct,
            "accuracy_trend": self.accuracy_trend,
            "accuracy_vs_last_month": self.accuracy_vs_last_month,
            "talking_points": [tp.to_dict() for tp in self.talking_points],
            "decisions_pending": self.decisions_pending,
            "executive_summary": self.executive_summary,
            "key_risks": self.key_risks,
            "recommended_actions": self.recommended_actions,
        }
