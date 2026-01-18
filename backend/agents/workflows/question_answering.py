"""
Question Answering Workflow

On-demand Q&A capability for FP&A questions.
Uses LLM reasoning to provide contextual answers.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..orchestrator import FPAOrchestrator

from ..workers.data_worker import DataWorker
from ..workers.reconciliation_worker import ReconciliationWorker
from ..workers.forecast_worker import ForecastWorker
from ..workers.variance_worker import VarianceWorker
from ..audit_log import AuditAction

logger = logging.getLogger(__name__)


class QuestionAnsweringWorkflow:
    """
    Answers FP&A questions using available data and LLM reasoning.
    
    Supports questions like:
    - "Why is cash down this week?"
    - "What's our forecast accuracy?"
    - "Which customers are overdue?"
    - "What's our runway?"
    """
    
    # Question patterns and handlers
    QUESTION_PATTERNS = {
        "cash_down": ["why is cash", "cash lower", "cash below", "cash down"],
        "forecast_accuracy": ["forecast accuracy", "how accurate", "prediction accuracy"],
        "overdue": ["overdue", "late payments", "aging", "past due"],
        "runway": ["runway", "how long", "cash last", "months left"],
        "variance": ["variance", "difference", "changed", "why different"],
        "forecast": ["forecast", "projection", "predict", "expected"],
        "reconciliation": ["reconciliation", "unmatched", "matching"],
        "position": ["cash position", "how much cash", "balance"],
    }
    
    def __init__(self, orchestrator: 'FPAOrchestrator'):
        self.orchestrator = orchestrator
        self.db = orchestrator.db
        self.entity_id = orchestrator.entity_id
        
        # Initialize workers
        self.data_worker = DataWorker(self.db, self.entity_id)
        self.recon_worker = ReconciliationWorker(self.db, self.entity_id)
        self.forecast_worker = ForecastWorker(self.db, self.entity_id)
        self.variance_worker = VarianceWorker(self.db, self.entity_id)
    
    async def run(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Answer an FP&A question"""
        logger.info(f"Answering question: {question[:100]}...")
        
        # Detect question type
        question_type = self._detect_question_type(question)
        
        # Gather relevant context
        data_context = self._gather_context(question_type, context)
        
        # Generate answer
        answer = self._generate_answer(question, question_type, data_context)
        
        result = {
            "question": question,
            "question_type": question_type,
            "answer": answer["text"],
            "supporting_data": answer.get("data", {}),
            "confidence": answer.get("confidence", 0.8),
            "sources": answer.get("sources", []),
            "follow_up_questions": answer.get("follow_ups", []),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return result
    
    def _detect_question_type(self, question: str) -> str:
        """Detect the type of question being asked"""
        question_lower = question.lower()
        
        for q_type, patterns in self.QUESTION_PATTERNS.items():
            if any(pattern in question_lower for pattern in patterns):
                return q_type
        
        return "general"
    
    def _gather_context(
        self,
        question_type: str,
        user_context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Gather relevant data context for the question"""
        context = {}
        
        # Always get current position and snapshot
        context["cash_position"] = self.data_worker.get_cash_position()
        snapshot = self.data_worker.get_latest_snapshot()
        context["snapshot_id"] = snapshot.id if snapshot else None
        
        # Add type-specific context
        if question_type in ["cash_down", "variance", "position"]:
            context["overnight_activity"] = self.data_worker.get_overnight_transactions()
            context["freshness"] = self.data_worker.get_data_freshness()
            if snapshot:
                context["forecast"] = self.forecast_worker.generate_forecast(snapshot.id, weeks=4)
        
        if question_type in ["forecast_accuracy", "forecast"]:
            context["accuracy"] = self.forecast_worker.get_forecast_accuracy()
            if snapshot:
                context["forecast"] = self.forecast_worker.generate_forecast(snapshot.id)
        
        if question_type in ["overdue", "reconciliation"]:
            context["recon_status"] = self.recon_worker.get_reconciliation_status()
            context["aged_items"] = self.recon_worker.get_aged_items()
            context["unmatched_summary"] = self.recon_worker.get_unmatched_summary()
        
        if question_type == "runway":
            if snapshot:
                context["runway"] = self.forecast_worker.get_runway(snapshot.id)
                context["forecast"] = self.forecast_worker.generate_forecast(snapshot.id)
        
        # Merge user-provided context
        if user_context:
            context.update(user_context)
        
        return context
    
    def _generate_answer(
        self,
        question: str,
        question_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate an answer using the gathered context"""
        
        # For now, generate template-based answers
        # In production, this would use the LLM reasoning layer
        
        handlers = {
            "cash_down": self._answer_cash_down,
            "forecast_accuracy": self._answer_forecast_accuracy,
            "overdue": self._answer_overdue,
            "runway": self._answer_runway,
            "variance": self._answer_variance,
            "forecast": self._answer_forecast,
            "reconciliation": self._answer_reconciliation,
            "position": self._answer_position,
            "general": self._answer_general,
        }
        
        handler = handlers.get(question_type, self._answer_general)
        return handler(question, context)
    
    def _answer_cash_down(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer 'why is cash down' type questions"""
        pos = context.get("cash_position")
        if not pos:
            return {"text": "Unable to retrieve cash position data.", "confidence": 0.3}
        
        variance = pos.variance_from_expected
        
        lines = []
        if variance < 0:
            lines.append(f"Cash is €{abs(variance):,.0f} below forecast due to:")
            lines.append("")
            
            # Analyze causes
            causes = []
            
            # Check overnight activity
            inflows, outflows = context.get("overnight_activity", ([], []))
            expected_inflows = context.get("expected_inflows", [])
            
            # Timing variance (expected but not received)
            if expected_inflows:
                overdue_amount = sum(
                    e.amount for e in expected_inflows
                    if hasattr(e, 'expected_date') and e.expected_date < date.today()
                )
                if overdue_amount > 0:
                    causes.append(f"TIMING (-€{overdue_amount:,.0f}): Payments expected but not yet received")
            
            # Volume variance
            expected_inflow_count = len(expected_inflows) if expected_inflows else 0
            actual_inflow_count = len(inflows)
            if actual_inflow_count < expected_inflow_count:
                causes.append(f"VOLUME: {expected_inflow_count - actual_inflow_count} fewer inflows than expected")
            
            if causes:
                for i, cause in enumerate(causes, 1):
                    lines.append(f"{i}. {cause}")
            else:
                lines.append("Investigating specific causes...")
            
            lines.append("")
            lines.append("Recommended actions:")
            lines.append("→ Review overdue invoices and follow up with customers")
        else:
            lines.append(f"Cash is actually €{variance:,.0f} above forecast.")
        
        return {
            "text": "\n".join(lines),
            "data": {"variance": str(variance), "current": str(pos.current_balance)},
            "confidence": 0.85,
            "sources": ["cash_position", "overnight_activity"],
            "follow_ups": ["Which customers are overdue?", "What's our forecast for next week?"],
        }
    
    def _answer_forecast_accuracy(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer forecast accuracy questions"""
        accuracy = context.get("accuracy", {})
        
        acc_pct = accuracy.get("accuracy_pct", 0)
        trend = accuracy.get("trend", "unknown")
        
        lines = [
            f"Forecast accuracy: {acc_pct:.0f}%",
            f"Trend: {trend}",
            "",
        ]
        
        if acc_pct >= 90:
            lines.append("This is within target range (>90%).")
        elif acc_pct >= 80:
            lines.append("This is acceptable but below target (90%).")
        else:
            lines.append("This is below acceptable threshold. Recommend reviewing forecast methodology.")
        
        return {
            "text": "\n".join(lines),
            "data": accuracy,
            "confidence": 0.9,
            "sources": ["forecast_accuracy_metrics"],
        }
    
    def _answer_overdue(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer overdue/aging questions"""
        aged = context.get("aged_items", [])
        summary = context.get("unmatched_summary", {})
        
        if not aged:
            return {
                "text": "No items are currently overdue beyond the threshold.",
                "confidence": 0.9,
            }
        
        total_amount = sum(abs(Decimal(str(i.get("amount", 0)))) for i in aged)
        
        lines = [
            f"{len(aged)} items are overdue (> 7 days):",
            f"Total amount: €{total_amount:,.0f}",
            "",
            "Top items:",
        ]
        
        for item in aged[:5]:
            lines.append(f"  • {item.get('counterparty', 'Unknown')}: €{abs(Decimal(str(item.get('amount', 0)))):,.0f} ({item.get('days_aged', 0)} days)")
        
        return {
            "text": "\n".join(lines),
            "data": {"count": len(aged), "total": str(total_amount)},
            "confidence": 0.9,
            "sources": ["reconciliation_aging"],
            "follow_ups": ["Escalate these items?"],
        }
    
    def _answer_runway(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer runway questions"""
        runway = context.get("runway", {})
        
        weeks = runway.get("runway_weeks", 0)
        min_cash = runway.get("min_cash_amount", "0")
        min_week = runway.get("min_cash_week", 0)
        
        lines = [
            f"Cash runway: {weeks} weeks",
            f"Minimum cash of €{Decimal(str(min_cash)):,.0f} projected in week {min_week}",
            "",
        ]
        
        if weeks >= 13:
            lines.append("Runway is healthy (>13 weeks).")
        elif weeks >= 8:
            lines.append("Runway is adequate but should be monitored.")
        else:
            lines.append("⚠️ Runway is concerning. Recommend reviewing cash management options.")
        
        return {
            "text": "\n".join(lines),
            "data": runway,
            "confidence": 0.85,
            "sources": ["forecast_runway"],
            "follow_ups": ["What options do we have to extend runway?"],
        }
    
    def _answer_variance(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer variance questions"""
        pos = context.get("cash_position")
        
        if not pos:
            return {"text": "Unable to analyze variance without position data.", "confidence": 0.3}
        
        variance = pos.variance_from_expected
        
        return {
            "text": f"Current variance from forecast: €{variance:,.0f} ({'favorable' if variance > 0 else 'unfavorable'})",
            "data": {"variance": str(variance)},
            "confidence": 0.8,
        }
    
    def _answer_forecast(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer general forecast questions"""
        forecast = context.get("forecast", {})
        weeks = forecast.get("weeks", [])
        
        if not weeks:
            return {"text": "Forecast data not available.", "confidence": 0.3}
        
        lines = ["13-week cash forecast (P50):"]
        for week in weeks[:4]:  # Show first 4 weeks
            lines.append(f"  Week {week['week']}: €{Decimal(str(week['p50'])):,.0f}")
        
        if len(weeks) > 4:
            lines.append(f"  ... and {len(weeks) - 4} more weeks")
        
        return {
            "text": "\n".join(lines),
            "data": {"weeks": len(weeks)},
            "confidence": 0.85,
            "sources": ["forecast"],
        }
    
    def _answer_reconciliation(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer reconciliation questions"""
        status = context.get("recon_status", {})
        
        match_pct = status.get("match_percentage", 0)
        unmatched = status.get("unmatched_transactions", 0)
        
        lines = [
            f"Reconciliation status: {match_pct:.1f}% matched",
            f"Unmatched transactions: {unmatched}",
            f"Unmatched amount: €{Decimal(str(status.get('unmatched_amount', 0))):,.0f}",
        ]
        
        return {
            "text": "\n".join(lines),
            "data": status,
            "confidence": 0.9,
            "sources": ["reconciliation_status"],
        }
    
    def _answer_position(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer cash position questions"""
        pos = context.get("cash_position")
        
        if not pos:
            return {"text": "Unable to retrieve cash position.", "confidence": 0.3}
        
        lines = [
            f"Current cash position: €{pos.current_balance:,.0f}",
            f"Expected: €{pos.expected_balance:,.0f}",
            f"Variance: €{pos.variance_from_expected:,.0f}",
        ]
        
        if pos.by_account:
            lines.append("")
            lines.append("By account:")
            for account, balance in pos.by_account.items():
                lines.append(f"  • {account}: €{balance:,.0f}")
        
        return {
            "text": "\n".join(lines),
            "data": {"current": str(pos.current_balance)},
            "confidence": 0.95,
            "sources": ["cash_position"],
        }
    
    def _answer_general(self, question: str, context: Dict) -> Dict[str, Any]:
        """Answer general questions"""
        # Provide a summary of key metrics
        pos = context.get("cash_position")
        
        lines = ["Here's a summary of key FP&A metrics:"]
        
        if pos:
            lines.append(f"• Cash position: €{pos.current_balance:,.0f}")
        
        accuracy = context.get("accuracy", {})
        if accuracy.get("accuracy_pct"):
            lines.append(f"• Forecast accuracy: {accuracy['accuracy_pct']:.0f}%")
        
        recon = context.get("recon_status", {})
        if recon.get("match_percentage"):
            lines.append(f"• Reconciliation: {recon['match_percentage']:.1f}%")
        
        lines.append("")
        lines.append("What specific aspect would you like to know more about?")
        
        return {
            "text": "\n".join(lines),
            "confidence": 0.6,
            "follow_ups": [
                "Why is cash down?",
                "What's our forecast accuracy?",
                "Which customers are overdue?",
                "What's our runway?",
            ],
        }


async def run_question_answering(
    orchestrator: 'FPAOrchestrator',
    entity_id: int,
    question: str,
    context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Entry point for question answering workflow.
    
    Called by the orchestrator.
    """
    workflow = QuestionAnsweringWorkflow(orchestrator)
    return await workflow.run(question=question, context=context)
