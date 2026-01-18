"""
Morning Briefing Workflow

The first thing FP&A checks every morning: current cash position,
overnight activity, surprises, and items needing attention.

Runs daily at 7:00 AM (configurable).
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, TYPE_CHECKING
import logging
import uuid

if TYPE_CHECKING:
    from ..orchestrator import FPAOrchestrator

from ..workers.data_worker import DataWorker
from ..workers.reconciliation_worker import ReconciliationWorker
from ..workers.forecast_worker import ForecastWorker
from ..models.briefings import (
    MorningBriefing, CashPosition, CashMovement, AttentionItem,
    ExpectedMovement, MovementType, AttentionSeverity
)
from ..audit_log import AuditAction

logger = logging.getLogger(__name__)


class MorningBriefingWorkflow:
    """
    Generates the daily morning briefing.
    
    Output includes:
    - Current cash position vs expected
    - Overnight inflows and outflows
    - Surprises (unexpected items)
    - Today's expected movements
    - Items needing attention
    """
    
    def __init__(self, orchestrator: 'FPAOrchestrator'):
        self.orchestrator = orchestrator
        self.db = orchestrator.db
        self.entity_id = orchestrator.entity_id
        
        # Initialize workers
        self.data_worker = DataWorker(self.db, self.entity_id)
        self.recon_worker = ReconciliationWorker(self.db, self.entity_id)
        self.forecast_worker = ForecastWorker(self.db, self.entity_id)
    
    async def run(self) -> MorningBriefing:
        """Generate the morning briefing"""
        today = date.today()
        now = datetime.utcnow()
        
        logger.info(f"Generating morning briefing for {today}")
        
        # 1. Get cash position
        cash_position = self.data_worker.get_cash_position()
        
        # 2. Get overnight activity
        overnight_inflows, overnight_outflows = self.data_worker.get_overnight_transactions()
        
        # 3. Identify surprises
        surprises = self._identify_surprises(
            cash_position, overnight_inflows, overnight_outflows
        )
        
        # 4. Get today's expected movements
        expected_inflows = self.data_worker.get_expected_inflows(today, days_ahead=1)
        expected_outflows = self.data_worker.get_expected_outflows(today, days_ahead=1)
        
        # 5. Get attention items
        attention_items = self._get_attention_items()
        
        # 6. Calculate metrics
        position_vs_forecast_pct = 0.0
        if cash_position.expected_balance != 0:
            position_vs_forecast_pct = float(
                (cash_position.current_balance - cash_position.expected_balance) /
                cash_position.expected_balance * 100
            )
        
        # Create briefing
        briefing = MorningBriefing(
            id=str(uuid.uuid4()),
            entity_id=self.entity_id,
            briefing_date=today,
            generated_at=now,
            cash_position=cash_position,
            overnight_inflows=overnight_inflows,
            overnight_outflows=overnight_outflows,
            surprises=surprises,
            expected_inflows=expected_inflows,
            expected_outflows=expected_outflows,
            total_expected_inflows=sum(m.amount for m in expected_inflows),
            total_expected_outflows=sum(m.amount for m in expected_outflows),
            attention_items=attention_items,
            position_vs_forecast_pct=round(position_vs_forecast_pct, 1),
            inflow_count_overnight=len(overnight_inflows),
            outflow_count_overnight=len(overnight_outflows),
        )
        
        # Generate executive summary if LLM available
        briefing.executive_summary = self._generate_executive_summary(briefing)
        
        # Log the briefing
        self.orchestrator.audit_log.log(
            action=AuditAction.BRIEFING_GENERATED,
            description=f"Morning briefing generated: Cash €{cash_position.current_balance:,.0f}",
            details={
                "cash_position": str(cash_position.current_balance),
                "variance_pct": position_vs_forecast_pct,
                "surprises": len(surprises),
                "attention_items": len(attention_items),
            },
        )
        
        return briefing
    
    def _identify_surprises(
        self,
        cash_position: CashPosition,
        overnight_inflows: list,
        overnight_outflows: list,
    ) -> list[AttentionItem]:
        """Identify unexpected items (surprises)"""
        surprises = []
        
        # Check for significant variance from expected
        if abs(cash_position.variance_from_expected) > Decimal("10000"):
            severity = (
                AttentionSeverity.CRITICAL
                if abs(cash_position.variance_from_expected) > Decimal("50000")
                else AttentionSeverity.WARNING
            )
            
            direction = "above" if cash_position.variance_from_expected > 0 else "below"
            
            surprises.append(AttentionItem(
                severity=severity,
                title=f"Cash position €{abs(cash_position.variance_from_expected):,.0f} {direction} forecast",
                description=f"Current: €{cash_position.current_balance:,.0f}, Expected: €{cash_position.expected_balance:,.0f}",
                amount=cash_position.variance_from_expected,
                recommended_action="Review forecast assumptions and investigate variance",
            ))
        
        # Check for unexpected large transactions
        threshold = Decimal("50000")
        for txn in overnight_inflows + overnight_outflows:
            if txn.amount > threshold:
                surprises.append(AttentionItem(
                    severity=AttentionSeverity.INFO,
                    title=f"Large {'inflow' if txn.amount > 0 else 'outflow'}: €{abs(txn.amount):,.0f}",
                    description=f"{txn.counterparty or 'Unknown'}: {txn.description}",
                    amount=txn.amount,
                    recommended_action="Verify transaction is expected",
                    evidence_refs=[{"type": "bank_transaction", "id": txn.transaction_id}],
                ))
        
        return surprises
    
    def _get_attention_items(self) -> list[AttentionItem]:
        """Get items that need attention today"""
        items = []
        
        # Check for overdue invoices
        expected_inflows = self.data_worker.get_expected_inflows(
            date.today() - timedelta(days=7),
            days_ahead=7,
        )
        
        overdue = [e for e in expected_inflows if e.expected_date < date.today()]
        for exp in overdue[:5]:  # Top 5 overdue
            days_overdue = (date.today() - exp.expected_date).days
            items.append(AttentionItem(
                severity=AttentionSeverity.WARNING if days_overdue < 7 else AttentionSeverity.CRITICAL,
                title=f"{exp.counterparty} payment {days_overdue} days overdue",
                description=f"Expected €{exp.amount:,.0f} on {exp.expected_date}",
                amount=exp.amount,
                recommended_action="Follow up with customer",
                evidence_refs=[{"type": "invoice", "id": exp.invoice_id}],
            ))
        
        # Check for aged reconciliation items
        aged_items = self.recon_worker.get_aged_items(days_threshold=7)
        if aged_items:
            total_aged = sum(Decimal(str(i["amount"])) for i in aged_items)
            items.append(AttentionItem(
                severity=AttentionSeverity.WARNING,
                title=f"{len(aged_items)} unmatched items aged > 7 days",
                description=f"Total amount: €{abs(total_aged):,.0f}",
                amount=total_aged,
                recommended_action="Investigate and escalate if needed",
                evidence_refs=[{"type": "bank_transaction", "id": i["id"]} for i in aged_items[:10]],
            ))
        
        # Check runway
        snapshot = self.data_worker.get_latest_snapshot()
        if snapshot:
            runway = self.forecast_worker.get_runway(snapshot.id)
            if runway.get("runway_weeks", 99) < 8:
                items.append(AttentionItem(
                    severity=AttentionSeverity.CRITICAL,
                    title=f"Cash runway: {runway.get('runway_weeks', 0)} weeks",
                    description="Cash position projected to breach minimum threshold",
                    amount=Decimal(str(runway.get("min_cash_amount", 0))),
                    recommended_action="Review cash management options immediately",
                ))
        
        return items
    
    def _generate_executive_summary(self, briefing: MorningBriefing) -> str:
        """Generate executive summary (uses LLM if available)"""
        # For now, generate a template-based summary
        # In production, this would use the LLM reasoning layer
        
        lines = []
        lines.append(f"Morning Briefing - {briefing.briefing_date.strftime('%B %d, %Y')}")
        lines.append("")
        
        # Cash position
        pos = briefing.cash_position
        if pos.variance_from_expected >= 0:
            lines.append(f"Cash position is €{pos.current_balance:,.0f}, "
                        f"€{pos.variance_from_expected:,.0f} above forecast.")
        else:
            lines.append(f"Cash position is €{pos.current_balance:,.0f}, "
                        f"€{abs(pos.variance_from_expected):,.0f} below forecast.")
        
        # Overnight activity
        lines.append(f"Overnight: {len(briefing.overnight_inflows)} inflows "
                    f"(€{sum(m.amount for m in briefing.overnight_inflows):,.0f}), "
                    f"{len(briefing.overnight_outflows)} outflows "
                    f"(€{sum(m.amount for m in briefing.overnight_outflows):,.0f}).")
        
        # Surprises
        if briefing.surprises:
            lines.append(f"{len(briefing.surprises)} items flagged for attention.")
        
        # Today's expected
        lines.append(f"Today's expected: €{briefing.total_expected_inflows:,.0f} in, "
                    f"€{briefing.total_expected_outflows:,.0f} out.")
        
        return "\n".join(lines)


async def run_morning_briefing(
    orchestrator: 'FPAOrchestrator',
    entity_id: int,
    **kwargs,
) -> MorningBriefing:
    """
    Entry point for the morning briefing workflow.
    
    Called by the orchestrator.
    """
    workflow = MorningBriefingWorkflow(orchestrator)
    return await workflow.run()
