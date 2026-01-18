"""
Decision Queue

Human-in-the-loop system for FP&A decisions. The AI identifies decisions,
presents options with pros/cons, makes recommendations, and waits for
human approval on high-stakes items.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json
import logging

from sqlalchemy.orm import Session

from .models.decisions import (
    Decision, DecisionOption, DecisionApproval, DecisionPolicy,
    DecisionPriority, DecisionStatus, DecisionCategory
)

logger = logging.getLogger(__name__)


class DecisionQueue:
    """
    Manages the queue of decisions awaiting human input.
    
    Decisions are stored in the database and can be:
    - Approved (with selected options)
    - Dismissed (no action taken)
    - Auto-approved (if policy allows)
    - Expired (if decision window passes)
    """
    
    def __init__(self, db: Session, entity_id: int):
        self.db = db
        self.entity_id = entity_id
        self.policy = DecisionPolicy()  # Can be loaded from DB per entity
        self._decisions: Dict[str, Decision] = {}  # In-memory cache
    
    def add_decision(self, decision: Decision) -> Decision:
        """
        Add a new decision to the queue.
        
        If auto-approval is allowed by policy, the decision may be
        auto-approved immediately.
        """
        # Check if can be auto-approved
        if self.policy.can_auto_approve(decision):
            decision.status = DecisionStatus.AUTO_APPROVED
            decision.approval = DecisionApproval(
                decision_id=decision.id,
                approved_by="system",
                approved_at=datetime.utcnow(),
                selected_options=decision.recommended_option_ids,
                notes="Auto-approved per policy",
                auto_approved=True,
            )
            logger.info(f"Decision {decision.id} auto-approved per policy")
            
            # Execute if enabled
            if self.policy.auto_execute_enabled:
                self._execute_decision(decision)
        
        # Store in database
        self._save_decision(decision)
        self._decisions[decision.id] = decision
        
        logger.info(f"Decision added: {decision.id} - {decision.title}")
        return decision
    
    def get_pending_decisions(
        self,
        priority: Optional[DecisionPriority] = None,
        category: Optional[DecisionCategory] = None,
        limit: int = 50,
    ) -> List[Decision]:
        """Get all pending decisions, optionally filtered"""
        decisions = [
            d for d in self._decisions.values()
            if d.status == DecisionStatus.PENDING
        ]
        
        if priority:
            decisions = [d for d in decisions if d.priority == priority]
        
        if category:
            decisions = [d for d in decisions if d.category == category]
        
        # Sort by priority (critical first) then by created_at
        priority_order = {
            DecisionPriority.CRITICAL: 0,
            DecisionPriority.HIGH: 1,
            DecisionPriority.MEDIUM: 2,
            DecisionPriority.LOW: 3,
        }
        decisions.sort(key=lambda d: (priority_order[d.priority], d.created_at))
        
        return decisions[:limit]
    
    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a specific decision by ID"""
        return self._decisions.get(decision_id)
    
    def approve_decision(
        self,
        decision_id: str,
        approved_by: str,
        selected_option_ids: List[str],
        notes: Optional[str] = None,
    ) -> Decision:
        """
        Approve a decision with selected options.
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        if decision.status != DecisionStatus.PENDING:
            raise ValueError(f"Decision {decision_id} is not pending (status: {decision.status})")
        
        # Validate selected options exist
        valid_option_ids = {o.id for o in decision.options}
        for opt_id in selected_option_ids:
            if opt_id not in valid_option_ids:
                raise ValueError(f"Invalid option ID: {opt_id}")
        
        # Create approval
        decision.approval = DecisionApproval(
            decision_id=decision_id,
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
            selected_options=selected_option_ids,
            notes=notes,
            auto_approved=False,
        )
        decision.status = DecisionStatus.APPROVED
        
        self._save_decision(decision)
        logger.info(f"Decision {decision_id} approved by {approved_by} with options {selected_option_ids}")
        
        return decision
    
    def dismiss_decision(
        self,
        decision_id: str,
        dismissed_by: str,
        reason: Optional[str] = None,
    ) -> Decision:
        """Dismiss a decision without taking action"""
        decision = self._decisions.get(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        if decision.status != DecisionStatus.PENDING:
            raise ValueError(f"Decision {decision_id} is not pending")
        
        decision.status = DecisionStatus.DISMISSED
        decision.approval = DecisionApproval(
            decision_id=decision_id,
            approved_by=dismissed_by,
            approved_at=datetime.utcnow(),
            selected_options=[],
            notes=reason or "Dismissed by user",
            auto_approved=False,
        )
        
        self._save_decision(decision)
        logger.info(f"Decision {decision_id} dismissed by {dismissed_by}")
        
        return decision
    
    def expire_old_decisions(self) -> List[Decision]:
        """Mark expired decisions"""
        now = datetime.utcnow()
        expired = []
        
        for decision in self._decisions.values():
            if (
                decision.status == DecisionStatus.PENDING and
                decision.expires_at and
                decision.expires_at < now
            ):
                decision.status = DecisionStatus.EXPIRED
                self._save_decision(decision)
                expired.append(decision)
                logger.info(f"Decision {decision.id} expired")
        
        return expired
    
    def get_decisions_needing_escalation(self) -> List[Decision]:
        """Get decisions that have been pending too long"""
        threshold = datetime.utcnow() - timedelta(hours=self.policy.escalate_unresolved_after_hours)
        
        return [
            d for d in self._decisions.values()
            if d.status == DecisionStatus.PENDING and d.created_at < threshold
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        all_decisions = list(self._decisions.values())
        pending = [d for d in all_decisions if d.status == DecisionStatus.PENDING]
        
        return {
            "total_decisions": len(all_decisions),
            "pending": len(pending),
            "pending_by_priority": {
                "critical": len([d for d in pending if d.priority == DecisionPriority.CRITICAL]),
                "high": len([d for d in pending if d.priority == DecisionPriority.HIGH]),
                "medium": len([d for d in pending if d.priority == DecisionPriority.MEDIUM]),
                "low": len([d for d in pending if d.priority == DecisionPriority.LOW]),
            },
            "approved_today": len([
                d for d in all_decisions
                if d.status == DecisionStatus.APPROVED and
                d.approval and d.approval.approved_at.date() == datetime.utcnow().date()
            ]),
            "auto_approved_today": len([
                d for d in all_decisions
                if d.status == DecisionStatus.AUTO_APPROVED and
                d.approval and d.approval.approved_at.date() == datetime.utcnow().date()
            ]),
            "total_amount_pending": str(sum(d.amount_at_stake for d in pending)),
        }
    
    def _save_decision(self, decision: Decision):
        """Save decision to database (placeholder - implement with actual DB model)"""
        # TODO: Implement actual database persistence
        # For now, just update in-memory cache
        self._decisions[decision.id] = decision
    
    def _load_decisions(self):
        """Load decisions from database (placeholder)"""
        # TODO: Implement actual database loading
        pass
    
    def _execute_decision(self, decision: Decision):
        """Execute an approved decision (placeholder)"""
        # TODO: Implement actual execution logic based on decision type
        decision.status = DecisionStatus.EXECUTING
        logger.info(f"Executing decision {decision.id}")


# Convenience function to create common decision types
def create_cash_shortfall_decision(
    entity_id: int,
    snapshot_id: int,
    shortfall_amount: Decimal,
    shortfall_week: int,
    options: List[Dict[str, Any]],
    recommendation: str,
) -> Decision:
    """
    Create a cash shortfall decision with standard options.
    """
    decision_options = []
    recommended_ids = []
    
    for i, opt in enumerate(options):
        opt_id = f"option_{chr(65 + i)}"  # A, B, C, etc.
        decision_option = DecisionOption(
            id=opt_id,
            label=f"{chr(65 + i)}) {opt['label']}",
            description=opt.get('description', ''),
            risk_level=opt.get('risk_level', 'medium'),
            risk_explanation=opt.get('risk_explanation', ''),
            impact_amount=Decimal(str(opt.get('impact_amount', 0))),
            impact_description=opt.get('impact_description', ''),
            recommended=opt.get('recommended', False),
            auto_executable=opt.get('auto_executable', False),
        )
        decision_options.append(decision_option)
        
        if opt.get('recommended'):
            recommended_ids.append(opt_id)
    
    return Decision.create(
        title=f"Cash Shortfall Detected - Week {shortfall_week}",
        description=f"Projected cash position €{shortfall_amount:,.2f} below minimum threshold.",
        category=DecisionCategory.CASH_SHORTFALL,
        priority=DecisionPriority.HIGH if shortfall_amount > Decimal("50000") else DecisionPriority.MEDIUM,
        entity_id=entity_id,
        snapshot_id=snapshot_id,
        amount_at_stake=shortfall_amount,
        options=decision_options,
        recommended_option_ids=recommended_ids,
        recommendation_reasoning=recommendation,
        expires_at=datetime.utcnow() + timedelta(days=3),
        source_workflow="continuous_monitoring",
    )


def create_reconciliation_escalation_decision(
    entity_id: int,
    unmatched_items: List[Dict[str, Any]],
    total_amount: Decimal,
    days_aged: int,
) -> Decision:
    """
    Create a reconciliation escalation decision.
    """
    return Decision.create(
        title=f"Reconciliation: {len(unmatched_items)} items aged > {days_aged} days",
        description=f"Total unreconciled amount: €{total_amount:,.2f}",
        category=DecisionCategory.RECONCILIATION_ESCALATION,
        priority=DecisionPriority.MEDIUM if total_amount < Decimal("10000") else DecisionPriority.HIGH,
        entity_id=entity_id,
        amount_at_stake=total_amount,
        options=[
            DecisionOption(
                id="escalate",
                label="Escalate to AR team for investigation",
                description="Send notification to AR team with item details",
                risk_level="low",
                risk_explanation="Standard process",
                impact_amount=total_amount,
                impact_description="Items will be investigated",
                recommended=True,
                auto_executable=True,
            ),
            DecisionOption(
                id="dismiss",
                label="Dismiss - will self-resolve",
                description="Take no action, items expected to match soon",
                risk_level="medium",
                risk_explanation="May miss actual issues",
                impact_amount=Decimal("0"),
                impact_description="No action taken",
                recommended=False,
                auto_executable=False,
            ),
        ],
        recommended_option_ids=["escalate"],
        recommendation_reasoning="Items have been unmatched for an extended period. Standard practice is to escalate for investigation.",
        source_workflow="continuous_monitoring",
        evidence_refs=[{"type": "unmatched_item", "ids": [i.get("id") for i in unmatched_items]}],
    )
