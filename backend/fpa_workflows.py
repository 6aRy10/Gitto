"""
FP&A Agent Workflows

Automated workflows for:
- Morning Briefing
- Weekly Forecast Update
- Month-End Close
- Continuous Monitoring
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from fpa_models import (
    Plan, PlanStatus, AssumptionSet, ActualsSnapshot, ForecastRun,
    FPAArtifact, FPADecision, VarianceReport, FPAAuditLog
)
from fpa_compute_engine import FPAComputeEngine
from fpa_variance_engine import FPAVarianceEngine, VarianceAnalysis

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW OUTPUTS
# =============================================================================

@dataclass
class MorningBriefingOutput:
    """Output of morning briefing workflow"""
    entity_id: int
    briefing_date: date
    
    # Cash position
    opening_cash: Decimal
    projected_cash_eod: Decimal
    min_cash_threshold: Decimal
    cash_status: str  # "healthy", "warning", "critical"
    
    # Overnight activity
    overnight_inflows: Decimal
    overnight_outflows: Decimal
    net_overnight: Decimal
    
    # Key items
    attention_items: List[Dict]  # Issues requiring attention
    expected_receipts: List[Dict]  # Expected collections today
    expected_payments: List[Dict]  # Expected payments today
    
    # Forecast summary
    runway_months: int
    burn_rate: Decimal
    
    # Data quality
    data_freshness: Dict[str, datetime]
    data_quality_issues: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "briefing_date": self.briefing_date.isoformat(),
            "opening_cash": str(self.opening_cash),
            "projected_cash_eod": str(self.projected_cash_eod),
            "min_cash_threshold": str(self.min_cash_threshold),
            "cash_status": self.cash_status,
            "overnight_inflows": str(self.overnight_inflows),
            "overnight_outflows": str(self.overnight_outflows),
            "net_overnight": str(self.net_overnight),
            "attention_items": self.attention_items,
            "expected_receipts": self.expected_receipts,
            "expected_payments": self.expected_payments,
            "runway_months": self.runway_months,
            "burn_rate": str(self.burn_rate),
            "data_freshness": {k: v.isoformat() for k, v in self.data_freshness.items()},
            "data_quality_issues": self.data_quality_issues,
        }


@dataclass
class WeeklyForecastOutput:
    """Output of weekly forecast update workflow"""
    entity_id: int
    week_ending: date
    
    # Forecast comparison
    current_forecast_id: int
    prior_forecast_id: Optional[int]
    
    # Variance analysis
    variance_analysis: Optional[VarianceAnalysis]
    
    # Key changes
    material_changes: List[Dict]
    driver_changes: List[Dict]
    
    # CFO talking points
    talking_points: List[Dict]
    
    # Recommendations
    decisions_required: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "week_ending": self.week_ending.isoformat(),
            "current_forecast_id": self.current_forecast_id,
            "prior_forecast_id": self.prior_forecast_id,
            "variance_analysis": self.variance_analysis.to_dict() if self.variance_analysis else None,
            "material_changes": self.material_changes,
            "driver_changes": self.driver_changes,
            "talking_points": self.talking_points,
            "decisions_required": self.decisions_required,
        }


@dataclass
class MonthEndCloseOutput:
    """Output of month-end close workflow"""
    entity_id: int
    period_month: date
    
    # Close status
    close_status: str  # "ready", "in_progress", "blocked", "completed"
    blocking_items: List[Dict]
    
    # Data completeness
    completeness_score: Decimal
    missing_items: List[Dict]
    
    # Reconciliation status
    reconciliation_status: Dict[str, str]
    unreconciled_items: List[Dict]
    
    # Actual vs plan
    variance_summary: Dict
    
    # Actions required
    pending_approvals: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            "entity_id": self.entity_id,
            "period_month": self.period_month.isoformat(),
            "close_status": self.close_status,
            "blocking_items": self.blocking_items,
            "completeness_score": str(self.completeness_score),
            "missing_items": self.missing_items,
            "reconciliation_status": self.reconciliation_status,
            "unreconciled_items": self.unreconciled_items,
            "variance_summary": self.variance_summary,
            "pending_approvals": self.pending_approvals,
        }


# =============================================================================
# WORKFLOW ORCHESTRATOR
# =============================================================================

class FPAWorkflowOrchestrator:
    """
    Orchestrates FP&A workflows.
    
    Coordinates between compute engine, variance engine, and data services.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.compute_engine = FPAComputeEngine(db)
        self.variance_engine = FPAVarianceEngine(db)
    
    # =========================================================================
    # MORNING BRIEFING
    # =========================================================================
    
    def run_morning_briefing(
        self,
        entity_id: int,
        briefing_date: Optional[date] = None,
    ) -> MorningBriefingOutput:
        """
        Generate morning briefing for treasury/FP&A team.
        
        Daily workflow that runs early morning to provide:
        - Cash position overview
        - Overnight activity
        - Expected receipts/payments
        - Issues requiring attention
        """
        briefing_date = briefing_date or date.today()
        
        # Get latest forecast for context
        latest_forecast = self._get_latest_forecast(entity_id)
        
        # Get latest actuals
        latest_actuals = self._get_latest_actuals(entity_id)
        
        # Cash position
        cash_data = self._get_cash_position(entity_id, latest_forecast, latest_actuals)
        
        # Overnight activity (simulated - in production would query bank feeds)
        overnight = self._get_overnight_activity(entity_id, briefing_date)
        
        # Expected receipts/payments
        expected_receipts = self._get_expected_receipts(entity_id, briefing_date)
        expected_payments = self._get_expected_payments(entity_id, briefing_date)
        
        # Attention items
        attention_items = self._identify_attention_items(
            entity_id, cash_data, expected_receipts, expected_payments
        )
        
        # Data quality check
        data_freshness, quality_issues = self._check_data_quality(entity_id)
        
        output = MorningBriefingOutput(
            entity_id=entity_id,
            briefing_date=briefing_date,
            opening_cash=cash_data.get("opening", Decimal("0")),
            projected_cash_eod=cash_data.get("projected_eod", Decimal("0")),
            min_cash_threshold=cash_data.get("min_threshold", Decimal("100000")),
            cash_status=cash_data.get("status", "unknown"),
            overnight_inflows=overnight.get("inflows", Decimal("0")),
            overnight_outflows=overnight.get("outflows", Decimal("0")),
            net_overnight=overnight.get("net", Decimal("0")),
            attention_items=attention_items,
            expected_receipts=expected_receipts,
            expected_payments=expected_payments,
            runway_months=cash_data.get("runway_months", 0),
            burn_rate=cash_data.get("burn_rate", Decimal("0")),
            data_freshness=data_freshness,
            data_quality_issues=quality_issues,
        )
        
        # Save as artifact
        self._save_artifact(
            entity_id=entity_id,
            artifact_type="morning_briefing",
            artifact_date=briefing_date,
            content=output.to_dict(),
        )
        
        self._log_action(entity_id, "workflow", "morning_briefing", None)
        
        return output
    
    def _get_cash_position(
        self,
        entity_id: int,
        forecast: Optional[ForecastRun],
        actuals: Optional[ActualsSnapshot],
    ) -> Dict:
        """Get current cash position and projections"""
        opening_cash = Decimal("0")
        min_threshold = Decimal("100000")
        runway_months = 0
        burn_rate = Decimal("0")
        
        if actuals and actuals.cash_ending:
            opening_cash = actuals.cash_ending
        
        if forecast and forecast.outputs_json:
            outputs = forecast.outputs_json
            runway = outputs.get("runway", {})
            runway_months = runway.get("runway_months", 0)
            burn_rate = Decimal(str(runway.get("average_monthly_burn", 0)))
            min_threshold = Decimal(str(runway.get("min_cash_threshold", 100000)))
        
        # Determine status
        if opening_cash < min_threshold:
            status = "critical"
        elif opening_cash < min_threshold * 2:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "opening": opening_cash,
            "projected_eod": opening_cash,  # Simplified
            "min_threshold": min_threshold,
            "status": status,
            "runway_months": runway_months,
            "burn_rate": burn_rate,
        }
    
    def _get_overnight_activity(self, entity_id: int, as_of: date) -> Dict:
        """Get overnight bank activity (stub)"""
        # In production, this would query bank feed data
        return {
            "inflows": Decimal("0"),
            "outflows": Decimal("0"),
            "net": Decimal("0"),
        }
    
    def _get_expected_receipts(self, entity_id: int, as_of: date) -> List[Dict]:
        """Get expected receipts for the day (stub)"""
        # In production, this would query AR aging
        return []
    
    def _get_expected_payments(self, entity_id: int, as_of: date) -> List[Dict]:
        """Get expected payments for the day (stub)"""
        # In production, this would query AP aging
        return []
    
    def _identify_attention_items(
        self,
        entity_id: int,
        cash_data: Dict,
        receipts: List[Dict],
        payments: List[Dict],
    ) -> List[Dict]:
        """Identify items requiring attention"""
        items = []
        
        # Cash position alerts
        if cash_data.get("status") == "critical":
            items.append({
                "severity": "critical",
                "type": "cash_position",
                "message": f"Cash below minimum threshold",
                "amount": str(cash_data.get("opening", 0)),
            })
        elif cash_data.get("status") == "warning":
            items.append({
                "severity": "warning",
                "type": "cash_position",
                "message": f"Cash approaching minimum threshold",
                "amount": str(cash_data.get("opening", 0)),
            })
        
        # Runway alerts
        runway = cash_data.get("runway_months", 0)
        if runway < 6:
            items.append({
                "severity": "critical" if runway < 3 else "warning",
                "type": "runway",
                "message": f"Cash runway is {runway} months",
            })
        
        return items
    
    def _check_data_quality(self, entity_id: int) -> Tuple[Dict, List[Dict]]:
        """Check data freshness and quality"""
        freshness = {
            "bank": datetime.utcnow() - timedelta(hours=2),  # Simulated
            "ar": datetime.utcnow() - timedelta(hours=12),
            "ap": datetime.utcnow() - timedelta(hours=12),
        }
        
        issues = []
        
        # Check for stale data
        now = datetime.utcnow()
        for source, last_update in freshness.items():
            age_hours = (now - last_update).total_seconds() / 3600
            if age_hours > 24:
                issues.append({
                    "type": "stale_data",
                    "source": source,
                    "message": f"{source} data is {age_hours:.0f} hours old",
                })
        
        return freshness, issues
    
    # =========================================================================
    # WEEKLY FORECAST UPDATE
    # =========================================================================
    
    def run_weekly_forecast_update(
        self,
        entity_id: int,
        plan_id: int,
        week_ending: Optional[date] = None,
    ) -> WeeklyForecastOutput:
        """
        Generate weekly forecast update.
        
        Weekly workflow that:
        - Runs new forecast with latest drivers
        - Compares to prior week's forecast
        - Identifies material changes
        - Generates CFO talking points
        """
        week_ending = week_ending or (date.today() + timedelta(days=(6 - date.today().weekday())))
        
        # Get plan and latest assumption set
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        latest_assumptions = self.db.query(AssumptionSet).filter(
            AssumptionSet.plan_id == plan_id
        ).order_by(desc(AssumptionSet.version)).first()
        
        if not latest_assumptions:
            raise ValueError(f"No assumptions found for plan {plan_id}")
        
        # Get latest actuals
        latest_actuals = self._get_latest_actuals(entity_id)
        
        # Run new forecast
        new_forecast = ForecastRun(
            plan_id=plan_id,
            assumption_set_id=latest_assumptions.id,
            actuals_snapshot_id=latest_actuals.id if latest_actuals else None,
            run_label=f"Weekly Update - {week_ending.isoformat()}",
        )
        self.db.add(new_forecast)
        self.db.commit()
        self.db.refresh(new_forecast)
        
        # Compute forecast
        self.compute_engine.run_forecast(new_forecast.id)
        self.db.refresh(new_forecast)
        
        # Get prior week's forecast
        prior_forecast = self._get_prior_forecast(plan_id, new_forecast.id)
        
        # Variance analysis
        variance_analysis = None
        if prior_forecast:
            variance_analysis = self.variance_engine.compare_forecast_vs_forecast(
                new_forecast, prior_forecast
            )
        
        # Identify material changes
        material_changes = []
        if variance_analysis:
            for item in variance_analysis.items:
                if item.is_material:
                    material_changes.append({
                        "line_item": item.line_item,
                        "period": item.period,
                        "variance": str(item.variance),
                        "variance_pct": str(item.variance_pct),
                        "is_favorable": item.is_favorable,
                    })
        
        # Generate talking points
        talking_points = []
        if variance_analysis:
            talking_points = [tp.to_dict() for tp in variance_analysis.talking_points]
        
        # Decisions required
        decisions = self._identify_decisions_required(entity_id, variance_analysis)
        
        output = WeeklyForecastOutput(
            entity_id=entity_id,
            week_ending=week_ending,
            current_forecast_id=new_forecast.id,
            prior_forecast_id=prior_forecast.id if prior_forecast else None,
            variance_analysis=variance_analysis,
            material_changes=material_changes,
            driver_changes=[],  # Would track driver changes in production
            talking_points=talking_points,
            decisions_required=decisions,
        )
        
        # Save as artifact
        self._save_artifact(
            entity_id=entity_id,
            artifact_type="weekly_forecast",
            artifact_date=week_ending,
            content=output.to_dict(),
            forecast_run_id=new_forecast.id,
        )
        
        # Save variance report
        if variance_analysis and prior_forecast:
            self.variance_engine.save_variance_report(
                entity_id=entity_id,
                analysis=variance_analysis,
                source_a_type="forecast_run",
                source_a_id=new_forecast.id,
                source_b_type="forecast_run",
                source_b_id=prior_forecast.id,
            )
        
        self._log_action(entity_id, "workflow", "weekly_forecast", new_forecast.id)
        
        return output
    
    def _get_prior_forecast(self, plan_id: int, exclude_id: int) -> Optional[ForecastRun]:
        """Get the most recent prior forecast"""
        return self.db.query(ForecastRun).filter(
            ForecastRun.plan_id == plan_id,
            ForecastRun.id != exclude_id,
        ).order_by(desc(ForecastRun.created_at)).first()
    
    def _identify_decisions_required(
        self,
        entity_id: int,
        variance_analysis: Optional[VarianceAnalysis],
    ) -> List[Dict]:
        """Identify decisions requiring human approval"""
        decisions = []
        
        if variance_analysis:
            # Check for significant unfavorable variances
            total_variance = variance_analysis.total_variance
            if total_variance < Decimal("-50000"):
                decisions.append({
                    "type": "variance_review",
                    "severity": "high",
                    "title": f"Review significant EBITDA variance of €{abs(total_variance):,.0f}",
                    "options": ["acknowledge", "investigate", "reforecast"],
                })
            
            # Check for data quality issues
            error_variances = [
                i for i in variance_analysis.items 
                if i.category.value == "error"
            ]
            if error_variances:
                decisions.append({
                    "type": "data_quality",
                    "severity": "medium",
                    "title": f"Review {len(error_variances)} potential data quality issues",
                    "options": ["fix_data", "acknowledge", "ignore"],
                })
        
        return decisions
    
    # =========================================================================
    # MONTH-END CLOSE
    # =========================================================================
    
    def run_month_end_close(
        self,
        entity_id: int,
        period_month: date,
    ) -> MonthEndCloseOutput:
        """
        Run month-end close workflow.
        
        Monthly workflow that:
        - Checks data completeness
        - Verifies reconciliations
        - Computes actual vs plan variance
        - Identifies blocking items
        """
        # Ensure period_month is first of month
        period_month = period_month.replace(day=1)
        
        # Check data completeness
        completeness_score, missing_items = self._check_completeness(entity_id, period_month)
        
        # Check reconciliation status
        recon_status, unreconciled = self._check_reconciliation_status(entity_id, period_month)
        
        # Get or create actuals snapshot
        actuals = self._get_or_create_actuals_snapshot(entity_id, period_month)
        
        # Get plan forecast for comparison
        plan_forecast = self._get_plan_forecast(entity_id, period_month)
        
        # Variance analysis
        variance_summary = {}
        if plan_forecast and actuals:
            variance_analysis = self.variance_engine.compare_actual_vs_plan(
                actuals, plan_forecast
            )
            variance_summary = {
                "total_variance": str(variance_analysis.total_variance),
                "material_count": variance_analysis.material_count,
                "favorable_count": variance_analysis.favorable_count,
                "unfavorable_count": variance_analysis.unfavorable_count,
            }
        
        # Identify blocking items
        blocking_items = []
        if completeness_score < Decimal("95"):
            blocking_items.append({
                "type": "incomplete_data",
                "message": f"Data completeness is {completeness_score}%",
            })
        
        if unreconciled:
            blocking_items.append({
                "type": "unreconciled",
                "message": f"{len(unreconciled)} items not reconciled",
            })
        
        # Get pending approvals
        pending_approvals = self._get_pending_approvals(entity_id)
        
        # Determine close status
        if blocking_items:
            close_status = "blocked"
        elif pending_approvals:
            close_status = "in_progress"
        elif actuals and actuals.locked:
            close_status = "completed"
        else:
            close_status = "ready"
        
        output = MonthEndCloseOutput(
            entity_id=entity_id,
            period_month=period_month,
            close_status=close_status,
            blocking_items=blocking_items,
            completeness_score=completeness_score,
            missing_items=missing_items,
            reconciliation_status=recon_status,
            unreconciled_items=unreconciled,
            variance_summary=variance_summary,
            pending_approvals=pending_approvals,
        )
        
        # Save as artifact
        self._save_artifact(
            entity_id=entity_id,
            artifact_type="month_end_close",
            artifact_date=period_month,
            content=output.to_dict(),
            actuals_snapshot_id=actuals.id if actuals else None,
        )
        
        self._log_action(entity_id, "workflow", "month_end_close", actuals.id if actuals else None)
        
        return output
    
    def _check_completeness(self, entity_id: int, period: date) -> Tuple[Decimal, List[Dict]]:
        """Check data completeness for period"""
        # In production, this would check actual data sources
        return Decimal("100"), []
    
    def _check_reconciliation_status(
        self,
        entity_id: int,
        period: date,
    ) -> Tuple[Dict[str, str], List[Dict]]:
        """Check reconciliation status"""
        # In production, this would check reconciliation results
        return {"bank": "complete", "ar": "complete", "ap": "complete"}, []
    
    def _get_or_create_actuals_snapshot(
        self,
        entity_id: int,
        period: date,
    ) -> Optional[ActualsSnapshot]:
        """Get or create actuals snapshot for period"""
        snapshot = self.db.query(ActualsSnapshot).filter(
            ActualsSnapshot.entity_id == entity_id,
            ActualsSnapshot.period_month == period,
        ).first()
        
        if not snapshot:
            # Create empty snapshot
            snapshot = ActualsSnapshot(
                entity_id=entity_id,
                period_month=period,
                period_label=period.strftime("%B %Y"),
            )
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)
        
        return snapshot
    
    def _get_plan_forecast(self, entity_id: int, period: date) -> Optional[ForecastRun]:
        """Get plan forecast for comparison"""
        # Find active plan that covers this period
        plan = self.db.query(Plan).filter(
            Plan.entity_id == entity_id,
            Plan.status == PlanStatus.ACTIVE,
            Plan.period_start <= period,
            Plan.period_end >= period,
        ).first()
        
        if not plan:
            return None
        
        # Get first forecast (the "plan")
        return self.db.query(ForecastRun).filter(
            ForecastRun.plan_id == plan.id,
        ).order_by(ForecastRun.created_at).first()
    
    def _get_pending_approvals(self, entity_id: int) -> List[Dict]:
        """Get pending decision approvals"""
        decisions = self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
        ).all()
        
        return [
            {
                "id": d.id,
                "type": d.decision_type,
                "title": d.title,
                "severity": d.severity,
            }
            for d in decisions
        ]
    
    # =========================================================================
    # CONTINUOUS MONITORING
    # =========================================================================
    
    def run_continuous_monitoring(
        self,
        entity_id: int,
    ) -> List[Dict]:
        """
        Run continuous monitoring checks.
        
        Periodic workflow that:
        - Monitors for anomalies
        - Checks for aging items
        - Watches forecast drift
        """
        alerts = []
        
        # Check cash position
        latest_forecast = self._get_latest_forecast(entity_id)
        if latest_forecast and latest_forecast.outputs_json:
            runway = latest_forecast.outputs_json.get("runway", {})
            runway_months = runway.get("runway_months", 12)
            
            if runway_months < 6:
                alerts.append({
                    "type": "runway_warning",
                    "severity": "critical" if runway_months < 3 else "warning",
                    "message": f"Cash runway is {runway_months} months",
                })
        
        # Check for forecast drift
        forecasts = self.db.query(ForecastRun).filter(
            ForecastRun.plan_id.in_(
                self.db.query(Plan.id).filter(
                    Plan.entity_id == entity_id,
                    Plan.status == PlanStatus.ACTIVE,
                )
            )
        ).order_by(desc(ForecastRun.created_at)).limit(5).all()
        
        if len(forecasts) >= 2:
            # Check for consistent negative drift
            ebitda_values = []
            for f in forecasts:
                if f.total_ebitda:
                    ebitda_values.append(f.total_ebitda)
            
            if len(ebitda_values) >= 3:
                # Check if trending down
                diffs = [
                    ebitda_values[i] - ebitda_values[i+1] 
                    for i in range(len(ebitda_values) - 1)
                ]
                if all(d < 0 for d in diffs):
                    alerts.append({
                        "type": "forecast_drift",
                        "severity": "warning",
                        "message": "EBITDA forecast declining week over week",
                    })
        
        # Check for overdue decisions
        overdue = self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
            FPADecision.expires_at < datetime.utcnow(),
        ).count()
        
        if overdue > 0:
            alerts.append({
                "type": "overdue_decisions",
                "severity": "high",
                "message": f"{overdue} decisions overdue for review",
            })
        
        return alerts
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_latest_forecast(self, entity_id: int) -> Optional[ForecastRun]:
        """Get the most recent forecast for entity"""
        return self.db.query(ForecastRun).join(Plan).filter(
            Plan.entity_id == entity_id,
        ).order_by(desc(ForecastRun.created_at)).first()
    
    def _get_latest_actuals(self, entity_id: int) -> Optional[ActualsSnapshot]:
        """Get the most recent actuals snapshot"""
        return self.db.query(ActualsSnapshot).filter(
            ActualsSnapshot.entity_id == entity_id,
        ).order_by(desc(ActualsSnapshot.period_month)).first()
    
    def _save_artifact(
        self,
        entity_id: int,
        artifact_type: str,
        artifact_date: date,
        content: Dict,
        plan_id: Optional[int] = None,
        forecast_run_id: Optional[int] = None,
        actuals_snapshot_id: Optional[int] = None,
    ) -> FPAArtifact:
        """Save workflow output as artifact"""
        artifact = FPAArtifact(
            entity_id=entity_id,
            artifact_type=artifact_type,
            artifact_date=artifact_date,
            content_json=content,
            plan_id=plan_id,
            forecast_run_id=forecast_run_id,
            actuals_snapshot_id=actuals_snapshot_id,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact
    
    def _log_action(
        self,
        entity_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
    ):
        """Log workflow action"""
        log = FPAAuditLog(
            entity_id=entity_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.db.add(log)
        self.db.commit()


# Type hint for return value
from typing import Tuple
