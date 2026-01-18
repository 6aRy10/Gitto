"""
Continuous Monitoring Workflow

Background vigilance for anomalies, aging items, and forecast drift.
Runs every 15 minutes during business hours.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ..orchestrator import FPAOrchestrator

from ..workers.data_worker import DataWorker
from ..workers.reconciliation_worker import ReconciliationWorker
from ..workers.forecast_worker import ForecastWorker
from ..decision_queue import (
    create_cash_shortfall_decision,
    create_reconciliation_escalation_decision,
)
from ..audit_log import AuditAction

logger = logging.getLogger(__name__)


class ContinuousMonitoringWorkflow:
    """
    Continuous background monitoring.
    
    Monitors:
    - Unusual transactions (amount, counterparty, timing)
    - Reconciliation aging (7 days = warning, 30 days = escalate)
    - Forecast accuracy degradation
    - Cash runway warnings
    - Covenant compliance
    """
    
    def __init__(self, orchestrator: 'FPAOrchestrator'):
        self.orchestrator = orchestrator
        self.db = orchestrator.db
        self.entity_id = orchestrator.entity_id
        
        # Initialize workers
        self.data_worker = DataWorker(self.db, self.entity_id)
        self.recon_worker = ReconciliationWorker(self.db, self.entity_id)
        self.forecast_worker = ForecastWorker(self.db, self.entity_id)
        
        # Thresholds (configurable)
        self.large_txn_threshold = Decimal("100000")
        self.recon_warning_days = 7
        self.recon_escalate_days = 30
        self.min_runway_weeks = 8
        self.forecast_degradation_threshold = 0.10  # 10% drop in accuracy
    
    async def run(self) -> Dict[str, Any]:
        """Run continuous monitoring checks"""
        logger.info("Running continuous monitoring")
        
        alerts = []
        decisions_created = []
        
        # 1. Check for unusual transactions
        txn_alerts = self._check_unusual_transactions()
        alerts.extend(txn_alerts)
        
        # 2. Check reconciliation aging
        recon_alerts, recon_decisions = self._check_reconciliation_aging()
        alerts.extend(recon_alerts)
        decisions_created.extend(recon_decisions)
        
        # 3. Check cash runway
        runway_alerts, runway_decisions = self._check_cash_runway()
        alerts.extend(runway_alerts)
        decisions_created.extend(runway_decisions)
        
        # 4. Check forecast drift
        drift_alerts = self._check_forecast_drift()
        alerts.extend(drift_alerts)
        
        # 5. Check data freshness
        freshness_alerts = self._check_data_freshness()
        alerts.extend(freshness_alerts)
        
        # Log alerts
        for alert in alerts:
            self.orchestrator.audit_log.log(
                action=AuditAction.ALERT_TRIGGERED,
                description=alert["message"],
                details=alert,
                severity=alert.get("audit_severity", "INFO"),
            )
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": alerts,
            "decisions_created": decisions_created,
            "checks_run": [
                "unusual_transactions",
                "reconciliation_aging",
                "cash_runway",
                "forecast_drift",
                "data_freshness",
            ],
        }
        
        return result
    
    def _check_unusual_transactions(self) -> List[Dict[str, Any]]:
        """Check for unusual transactions"""
        alerts = []
        
        # Get recent transactions
        since = datetime.utcnow() - timedelta(hours=1)
        inflows = self.data_worker.get_transactions_since(since, direction="inflow")
        outflows = self.data_worker.get_transactions_since(since, direction="outflow")
        
        for txn in inflows + outflows:
            # Large transaction
            if txn.amount > self.large_txn_threshold:
                alerts.append({
                    "type": "large_transaction",
                    "severity": "info",
                    "message": f"Large {'inflow' if txn.movement_type.value == 'inflow' else 'outflow'}: €{txn.amount:,.0f}",
                    "details": {
                        "amount": str(txn.amount),
                        "counterparty": txn.counterparty,
                        "description": txn.description,
                        "transaction_id": txn.transaction_id,
                    },
                })
            
            # Unknown counterparty (new vendor/customer)
            if not txn.counterparty or txn.counterparty.lower() == "unknown":
                if txn.amount > Decimal("10000"):
                    alerts.append({
                        "type": "unknown_counterparty",
                        "severity": "warning",
                        "message": f"Transaction from unknown counterparty: €{txn.amount:,.0f}",
                        "details": {
                            "amount": str(txn.amount),
                            "description": txn.description,
                            "transaction_id": txn.transaction_id,
                        },
                    })
        
        return alerts
    
    def _check_reconciliation_aging(self) -> tuple[List[Dict], List[str]]:
        """Check for aged reconciliation items"""
        alerts = []
        decisions = []
        
        # Check warning threshold (7 days)
        warning_items = self.recon_worker.get_aged_items(days_threshold=self.recon_warning_days)
        
        # Check escalation threshold (30 days)
        escalate_items = self.recon_worker.get_aged_items(days_threshold=self.recon_escalate_days)
        
        # Warning alert
        if warning_items and len(warning_items) != len(escalate_items):
            new_warnings = len(warning_items) - len(escalate_items)
            if new_warnings > 0:
                alerts.append({
                    "type": "reconciliation_aging_warning",
                    "severity": "warning",
                    "message": f"{new_warnings} items aged {self.recon_warning_days}-{self.recon_escalate_days} days",
                    "details": {
                        "count": new_warnings,
                        "total_amount": str(sum(Decimal(str(i["amount"])) for i in warning_items[:new_warnings])),
                    },
                })
        
        # Escalation alert + decision
        if escalate_items:
            total_amount = sum(abs(Decimal(str(i["amount"]))) for i in escalate_items)
            
            alerts.append({
                "type": "reconciliation_aging_critical",
                "severity": "critical",
                "message": f"{len(escalate_items)} items aged > {self.recon_escalate_days} days",
                "details": {
                    "count": len(escalate_items),
                    "total_amount": str(total_amount),
                    "items": escalate_items[:5],  # Top 5
                },
            })
            
            # Create decision for escalation
            decision = create_reconciliation_escalation_decision(
                entity_id=self.entity_id,
                unmatched_items=escalate_items,
                total_amount=total_amount,
                days_aged=self.recon_escalate_days,
            )
            self.orchestrator.decision_queue.add_decision(decision)
            decisions.append(decision.id)
        
        return alerts, decisions
    
    def _check_cash_runway(self) -> tuple[List[Dict], List[str]]:
        """Check cash runway"""
        alerts = []
        decisions = []
        
        snapshot = self.data_worker.get_latest_snapshot()
        if not snapshot:
            return alerts, decisions
        
        runway = self.forecast_worker.get_runway(snapshot.id)
        runway_weeks = runway.get("runway_weeks", 99)
        
        if runway_weeks < self.min_runway_weeks:
            severity = "critical" if runway_weeks < 4 else "warning"
            
            alerts.append({
                "type": "low_runway",
                "severity": severity,
                "message": f"Cash runway: {runway_weeks} weeks (below {self.min_runway_weeks} week threshold)",
                "details": runway,
            })
            
            # Create shortfall decision if critical
            if runway_weeks < 4:
                min_cash = Decimal(str(runway.get("min_cash_amount", 0)))
                decision = create_cash_shortfall_decision(
                    entity_id=self.entity_id,
                    snapshot_id=snapshot.id,
                    shortfall_amount=abs(min_cash) if min_cash < 0 else Decimal("50000"),
                    shortfall_week=runway.get("min_cash_week", runway_weeks),
                    options=[
                        {
                            "label": "Immediate review required",
                            "description": "Critical cash situation requires immediate attention",
                            "risk_level": "high",
                            "risk_explanation": "Business continuity at risk",
                            "impact_amount": 0,
                            "impact_description": "Enables proactive cash management",
                            "recommended": True,
                        },
                    ],
                    recommendation="Immediate management review required",
                )
                self.orchestrator.decision_queue.add_decision(decision)
                decisions.append(decision.id)
        
        return alerts, decisions
    
    def _check_forecast_drift(self) -> List[Dict[str, Any]]:
        """Check for significant forecast drift"""
        alerts = []
        
        snapshot = self.data_worker.get_latest_snapshot()
        if not snapshot:
            return alerts
        
        # Check for regime shift
        regime = self.forecast_worker.detect_regime_shift(snapshot.id)
        
        if regime.get("regime_shift_detected"):
            alerts.append({
                "type": "regime_shift",
                "severity": "warning",
                "message": f"Regime shift detected: {regime.get('description', 'Payment patterns have changed')}",
                "details": regime,
            })
        
        # Check forecast accuracy trend
        accuracy = self.forecast_worker.get_forecast_accuracy()
        
        if accuracy.get("trend") == "declining":
            alerts.append({
                "type": "forecast_degradation",
                "severity": "warning",
                "message": f"Forecast accuracy declining: {accuracy.get('accuracy_pct', 0):.0f}%",
                "details": accuracy,
            })
        
        return alerts
    
    def _check_data_freshness(self) -> List[Dict[str, Any]]:
        """Check data freshness"""
        alerts = []
        
        freshness = self.data_worker.get_data_freshness()
        
        # Bank data stale (> 24 hours)
        bank_hours = freshness.get("bank_hours_old")
        if bank_hours and bank_hours > 24:
            alerts.append({
                "type": "bank_data_stale",
                "severity": "warning",
                "message": f"Bank data is {bank_hours:.0f} hours old",
                "details": freshness,
            })
        
        # Large mismatch between bank and ERP freshness
        mismatch = freshness.get("freshness_mismatch_hours", 0)
        if mismatch > 12:
            alerts.append({
                "type": "freshness_mismatch",
                "severity": "info",
                "message": f"Bank/ERP data freshness mismatch: {mismatch:.0f} hours",
                "details": freshness,
            })
        
        return alerts


async def run_continuous_monitoring(
    orchestrator: 'FPAOrchestrator',
    entity_id: int,
    **kwargs,
) -> Dict[str, Any]:
    """
    Entry point for continuous monitoring workflow.
    
    Called by the orchestrator.
    """
    workflow = ContinuousMonitoringWorkflow(orchestrator)
    return await workflow.run()
