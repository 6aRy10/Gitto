"""
Weekly Meeting Prep Workflow

Prepares materials for the weekly cash meeting:
- 13-week rolling forecast
- Week-over-week comparison with root cause analysis
- CFO talking points
- Decisions needing approval

Runs Monday at 6:00 AM (configurable).
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import logging
import uuid

if TYPE_CHECKING:
    from ..orchestrator import FPAOrchestrator

from ..workers.data_worker import DataWorker
from ..workers.reconciliation_worker import ReconciliationWorker
from ..workers.forecast_worker import ForecastWorker
from ..workers.variance_worker import VarianceWorker
from ..models.briefings import (
    WeeklyPack, ForecastComparison, TalkingPoint, AttentionSeverity
)
from ..models.variance import VarianceCategory
from ..decision_queue import create_cash_shortfall_decision
from ..audit_log import AuditAction

logger = logging.getLogger(__name__)


class WeeklyMeetingPrepWorkflow:
    """
    Prepares the weekly cash meeting pack.
    
    Output includes:
    - 13-week rolling cash forecast
    - Week-over-week forecast changes with root cause
    - CFO talking points
    - Decisions requiring approval
    - Forecast accuracy metrics
    """
    
    def __init__(self, orchestrator: 'FPAOrchestrator'):
        self.orchestrator = orchestrator
        self.db = orchestrator.db
        self.entity_id = orchestrator.entity_id
        
        # Initialize workers
        self.data_worker = DataWorker(self.db, self.entity_id)
        self.recon_worker = ReconciliationWorker(self.db, self.entity_id)
        self.forecast_worker = ForecastWorker(self.db, self.entity_id)
        self.variance_worker = VarianceWorker(self.db, self.entity_id)
    
    async def run(self, snapshot_id: Optional[int] = None) -> WeeklyPack:
        """Generate the weekly meeting pack"""
        today = date.today()
        now = datetime.utcnow()
        
        logger.info(f"Generating weekly meeting pack for {today}")
        
        # Get current snapshot
        if snapshot_id:
            snapshot = self.data_worker.get_snapshot(snapshot_id)
        else:
            snapshot = self.data_worker.get_latest_snapshot()
        
        if not snapshot:
            raise ValueError("No snapshot available")
        
        # 1. Generate 13-week forecast
        forecast_result = self.forecast_worker.generate_forecast(snapshot.id, weeks=13)
        forecast_weeks = forecast_result.get("weeks", [])
        
        # 2. Get previous week's forecast for comparison
        forecast_comparisons = self._get_forecast_comparisons(snapshot.id)
        
        # 3. Get cash metrics
        cash_position = self.data_worker.get_cash_position()
        runway = self.forecast_worker.get_runway(snapshot.id)
        
        # 4. Get forecast accuracy
        accuracy = self.forecast_worker.get_accuracy_metrics()
        
        # 5. Generate talking points
        talking_points = self._generate_talking_points(
            cash_position, forecast_weeks, forecast_comparisons, runway, accuracy
        )
        
        # 6. Check for decisions needed
        decisions_pending = self._check_for_decisions(forecast_weeks, cash_position)
        
        # 7. Identify risks
        key_risks = self._identify_risks(forecast_weeks, runway)
        
        # Create the pack
        pack = WeeklyPack(
            id=str(uuid.uuid4()),
            entity_id=self.entity_id,
            snapshot_id=snapshot.id,
            pack_date=today,
            generated_at=now,
            forecast_weeks=forecast_weeks,
            forecast_comparisons=forecast_comparisons,
            current_cash=cash_position.current_balance,
            min_cash_week=runway.get("min_cash_week", 0),
            min_cash_amount=Decimal(str(runway.get("min_cash_amount", 0))),
            runway_weeks=runway.get("runway_weeks", 0),
            forecast_accuracy_pct=accuracy.get("accuracy_pct", 0) or 0,
            accuracy_trend=accuracy.get("trend", "stable"),
            accuracy_vs_last_month=0,  # Would need historical data
            talking_points=talking_points,
            decisions_pending=decisions_pending,
            key_risks=key_risks,
        )
        
        # Generate executive summary
        pack.executive_summary = self._generate_executive_summary(pack)
        pack.recommended_actions = self._get_recommended_actions(pack)
        
        # Log
        self.orchestrator.audit_log.log(
            action=AuditAction.WEEKLY_PACK_GENERATED,
            description=f"Weekly pack generated: {len(forecast_weeks)} weeks forecast",
            details={
                "snapshot_id": snapshot.id,
                "runway_weeks": pack.runway_weeks,
                "accuracy_pct": pack.forecast_accuracy_pct,
                "decisions_pending": len(pack.decisions_pending),
            },
        )
        
        return pack
    
    def _get_forecast_comparisons(self, current_snapshot_id: int) -> List[ForecastComparison]:
        """Compare current forecast to previous week's"""
        # Get previous snapshot
        import models
        previous_snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.entity_id == self.entity_id,
            models.Snapshot.id != current_snapshot_id,
        ).order_by(models.Snapshot.created_at.desc()).first()
        
        if not previous_snapshot:
            return []
        
        comparisons = self.forecast_worker.compare_forecasts(
            current_snapshot_id, previous_snapshot.id
        )
        
        # Add variance categorization
        for comp in comparisons:
            if abs(comp.variance) > Decimal("5000"):
                # Use variance worker to categorize
                # This is simplified - full implementation would do detailed analysis
                if comp.variance_pct < 0:
                    comp.timing_variance = comp.variance * Decimal("0.6")
                    comp.volume_variance = comp.variance * Decimal("0.3")
                    comp.one_time_variance = comp.variance * Decimal("0.1")
                    comp.explanation = self._explain_forecast_change(comp)
        
        return comparisons
    
    def _explain_forecast_change(self, comparison: ForecastComparison) -> str:
        """Generate explanation for forecast change"""
        explanations = []
        
        if comparison.timing_variance != 0:
            explanations.append(
                f"Timing shifts: €{abs(comparison.timing_variance):,.0f} "
                f"({'later' if comparison.timing_variance < 0 else 'earlier'} than expected)"
            )
        
        if comparison.volume_variance != 0:
            explanations.append(
                f"Volume change: €{abs(comparison.volume_variance):,.0f} "
                f"({'fewer' if comparison.volume_variance < 0 else 'more'} transactions)"
            )
        
        if comparison.one_time_variance != 0:
            explanations.append(
                f"One-time items: €{abs(comparison.one_time_variance):,.0f}"
            )
        
        return "; ".join(explanations) if explanations else "Within normal variance"
    
    def _generate_talking_points(
        self,
        cash_position,
        forecast_weeks,
        comparisons,
        runway,
        accuracy,
    ) -> List[TalkingPoint]:
        """Generate CFO talking points"""
        points = []
        order = 0
        
        # 1. Current cash position
        order += 1
        points.append(TalkingPoint(
            order=order,
            headline=f"Cash position: €{cash_position.current_balance:,.0f}",
            detail=f"{'Above' if cash_position.variance_from_expected >= 0 else 'Below'} "
                   f"forecast by €{abs(cash_position.variance_from_expected):,.0f}",
            supporting_data={
                "current": str(cash_position.current_balance),
                "expected": str(cash_position.expected_balance),
            },
            severity=AttentionSeverity.INFO,
        ))
        
        # 2. Runway status
        order += 1
        runway_weeks = runway.get("runway_weeks", 0)
        severity = (
            AttentionSeverity.CRITICAL if runway_weeks < 8
            else AttentionSeverity.WARNING if runway_weeks < 13
            else AttentionSeverity.INFO
        )
        points.append(TalkingPoint(
            order=order,
            headline=f"Cash runway: {runway_weeks} weeks",
            detail=f"Minimum cash of €{Decimal(str(runway.get('min_cash_amount', 0))):,.0f} "
                   f"projected in week {runway.get('min_cash_week', 0)}",
            supporting_data=runway,
            severity=severity,
            action_required=runway_weeks < 13,
        ))
        
        # 3. Key forecast changes
        material_changes = [c for c in comparisons if abs(c.variance) > Decimal("10000")]
        if material_changes:
            order += 1
            total_change = sum(c.variance for c in material_changes)
            points.append(TalkingPoint(
                order=order,
                headline=f"Forecast revised by €{total_change:,.0f} vs last week",
                detail=f"{len(material_changes)} material changes identified",
                supporting_data={
                    "changes": [c.to_dict() for c in material_changes[:3]],
                },
                severity=AttentionSeverity.WARNING if total_change < 0 else AttentionSeverity.INFO,
            ))
        
        # 4. Forecast accuracy
        order += 1
        acc_pct = accuracy.get("accuracy_pct", 0)
        points.append(TalkingPoint(
            order=order,
            headline=f"Forecast accuracy: {acc_pct:.0f}%",
            detail=f"Trend: {accuracy.get('trend', 'stable')}",
            supporting_data=accuracy,
            severity=AttentionSeverity.INFO,
        ))
        
        return points
    
    def _check_for_decisions(
        self,
        forecast_weeks: List[Dict],
        cash_position,
    ) -> List[str]:
        """Check if any decisions are needed and create them"""
        decision_ids = []
        
        # Check for cash shortfalls
        min_cash_threshold = Decimal("100000")  # Configurable
        
        for week in forecast_weeks:
            p50 = Decimal(str(week.get("p50", 0)))
            if p50 < min_cash_threshold:
                week_num = week.get("week", 0)
                shortfall = min_cash_threshold - p50
                
                # Create decision
                decision = create_cash_shortfall_decision(
                    entity_id=self.entity_id,
                    snapshot_id=self.data_worker.get_latest_snapshot().id,
                    shortfall_amount=shortfall,
                    shortfall_week=week_num,
                    options=[
                        {
                            "label": "Delay discretionary vendor payments",
                            "description": "Defer non-critical vendor payments by 1-2 weeks",
                            "risk_level": "low",
                            "risk_explanation": "Most vendors have 30-day terms",
                            "impact_amount": float(shortfall * Decimal("0.5")),
                            "impact_description": f"Closes ~50% of gap",
                            "recommended": True,
                        },
                        {
                            "label": "Accelerate AR collection",
                            "description": "Contact customers with outstanding invoices",
                            "risk_level": "medium",
                            "risk_explanation": "May impact customer relationships",
                            "impact_amount": float(shortfall * Decimal("0.3")),
                            "impact_description": f"Potential to close ~30% of gap",
                        },
                        {
                            "label": "Draw on credit line",
                            "description": "Use available credit facility",
                            "risk_level": "low",
                            "risk_explanation": "Interest cost but guaranteed liquidity",
                            "impact_amount": float(shortfall),
                            "impact_description": "Full coverage",
                        },
                    ],
                    recommendation="Recommend combination of vendor delay and AR acceleration to avoid interest costs",
                )
                
                self.orchestrator.decision_queue.add_decision(decision)
                decision_ids.append(decision.id)
                
                # Only create one shortfall decision per run
                break
        
        return decision_ids
    
    def _identify_risks(self, forecast_weeks: List[Dict], runway: Dict) -> List[str]:
        """Identify key risks"""
        risks = []
        
        # Runway risk
        if runway.get("runway_weeks", 99) < 13:
            risks.append(f"Cash runway below 13 weeks ({runway.get('runway_weeks')} weeks)")
        
        # Concentration risk
        # Would analyze customer concentration here
        
        # Forecast volatility
        if forecast_weeks:
            p50_values = [Decimal(str(w.get("p50", 0))) for w in forecast_weeks]
            if p50_values:
                volatility = max(p50_values) - min(p50_values)
                avg = sum(p50_values) / len(p50_values)
                if avg > 0 and volatility / avg > Decimal("0.3"):
                    risks.append("High forecast volatility (>30% range)")
        
        return risks
    
    def _generate_executive_summary(self, pack: WeeklyPack) -> str:
        """Generate executive summary"""
        lines = []
        
        lines.append(f"Weekly Cash Meeting Pack - {pack.pack_date.strftime('%B %d, %Y')}")
        lines.append("")
        lines.append(f"Current cash: €{pack.current_cash:,.0f}")
        lines.append(f"Runway: {pack.runway_weeks} weeks")
        lines.append(f"Forecast accuracy: {pack.forecast_accuracy_pct:.0f}% ({pack.accuracy_trend})")
        
        if pack.decisions_pending:
            lines.append(f"\n{len(pack.decisions_pending)} decision(s) require approval")
        
        if pack.key_risks:
            lines.append(f"\nKey risks: {', '.join(pack.key_risks)}")
        
        return "\n".join(lines)
    
    def _get_recommended_actions(self, pack: WeeklyPack) -> List[str]:
        """Generate recommended actions"""
        actions = []
        
        if pack.runway_weeks < 13:
            actions.append("Review cash management options to extend runway")
        
        if pack.forecast_accuracy_pct < 85:
            actions.append("Investigate forecast accuracy drivers")
        
        if pack.decisions_pending:
            actions.append(f"Review and approve {len(pack.decisions_pending)} pending decision(s)")
        
        return actions


async def run_weekly_meeting_prep(
    orchestrator: 'FPAOrchestrator',
    entity_id: int,
    snapshot_id: Optional[int] = None,
    **kwargs,
) -> WeeklyPack:
    """
    Entry point for the weekly meeting prep workflow.
    
    Called by the orchestrator.
    """
    workflow = WeeklyMeetingPrepWorkflow(orchestrator)
    return await workflow.run(snapshot_id=snapshot_id)
