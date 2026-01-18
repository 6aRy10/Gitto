"""
FP&A Variance Engine

Computes structured variance analysis with categorization, root cause analysis,
and talking points for CFO briefings.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from sqlalchemy.orm import Session

from fpa_models import (
    ActualsSnapshot, ForecastRun, VarianceReport, VarianceCategory
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class VarianceItem:
    """A single variance item"""
    category: VarianceCategory
    line_item: str  # P&L line or cash line
    period: str  # Month or week
    
    actual: Decimal
    expected: Decimal
    variance: Decimal  # actual - expected
    variance_pct: Decimal
    
    # Attribution
    drivers: List[str] = field(default_factory=list)  # Contributing drivers
    evidence_refs: List[Dict] = field(default_factory=list)
    
    # Flags
    is_favorable: bool = False
    is_material: bool = False  # Above materiality threshold
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "line_item": self.line_item,
            "period": self.period,
            "actual": str(self.actual),
            "expected": str(self.expected),
            "variance": str(self.variance),
            "variance_pct": str(self.variance_pct),
            "drivers": self.drivers,
            "evidence_refs": self.evidence_refs,
            "is_favorable": self.is_favorable,
            "is_material": self.is_material,
        }


@dataclass
class RootCause:
    """Root cause analysis for a variance"""
    category: VarianceCategory
    description: str
    impact_amount: Decimal
    impact_pct: Decimal
    confidence: str  # "high", "medium", "low"
    
    # Supporting evidence
    evidence: List[Dict] = field(default_factory=list)
    related_items: List[str] = field(default_factory=list)  # Other affected items
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category.value,
            "description": self.description,
            "impact_amount": str(self.impact_amount),
            "impact_pct": str(self.impact_pct),
            "confidence": self.confidence,
            "evidence": self.evidence,
            "related_items": self.related_items,
        }


@dataclass
class TalkingPoint:
    """A bullet point for CFO briefing"""
    priority: int  # 1 = highest
    headline: str  # One-liner
    detail: str  # Supporting detail
    action_required: bool
    owner: Optional[str] = None
    
    # Supporting data
    variance_amount: Optional[Decimal] = None
    evidence_refs: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "priority": self.priority,
            "headline": self.headline,
            "detail": self.detail,
            "action_required": self.action_required,
            "owner": self.owner,
            "variance_amount": str(self.variance_amount) if self.variance_amount else None,
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class VarianceAnalysis:
    """Complete variance analysis output"""
    comparison_type: str
    period_start: date
    period_end: date
    
    # Variance items by category
    items: List[VarianceItem]
    root_causes: List[RootCause]
    talking_points: List[TalkingPoint]
    
    # Summary
    total_variance: Decimal = Decimal("0")
    variance_by_category: Dict[str, Decimal] = field(default_factory=dict)
    favorable_count: int = 0
    unfavorable_count: int = 0
    material_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "comparison_type": self.comparison_type,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "items": [i.to_dict() for i in self.items],
            "root_causes": [r.to_dict() for r in self.root_causes],
            "talking_points": [t.to_dict() for t in self.talking_points],
            "total_variance": str(self.total_variance),
            "variance_by_category": {k: str(v) for k, v in self.variance_by_category.items()},
            "favorable_count": self.favorable_count,
            "unfavorable_count": self.unfavorable_count,
            "material_count": self.material_count,
        }


# =============================================================================
# VARIANCE ENGINE
# =============================================================================

class FPAVarianceEngine:
    """
    Variance analysis engine.
    
    Supports:
    - Actual vs Plan
    - Actual vs Forecast
    - Forecast vs Forecast (period over period)
    """
    
    def __init__(self, db: Session, materiality_threshold: Decimal = Decimal("10000")):
        self.db = db
        self.materiality_threshold = materiality_threshold
    
    def compare_actual_vs_plan(
        self,
        actuals: ActualsSnapshot,
        plan_forecast: ForecastRun,
    ) -> VarianceAnalysis:
        """
        Compare actuals to plan forecast.
        """
        return self._analyze_variance(
            comparison_type="actual_vs_plan",
            actual_data=self._extract_actuals_data(actuals),
            expected_data=self._extract_forecast_data(plan_forecast),
            period_start=actuals.period_month,
            period_end=actuals.period_month,
        )
    
    def compare_actual_vs_forecast(
        self,
        actuals: ActualsSnapshot,
        forecast: ForecastRun,
    ) -> VarianceAnalysis:
        """
        Compare actuals to latest forecast.
        """
        return self._analyze_variance(
            comparison_type="actual_vs_forecast",
            actual_data=self._extract_actuals_data(actuals),
            expected_data=self._extract_forecast_data(forecast),
            period_start=actuals.period_month,
            period_end=actuals.period_month,
        )
    
    def compare_forecast_vs_forecast(
        self,
        current_forecast: ForecastRun,
        prior_forecast: ForecastRun,
    ) -> VarianceAnalysis:
        """
        Compare two forecast runs (period over period or version comparison).
        """
        current_data = self._extract_forecast_data(current_forecast)
        prior_data = self._extract_forecast_data(prior_forecast)
        
        # Determine period from forecasts
        period_start = date.fromisoformat(
            list(current_data.get("revenue_by_month", {"2026-01": 0}).keys())[0] + "-01"
        ) if current_data.get("revenue_by_month") else date.today()
        
        return self._analyze_variance(
            comparison_type="forecast_vs_forecast",
            actual_data=current_data,  # "current" is the new actual
            expected_data=prior_data,  # "prior" is what we expected
            period_start=period_start,
            period_end=period_start,
        )
    
    def _analyze_variance(
        self,
        comparison_type: str,
        actual_data: Dict,
        expected_data: Dict,
        period_start: date,
        period_end: date,
    ) -> VarianceAnalysis:
        """
        Core variance analysis logic.
        """
        items = []
        
        # Revenue variance
        revenue_items = self._analyze_line_variances(
            actual_data.get("revenue_by_month", {}),
            expected_data.get("revenue_by_month", {}),
            "Revenue",
            is_expense=False,
        )
        items.extend(revenue_items)
        
        # COGS variance
        cogs_items = self._analyze_line_variances(
            actual_data.get("cogs_by_month", {}),
            expected_data.get("cogs_by_month", {}),
            "COGS",
            is_expense=True,
        )
        items.extend(cogs_items)
        
        # Opex variance
        opex_items = self._analyze_line_variances(
            actual_data.get("opex_by_month", {}),
            expected_data.get("opex_by_month", {}),
            "Operating Expenses",
            is_expense=True,
        )
        items.extend(opex_items)
        
        # EBITDA variance
        ebitda_items = self._analyze_line_variances(
            actual_data.get("ebitda_by_month", {}),
            expected_data.get("ebitda_by_month", {}),
            "EBITDA",
            is_expense=False,
        )
        items.extend(ebitda_items)
        
        # Cash variance
        cash_items = self._analyze_line_variances(
            actual_data.get("ending_cash_by_month", {}),
            expected_data.get("ending_cash_by_month", {}),
            "Ending Cash",
            is_expense=False,
        )
        items.extend(cash_items)
        
        # Categorize variances
        items = self._categorize_variances(items, actual_data, expected_data)
        
        # Generate root causes
        root_causes = self._analyze_root_causes(items)
        
        # Generate talking points
        talking_points = self._generate_talking_points(items, root_causes)
        
        # Calculate summary
        total_variance = sum(i.variance for i in items if i.line_item == "EBITDA")
        
        variance_by_category = {}
        for category in VarianceCategory:
            category_variance = sum(
                i.variance for i in items 
                if i.category == category and i.line_item == "EBITDA"
            )
            if category_variance != 0:
                variance_by_category[category.value] = category_variance
        
        favorable_count = sum(1 for i in items if i.is_favorable)
        unfavorable_count = len(items) - favorable_count
        material_count = sum(1 for i in items if i.is_material)
        
        return VarianceAnalysis(
            comparison_type=comparison_type,
            period_start=period_start,
            period_end=period_end,
            items=items,
            root_causes=root_causes,
            talking_points=talking_points,
            total_variance=total_variance,
            variance_by_category=variance_by_category,
            favorable_count=favorable_count,
            unfavorable_count=unfavorable_count,
            material_count=material_count,
        )
    
    def _analyze_line_variances(
        self,
        actual_by_month: Dict[str, Any],
        expected_by_month: Dict[str, Any],
        line_item: str,
        is_expense: bool,
    ) -> List[VarianceItem]:
        """
        Analyze variances for a specific line item.
        """
        items = []
        
        all_months = set(actual_by_month.keys()) | set(expected_by_month.keys())
        
        for month in sorted(all_months):
            actual = Decimal(str(actual_by_month.get(month, 0)))
            expected = Decimal(str(expected_by_month.get(month, 0)))
            
            variance = actual - expected
            variance_pct = (
                (variance / abs(expected) * 100) if expected != 0 
                else Decimal("100") if variance != 0 
                else Decimal("0")
            )
            
            # Determine favorability
            # For expenses: negative variance (less than expected) is favorable
            # For revenue/profit: positive variance is favorable
            if is_expense:
                is_favorable = variance < 0  # Spent less than expected
            else:
                is_favorable = variance > 0  # Made more than expected
            
            is_material = abs(variance) >= self.materiality_threshold
            
            items.append(VarianceItem(
                category=VarianceCategory.VOLUME,  # Default, will be recategorized
                line_item=line_item,
                period=month,
                actual=actual,
                expected=expected,
                variance=variance,
                variance_pct=variance_pct.quantize(Decimal("0.1")),
                is_favorable=is_favorable,
                is_material=is_material,
            ))
        
        return items
    
    def _categorize_variances(
        self,
        items: List[VarianceItem],
        actual_data: Dict,
        expected_data: Dict,
    ) -> List[VarianceItem]:
        """
        Assign variance categories based on root cause analysis.
        """
        for item in items:
            category = self._determine_category(item, actual_data, expected_data)
            item.category = category
        
        return items
    
    def _determine_category(
        self,
        item: VarianceItem,
        actual_data: Dict,
        expected_data: Dict,
    ) -> VarianceCategory:
        """
        Determine the category for a variance item.
        
        Categories:
        - TIMING: Same transaction, different period (e.g., invoice recognized in different month)
        - VOLUME: Quantity/count differences (e.g., fewer sales, more hires)
        - PRICE_RATE: Unit price or FX changes
        - MIX: Composition shift (e.g., different product mix)
        - ONE_TIME: Non-recurring items
        - ERROR: Data quality issues (duplicates, missing data)
        """
        # This is a simplified categorization
        # In production, this would analyze underlying transaction data
        
        line_item = item.line_item.lower()
        variance_pct = abs(item.variance_pct)
        
        # Large percentage swings might indicate timing or one-time
        if variance_pct > Decimal("50"):
            if "revenue" in line_item:
                return VarianceCategory.TIMING  # Large revenue variance often timing
            else:
                return VarianceCategory.ONE_TIME  # Large expense variance often one-time
        
        # Check for data issues
        if item.expected == 0 and item.actual != 0:
            return VarianceCategory.ERROR  # Unexpected item
        
        # Small to moderate variances are typically volume
        if variance_pct < Decimal("20"):
            return VarianceCategory.VOLUME
        
        # Medium variances might be price/rate or mix
        if "cogs" in line_item or "expense" in line_item:
            return VarianceCategory.PRICE_RATE
        
        return VarianceCategory.MIX
    
    def _analyze_root_causes(self, items: List[VarianceItem]) -> List[RootCause]:
        """
        Generate root cause explanations for variances.
        """
        root_causes = []
        
        # Group material variances by category
        category_groups: Dict[VarianceCategory, List[VarianceItem]] = {}
        for item in items:
            if item.is_material:
                if item.category not in category_groups:
                    category_groups[item.category] = []
                category_groups[item.category].append(item)
        
        # Generate root cause for each category
        for category, category_items in category_groups.items():
            total_impact = sum(i.variance for i in category_items)
            
            if total_impact == 0:
                continue
            
            # Generate description based on category
            description = self._generate_root_cause_description(
                category, category_items, total_impact
            )
            
            # Confidence based on data availability
            confidence = "high" if len(category_items) >= 3 else "medium"
            
            root_causes.append(RootCause(
                category=category,
                description=description,
                impact_amount=total_impact,
                impact_pct=sum(i.variance_pct for i in category_items) / len(category_items),
                confidence=confidence,
                related_items=[i.line_item for i in category_items],
            ))
        
        # Sort by impact
        root_causes.sort(key=lambda x: abs(x.impact_amount), reverse=True)
        
        return root_causes
    
    def _generate_root_cause_description(
        self,
        category: VarianceCategory,
        items: List[VarianceItem],
        total_impact: Decimal,
    ) -> str:
        """
        Generate human-readable root cause description.
        """
        line_items = list(set(i.line_item for i in items))
        impact_direction = "over" if total_impact > 0 else "under"
        impact_abs = abs(total_impact)
        
        descriptions = {
            VarianceCategory.TIMING: (
                f"Timing differences in {', '.join(line_items)}: "
                f"€{impact_abs:,.0f} {impact_direction} due to recognition timing shifts"
            ),
            VarianceCategory.VOLUME: (
                f"Volume variance in {', '.join(line_items)}: "
                f"€{impact_abs:,.0f} {impact_direction} due to activity level changes"
            ),
            VarianceCategory.PRICE_RATE: (
                f"Price/rate changes in {', '.join(line_items)}: "
                f"€{impact_abs:,.0f} {impact_direction} due to unit cost or FX changes"
            ),
            VarianceCategory.MIX: (
                f"Mix shift in {', '.join(line_items)}: "
                f"€{impact_abs:,.0f} {impact_direction} due to composition changes"
            ),
            VarianceCategory.ONE_TIME: (
                f"One-time items affecting {', '.join(line_items)}: "
                f"€{impact_abs:,.0f} {impact_direction} from non-recurring events"
            ),
            VarianceCategory.ERROR: (
                f"Data quality issues in {', '.join(line_items)}: "
                f"€{impact_abs:,.0f} variance may be due to missing or duplicate data"
            ),
        }
        
        return descriptions.get(category, f"Variance of €{impact_abs:,.0f} in {', '.join(line_items)}")
    
    def _generate_talking_points(
        self,
        items: List[VarianceItem],
        root_causes: List[RootCause],
    ) -> List[TalkingPoint]:
        """
        Generate CFO talking points.
        
        These are factual bullet points (not narratives) for briefings.
        """
        talking_points = []
        priority = 1
        
        # Top unfavorable variances
        unfavorable_items = [i for i in items if not i.is_favorable and i.is_material]
        unfavorable_items.sort(key=lambda x: x.variance)  # Most negative first
        
        for item in unfavorable_items[:3]:  # Top 3
            talking_points.append(TalkingPoint(
                priority=priority,
                headline=f"{item.line_item} unfavorable by €{abs(item.variance):,.0f} ({item.variance_pct}%)",
                detail=f"Actual: €{item.actual:,.0f} vs Expected: €{item.expected:,.0f}",
                action_required=abs(item.variance_pct) > Decimal("20"),
                variance_amount=item.variance,
            ))
            priority += 1
        
        # Top favorable variances (as good news)
        favorable_items = [i for i in items if i.is_favorable and i.is_material]
        favorable_items.sort(key=lambda x: x.variance, reverse=True)
        
        for item in favorable_items[:2]:  # Top 2
            talking_points.append(TalkingPoint(
                priority=priority,
                headline=f"{item.line_item} favorable by €{abs(item.variance):,.0f} ({item.variance_pct}%)",
                detail=f"Actual: €{item.actual:,.0f} vs Expected: €{item.expected:,.0f}",
                action_required=False,
                variance_amount=item.variance,
            ))
            priority += 1
        
        # Root cause summary
        for rc in root_causes[:2]:  # Top 2 root causes
            talking_points.append(TalkingPoint(
                priority=priority,
                headline=f"Root cause: {rc.category.value.replace('_', ' ').title()}",
                detail=rc.description,
                action_required=rc.category == VarianceCategory.ERROR,
            ))
            priority += 1
        
        # Net summary
        ebitda_items = [i for i in items if i.line_item == "EBITDA"]
        if ebitda_items:
            total_ebitda_variance = sum(i.variance for i in ebitda_items)
            direction = "favorable" if total_ebitda_variance > 0 else "unfavorable"
            talking_points.insert(0, TalkingPoint(
                priority=0,
                headline=f"Net EBITDA {direction} by €{abs(total_ebitda_variance):,.0f}",
                detail=f"{len([i for i in items if i.is_material])} material variances identified",
                action_required=total_ebitda_variance < Decimal("-50000"),
                variance_amount=total_ebitda_variance,
            ))
        
        return sorted(talking_points, key=lambda x: x.priority)
    
    def _extract_actuals_data(self, actuals: ActualsSnapshot) -> Dict:
        """
        Extract structured data from actuals snapshot.
        """
        month_key = actuals.period_month.strftime("%Y-%m")
        
        return {
            "revenue_by_month": {month_key: actuals.revenue_total or Decimal("0")},
            "cogs_by_month": {month_key: actuals.cogs_total or Decimal("0")},
            "opex_by_month": {month_key: actuals.opex_total or Decimal("0")},
            "ebitda_by_month": {
                month_key: (
                    (actuals.revenue_total or Decimal("0")) - 
                    abs(actuals.cogs_total or Decimal("0")) - 
                    abs(actuals.opex_total or Decimal("0"))
                )
            },
            "ending_cash_by_month": {month_key: actuals.cash_ending or Decimal("0")},
        }
    
    def _extract_forecast_data(self, forecast: ForecastRun) -> Dict:
        """
        Extract structured data from forecast run.
        """
        if not forecast.outputs_json:
            return {}
        
        outputs = forecast.outputs_json
        pl = outputs.get("pl", {})
        cash = outputs.get("cash_bridge", {})
        
        return {
            "revenue_by_month": {
                k: Decimal(str(v)) 
                for k, v in pl.get("revenue_by_month", {}).items()
            },
            "cogs_by_month": {
                k: Decimal(str(v)) 
                for k, v in pl.get("cogs_by_month", {}).items()
            },
            "opex_by_month": {
                k: Decimal(str(v)) 
                for k, v in pl.get("opex_by_month", {}).items()
            },
            "ebitda_by_month": {
                k: Decimal(str(v)) 
                for k, v in pl.get("ebitda_by_month", {}).items()
            },
            "ending_cash_by_month": {
                k: Decimal(str(v)) 
                for k, v in cash.get("ending_cash_by_month", {}).items()
            },
        }
    
    def save_variance_report(
        self,
        entity_id: int,
        analysis: VarianceAnalysis,
        source_a_type: str,
        source_a_id: int,
        source_b_type: str,
        source_b_id: int,
    ) -> VarianceReport:
        """
        Save variance analysis to database.
        """
        report = VarianceReport(
            entity_id=entity_id,
            comparison_type=analysis.comparison_type,
            source_a_type=source_a_type,
            source_a_id=source_a_id,
            source_b_type=source_b_type,
            source_b_id=source_b_id,
            variance_items_json=[i.to_dict() for i in analysis.items],
            root_causes_json=[r.to_dict() for r in analysis.root_causes],
            talking_points_json=[t.to_dict() for t in analysis.talking_points],
            total_variance=analysis.total_variance,
            variance_by_category_json={k: str(v) for k, v in analysis.variance_by_category.items()},
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
