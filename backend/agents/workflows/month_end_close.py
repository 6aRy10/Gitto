"""
Month-End Close Workflow

Ensures data completeness, clears reconciling items, and locks the period.

Runs on the last business day of each month at 5:00 PM.
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
from ..models.briefings import AttentionItem, AttentionSeverity
from ..decision_queue import Decision, DecisionOption, DecisionCategory, DecisionPriority
from ..audit_log import AuditAction

logger = logging.getLogger(__name__)


class MonthEndCloseWorkflow:
    """
    Month-end close workflow.
    
    Steps:
    1. Check data completeness (all bank feeds, AR/AP balanced)
    2. Review aged reconciliation items
    3. Generate management report
    4. Request period lock
    """
    
    def __init__(self, orchestrator: 'FPAOrchestrator'):
        self.orchestrator = orchestrator
        self.db = orchestrator.db
        self.entity_id = orchestrator.entity_id
        
        # Initialize workers
        self.data_worker = DataWorker(self.db, self.entity_id)
        self.recon_worker = ReconciliationWorker(self.db, self.entity_id)
        self.forecast_worker = ForecastWorker(self.db, self.entity_id)
    
    async def run(self, period: Optional[str] = None) -> Dict[str, Any]:
        """Run the month-end close workflow"""
        # Determine period
        if period:
            # Parse period like "2026-01"
            year, month = map(int, period.split("-"))
            period_date = date(year, month, 1)
        else:
            # Use current month
            today = date.today()
            period_date = today.replace(day=1)
        
        period_str = period_date.strftime("%B %Y")
        logger.info(f"Running month-end close for {period_str}")
        
        # 1. Check data completeness
        completeness = self._check_completeness(period_date)
        
        # 2. Check reconciliation status
        recon_status = self._check_reconciliation(period_date)
        
        # 3. Identify blocking issues
        blocking_issues = self._identify_blocking_issues(completeness, recon_status)
        
        # 4. Generate close checklist
        checklist = self._generate_checklist(completeness, recon_status, blocking_issues)
        
        # 5. Generate management metrics
        metrics = self._calculate_period_metrics(period_date)
        
        # 6. Determine if ready for close
        ready_for_close = len(blocking_issues) == 0
        
        # 7. If not ready, create decisions for blocking items
        decision_ids = []
        if not ready_for_close:
            decision_ids = self._create_close_decisions(blocking_issues, period_str)
        
        result = {
            "period": period_str,
            "period_date": period_date.isoformat(),
            "completeness": completeness,
            "reconciliation": recon_status,
            "blocking_issues": blocking_issues,
            "checklist": checklist,
            "metrics": metrics,
            "ready_for_close": ready_for_close,
            "decision_ids": decision_ids,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        # Log
        self.orchestrator.audit_log.log(
            action=AuditAction.PERIOD_CLOSE_INITIATED,
            description=f"Month-end close initiated for {period_str}",
            details={
                "period": period_str,
                "ready_for_close": ready_for_close,
                "blocking_issues": len(blocking_issues),
            },
        )
        
        return result
    
    def _check_completeness(self, period_date: date) -> Dict[str, Any]:
        """Check data completeness for the period"""
        # Get end of period
        if period_date.month == 12:
            next_month = date(period_date.year + 1, 1, 1)
        else:
            next_month = date(period_date.year, period_date.month + 1, 1)
        period_end = next_month - timedelta(days=1)
        
        completeness = self.data_worker.check_data_completeness("month")
        freshness = self.data_worker.get_data_freshness()
        
        return {
            "period_start": period_date.isoformat(),
            "period_end": period_end.isoformat(),
            "bank_feeds": completeness.get("bank_feeds", []),
            "all_bank_feeds_current": completeness.get("all_bank_feeds_current", False),
            "ar_records": completeness.get("ar_records", 0),
            "ap_records": completeness.get("ap_records", 0),
            "bank_hours_old": freshness.get("bank_hours_old"),
            "erp_hours_old": freshness.get("erp_hours_old"),
            "is_complete": completeness.get("is_complete", False),
        }
    
    def _check_reconciliation(self, period_date: date) -> Dict[str, Any]:
        """Check reconciliation status"""
        status = self.recon_worker.get_reconciliation_status()
        unmatched = self.recon_worker.get_unmatched_summary()
        aged = self.recon_worker.get_aged_items(days_threshold=30)
        
        return {
            "match_percentage": status.get("match_percentage", 0),
            "match_amount_percentage": status.get("match_amount_percentage", 0),
            "unmatched_count": status.get("unmatched_transactions", 0),
            "unmatched_amount": status.get("unmatched_amount", "0"),
            "aged_items_count": len(aged),
            "aged_items": aged[:10],  # Top 10 for display
            "by_age_bucket": unmatched.get("buckets", {}),
        }
    
    def _identify_blocking_issues(
        self,
        completeness: Dict,
        recon_status: Dict,
    ) -> List[Dict[str, Any]]:
        """Identify issues that block period close"""
        issues = []
        
        # Bank feeds not current
        if not completeness.get("all_bank_feeds_current"):
            for feed in completeness.get("bank_feeds", []):
                if not feed.get("is_current"):
                    issues.append({
                        "type": "bank_feed_stale",
                        "severity": "critical",
                        "description": f"Bank feed '{feed['account']}' is stale",
                        "details": f"Last transaction: {feed.get('last_transaction', 'Unknown')}",
                    })
        
        # Low reconciliation rate
        if recon_status.get("match_percentage", 0) < 95:
            issues.append({
                "type": "low_reconciliation",
                "severity": "warning",
                "description": f"Reconciliation rate below 95%",
                "details": f"Current: {recon_status.get('match_percentage', 0):.1f}%",
            })
        
        # Aged unmatched items
        aged_count = recon_status.get("aged_items_count", 0)
        if aged_count > 0:
            issues.append({
                "type": "aged_items",
                "severity": "warning" if aged_count < 5 else "critical",
                "description": f"{aged_count} items aged > 30 days",
                "details": "Manual review required before close",
            })
        
        return issues
    
    def _generate_checklist(
        self,
        completeness: Dict,
        recon_status: Dict,
        blocking_issues: List,
    ) -> List[Dict[str, Any]]:
        """Generate close checklist"""
        checklist = []
        
        # Bank feeds
        checklist.append({
            "item": "Bank feeds received through period end",
            "status": "pass" if completeness.get("all_bank_feeds_current") else "fail",
            "details": f"{len([f for f in completeness.get('bank_feeds', []) if f.get('is_current')])} of {len(completeness.get('bank_feeds', []))} feeds current",
        })
        
        # Reconciliation
        match_pct = recon_status.get("match_percentage", 0)
        checklist.append({
            "item": "Bank reconciliation > 95%",
            "status": "pass" if match_pct >= 95 else "warning" if match_pct >= 90 else "fail",
            "details": f"{match_pct:.1f}% matched",
        })
        
        # Aged items
        aged_count = recon_status.get("aged_items_count", 0)
        checklist.append({
            "item": "No items aged > 30 days",
            "status": "pass" if aged_count == 0 else "warning" if aged_count < 5 else "fail",
            "details": f"{aged_count} items aged > 30 days",
        })
        
        # AR/AP balanced (placeholder - would need GL integration)
        checklist.append({
            "item": "AR subledger balanced to GL",
            "status": "pending",
            "details": "Manual verification required",
        })
        
        return checklist
    
    def _calculate_period_metrics(self, period_date: date) -> Dict[str, Any]:
        """Calculate key metrics for the period"""
        snapshot = self.data_worker.get_latest_snapshot()
        cash_position = self.data_worker.get_cash_position()
        accuracy = self.forecast_worker.get_forecast_accuracy()
        
        # Get previous period for comparison
        if period_date.month == 1:
            prev_period = date(period_date.year - 1, 12, 1)
        else:
            prev_period = date(period_date.year, period_date.month - 1, 1)
        
        return {
            "cash_balance": str(cash_position.current_balance),
            "cash_change_pct": 0,  # Would calculate vs previous period
            "dso": 0,  # Would calculate from AR data
            "dpo": 0,  # Would calculate from AP data
            "forecast_accuracy": accuracy.get("accuracy_pct", 0),
            "forecast_trend": accuracy.get("trend", "stable"),
        }
    
    def _create_close_decisions(
        self,
        blocking_issues: List[Dict],
        period_str: str,
    ) -> List[str]:
        """Create decisions for blocking issues"""
        decision_ids = []
        
        # Group issues by type
        aged_items = [i for i in blocking_issues if i["type"] == "aged_items"]
        stale_feeds = [i for i in blocking_issues if i["type"] == "bank_feed_stale"]
        
        if aged_items:
            from ..models.decisions import DecisionStatus
            
            decision = Decision.create(
                title=f"Month-End Close: {aged_items[0]['description']}",
                description=f"Reconciliation items must be resolved before closing {period_str}",
                category=DecisionCategory.PERIOD_CLOSE,
                priority=DecisionPriority.HIGH,
                entity_id=self.entity_id,
                amount_at_stake=Decimal("0"),  # Would calculate from aged items
                options=[
                    DecisionOption(
                        id="escalate",
                        label="Escalate to AR/AP team",
                        description="Send items for investigation",
                        risk_level="low",
                        risk_explanation="Standard process",
                        impact_amount=Decimal("0"),
                        impact_description="Items will be investigated",
                        recommended=True,
                        auto_executable=True,
                    ),
                    DecisionOption(
                        id="write_off",
                        label="Write off small items",
                        description="Write off items under €100",
                        risk_level="medium",
                        risk_explanation="May impact reconciliation accuracy",
                        impact_amount=Decimal("0"),
                        impact_description="Clears small items",
                        recommended=False,
                        auto_executable=False,
                    ),
                    DecisionOption(
                        id="defer",
                        label="Defer to next period",
                        description="Close period with exceptions noted",
                        risk_level="high",
                        risk_explanation="Items remain unresolved",
                        impact_amount=Decimal("0"),
                        impact_description="Close proceeds with caveats",
                        recommended=False,
                        auto_executable=False,
                    ),
                ],
                recommended_option_ids=["escalate"],
                recommendation_reasoning="Standard practice is to escalate for investigation before period close",
                source_workflow="month_end_close",
            )
            
            self.orchestrator.decision_queue.add_decision(decision)
            decision_ids.append(decision.id)
        
        return decision_ids


async def run_month_end_close(
    orchestrator: 'FPAOrchestrator',
    entity_id: int,
    period: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Entry point for the month-end close workflow.
    
    Called by the orchestrator.
    """
    workflow = MonthEndCloseWorkflow(orchestrator)
    return await workflow.run(period=period)
