"""
FP&A Decision Queue

Human-in-the-loop decision management for FP&A workflows.
Handles approval routing, policies, and audit logging.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from fpa_models import (
    FPADecision, FPAApproval, FPAAuditLog, Plan
)

logger = logging.getLogger(__name__)


# =============================================================================
# POLICY DEFINITIONS
# =============================================================================

class ApprovalPolicy(str, Enum):
    """Approval policies for different decision types"""
    AUTO_APPROVE = "auto_approve"        # No human approval needed
    SINGLE_APPROVAL = "single_approval"  # One approver required
    DUAL_APPROVAL = "dual_approval"      # Two approvers required
    CFO_ONLY = "cfo_only"                # Only CFO can approve


@dataclass
class PolicyRule:
    """A policy rule for decision routing"""
    decision_type: str
    condition: str  # Python expression as string
    policy: ApprovalPolicy
    approver_roles: List[str]
    expiry_hours: int = 24
    
    def to_dict(self) -> Dict:
        return {
            "decision_type": self.decision_type,
            "condition": self.condition,
            "policy": self.policy.value,
            "approver_roles": self.approver_roles,
            "expiry_hours": self.expiry_hours,
        }


# Default policy rules
DEFAULT_POLICIES = [
    # Forecast approval
    PolicyRule(
        decision_type="forecast_approval",
        condition="variance_pct < 5",
        policy=ApprovalPolicy.AUTO_APPROVE,
        approver_roles=[],
    ),
    PolicyRule(
        decision_type="forecast_approval",
        condition="variance_pct >= 5 and variance_pct < 20",
        policy=ApprovalPolicy.SINGLE_APPROVAL,
        approver_roles=["fp&a_analyst", "fp&a_manager"],
        expiry_hours=24,
    ),
    PolicyRule(
        decision_type="forecast_approval",
        condition="variance_pct >= 20",
        policy=ApprovalPolicy.CFO_ONLY,
        approver_roles=["cfo"],
        expiry_hours=48,
    ),
    
    # Assumption changes
    PolicyRule(
        decision_type="assumption_change",
        condition="impact_amount < 10000",
        policy=ApprovalPolicy.SINGLE_APPROVAL,
        approver_roles=["fp&a_analyst", "fp&a_manager"],
        expiry_hours=24,
    ),
    PolicyRule(
        decision_type="assumption_change",
        condition="impact_amount >= 10000",
        policy=ApprovalPolicy.DUAL_APPROVAL,
        approver_roles=["fp&a_manager", "cfo"],
        expiry_hours=48,
    ),
    
    # Data quality issues
    PolicyRule(
        decision_type="data_quality",
        condition="severity == 'low'",
        policy=ApprovalPolicy.SINGLE_APPROVAL,
        approver_roles=["fp&a_analyst"],
        expiry_hours=72,
    ),
    PolicyRule(
        decision_type="data_quality",
        condition="severity in ['medium', 'high']",
        policy=ApprovalPolicy.SINGLE_APPROVAL,
        approver_roles=["fp&a_manager"],
        expiry_hours=24,
    ),
    
    # Scenario approval
    PolicyRule(
        decision_type="scenario_approval",
        condition="True",  # Always requires approval
        policy=ApprovalPolicy.DUAL_APPROVAL,
        approver_roles=["fp&a_manager", "cfo"],
        expiry_hours=48,
    ),
    
    # Period lock
    PolicyRule(
        decision_type="period_lock",
        condition="True",
        policy=ApprovalPolicy.CFO_ONLY,
        approver_roles=["cfo"],
        expiry_hours=72,
    ),
]


# =============================================================================
# DECISION QUEUE
# =============================================================================

@dataclass
class DecisionOption:
    """An option for a decision"""
    key: str
    label: str
    description: str
    is_recommended: bool = False
    impact_summary: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "is_recommended": self.is_recommended,
            "impact_summary": self.impact_summary,
        }


class FPADecisionQueue:
    """
    Decision queue manager.
    
    Handles:
    - Creating decisions with appropriate routing
    - Processing approvals
    - Policy enforcement
    - Audit logging
    """
    
    def __init__(self, db: Session, policies: Optional[List[PolicyRule]] = None):
        self.db = db
        self.policies = policies or DEFAULT_POLICIES
    
    def create_decision(
        self,
        entity_id: int,
        decision_type: str,
        title: str,
        description: str,
        options: List[DecisionOption],
        context: Dict[str, Any],
        recommended_option: Optional[str] = None,
        recommendation_reasoning: Optional[str] = None,
        plan_id: Optional[int] = None,
        forecast_run_id: Optional[int] = None,
        artifact_id: Optional[int] = None,
        evidence_refs: Optional[List[Dict]] = None,
    ) -> FPADecision:
        """
        Create a new decision.
        
        Routes to appropriate approvers based on policy.
        """
        # Find matching policy
        policy = self._find_matching_policy(decision_type, context)
        
        # Check for auto-approve
        if policy and policy.policy == ApprovalPolicy.AUTO_APPROVE:
            return self._create_auto_approved_decision(
                entity_id=entity_id,
                decision_type=decision_type,
                title=title,
                description=description,
                options=options,
                recommended_option=recommended_option,
            )
        
        # Determine severity based on context
        severity = self._determine_severity(decision_type, context)
        
        # Calculate expiry
        expiry_hours = policy.expiry_hours if policy else 24
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # Create decision
        decision = FPADecision(
            entity_id=entity_id,
            severity=severity,
            decision_type=decision_type,
            title=title,
            description=description,
            options_json=[o.to_dict() for o in options],
            recommended_option=recommended_option,
            recommendation_reasoning=recommendation_reasoning,
            requires_approval=True,
            policy_snapshot_json=policy.to_dict() if policy else None,
            evidence_refs_json=evidence_refs,
            plan_id=plan_id,
            forecast_run_id=forecast_run_id,
            artifact_id=artifact_id,
            expires_at=expires_at,
        )
        
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        
        # Log creation
        self._log_action(
            entity_id=entity_id,
            action="decision_created",
            resource_type="decision",
            resource_id=decision.id,
            details={
                "decision_type": decision_type,
                "policy": policy.policy.value if policy else None,
            },
        )
        
        logger.info(f"Created decision {decision.id}: {title}")
        
        return decision
    
    def _create_auto_approved_decision(
        self,
        entity_id: int,
        decision_type: str,
        title: str,
        description: str,
        options: List[DecisionOption],
        recommended_option: Optional[str],
    ) -> FPADecision:
        """Create an auto-approved decision"""
        decision = FPADecision(
            entity_id=entity_id,
            severity="low",
            decision_type=decision_type,
            title=title,
            description=description,
            options_json=[o.to_dict() for o in options],
            recommended_option=recommended_option,
            requires_approval=False,
            status="auto_approved",
            resolved_at=datetime.utcnow(),
        )
        
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        
        # Create automatic approval record
        approval = FPAApproval(
            decision_id=decision.id,
            user_id="system",
            option_selected=recommended_option or options[0].key,
            note="Auto-approved by policy",
        )
        self.db.add(approval)
        self.db.commit()
        
        # Log
        self._log_action(
            entity_id=entity_id,
            action="decision_auto_approved",
            resource_type="decision",
            resource_id=decision.id,
        )
        
        return decision
    
    def process_approval(
        self,
        decision_id: int,
        user_id: str,
        user_role: str,
        option_selected: str,
        note: Optional[str] = None,
    ) -> FPADecision:
        """
        Process an approval for a decision.
        
        Validates user role against policy and updates status.
        """
        decision = self.db.query(FPADecision).filter(
            FPADecision.id == decision_id
        ).first()
        
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        if decision.status != "pending":
            raise ValueError(f"Decision {decision_id} is not pending (status: {decision.status})")
        
        # Validate option
        valid_options = [o["key"] for o in decision.options_json]
        if option_selected not in valid_options:
            raise ValueError(f"Invalid option: {option_selected}")
        
        # Validate user role against policy
        policy_data = decision.policy_snapshot_json
        if policy_data:
            allowed_roles = policy_data.get("approver_roles", [])
            if allowed_roles and user_role not in allowed_roles:
                raise ValueError(f"User role {user_role} not authorized for this decision")
        
        # Create approval record
        approval = FPAApproval(
            decision_id=decision_id,
            user_id=user_id,
            option_selected=option_selected,
            note=note,
        )
        self.db.add(approval)
        
        # Check if enough approvals
        required_approvals = self._get_required_approvals(decision)
        current_approvals = len(decision.approvals) + 1  # Including new one
        
        if current_approvals >= required_approvals:
            # Decision is resolved
            if option_selected == "reject":
                decision.status = "rejected"
            else:
                decision.status = "approved"
            decision.resolved_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(decision)
        
        # Log
        self._log_action(
            entity_id=decision.entity_id,
            action="decision_approved" if decision.status == "approved" else "decision_voted",
            resource_type="decision",
            resource_id=decision.id,
            user_id=user_id,
            details={
                "option": option_selected,
                "status": decision.status,
            },
        )
        
        logger.info(f"Approval processed for decision {decision_id} by {user_id}: {option_selected}")
        
        return decision
    
    def dismiss_decision(
        self,
        decision_id: int,
        user_id: str,
        reason: str,
    ) -> FPADecision:
        """
        Dismiss a decision without taking action.
        
        Used when a decision is no longer relevant.
        """
        decision = self.db.query(FPADecision).filter(
            FPADecision.id == decision_id
        ).first()
        
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision.status = "dismissed"
        decision.resolved_at = datetime.utcnow()
        
        # Create dismissal record
        approval = FPAApproval(
            decision_id=decision_id,
            user_id=user_id,
            option_selected="dismiss",
            note=reason,
        )
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(decision)
        
        # Log
        self._log_action(
            entity_id=decision.entity_id,
            action="decision_dismissed",
            resource_type="decision",
            resource_id=decision.id,
            user_id=user_id,
            details={"reason": reason},
        )
        
        return decision
    
    def get_pending_decisions(
        self,
        entity_id: int,
        decision_type: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> List[FPADecision]:
        """
        Get pending decisions for an entity.
        
        Optionally filter by type or user role.
        """
        query = self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
        )
        
        if decision_type:
            query = query.filter(FPADecision.decision_type == decision_type)
        
        decisions = query.order_by(
            desc(FPADecision.severity == "critical"),
            desc(FPADecision.severity == "high"),
            FPADecision.created_at,
        ).all()
        
        # Filter by user role if specified
        if user_role:
            filtered = []
            for d in decisions:
                policy = d.policy_snapshot_json
                if policy:
                    allowed_roles = policy.get("approver_roles", [])
                    if not allowed_roles or user_role in allowed_roles:
                        filtered.append(d)
                else:
                    filtered.append(d)
            return filtered
        
        return decisions
    
    def get_expiring_decisions(
        self,
        entity_id: int,
        hours: int = 24,
    ) -> List[FPADecision]:
        """Get decisions expiring within specified hours"""
        threshold = datetime.utcnow() + timedelta(hours=hours)
        
        return self.db.query(FPADecision).filter(
            FPADecision.entity_id == entity_id,
            FPADecision.status == "pending",
            FPADecision.expires_at <= threshold,
        ).order_by(FPADecision.expires_at).all()
    
    def _find_matching_policy(
        self,
        decision_type: str,
        context: Dict[str, Any],
    ) -> Optional[PolicyRule]:
        """Find the matching policy rule for a decision"""
        for policy in self.policies:
            if policy.decision_type != decision_type:
                continue
            
            try:
                # Evaluate condition with context
                if eval(policy.condition, {"__builtins__": {}}, context):
                    return policy
            except Exception as e:
                logger.warning(f"Policy condition evaluation failed: {e}")
        
        return None
    
    def _determine_severity(self, decision_type: str, context: Dict[str, Any]) -> str:
        """Determine severity based on decision type and context"""
        if decision_type == "period_lock":
            return "critical"
        
        impact = context.get("impact_amount", 0)
        variance_pct = context.get("variance_pct", 0)
        
        if impact >= 100000 or variance_pct >= 50:
            return "critical"
        elif impact >= 50000 or variance_pct >= 20:
            return "high"
        elif impact >= 10000 or variance_pct >= 10:
            return "medium"
        else:
            return "low"
    
    def _get_required_approvals(self, decision: FPADecision) -> int:
        """Get number of required approvals for a decision"""
        policy = decision.policy_snapshot_json
        if not policy:
            return 1
        
        policy_type = policy.get("policy")
        if policy_type == "dual_approval":
            return 2
        else:
            return 1
    
    def _log_action(
        self,
        entity_id: int,
        action: str,
        resource_type: str,
        resource_id: int,
        user_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        """Log an action to audit log"""
        log = FPAAuditLog(
            entity_id=entity_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details_json=details,
        )
        self.db.add(log)
        self.db.commit()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_variance_decision(
    queue: FPADecisionQueue,
    entity_id: int,
    variance_amount: Decimal,
    variance_pct: Decimal,
    line_item: str,
    is_favorable: bool,
    forecast_run_id: int,
) -> FPADecision:
    """Create a decision for reviewing a variance"""
    direction = "favorable" if is_favorable else "unfavorable"
    
    options = [
        DecisionOption(
            key="acknowledge",
            label="Acknowledge",
            description="Acknowledge the variance as expected",
            is_recommended=is_favorable,
        ),
        DecisionOption(
            key="investigate",
            label="Investigate",
            description="Flag for investigation",
            is_recommended=not is_favorable and abs(variance_pct) > 20,
        ),
        DecisionOption(
            key="reforecast",
            label="Reforecast",
            description="Trigger a reforecast with updated assumptions",
        ),
    ]
    
    return queue.create_decision(
        entity_id=entity_id,
        decision_type="variance_review",
        title=f"Review {line_item} variance: €{abs(variance_amount):,.0f} {direction}",
        description=f"{line_item} is €{abs(variance_amount):,.0f} ({variance_pct}%) {direction} compared to forecast.",
        options=options,
        context={
            "variance_amount": float(variance_amount),
            "variance_pct": float(variance_pct),
            "is_favorable": is_favorable,
        },
        recommended_option="acknowledge" if is_favorable else "investigate",
        recommendation_reasoning=f"{'Favorable' if is_favorable else 'Unfavorable'} variance of {variance_pct}% warrants {'acknowledgment' if is_favorable else 'investigation'}.",
        forecast_run_id=forecast_run_id,
    )


def create_assumption_change_decision(
    queue: FPADecisionQueue,
    entity_id: int,
    driver_key: str,
    old_value: Any,
    new_value: Any,
    impact_amount: Decimal,
    plan_id: int,
) -> FPADecision:
    """Create a decision for approving an assumption change"""
    options = [
        DecisionOption(
            key="approve",
            label="Approve",
            description="Approve the assumption change",
            is_recommended=abs(impact_amount) < 50000,
            impact_summary=f"Impact: €{impact_amount:,.0f}",
        ),
        DecisionOption(
            key="reject",
            label="Reject",
            description="Reject the assumption change",
        ),
        DecisionOption(
            key="modify",
            label="Modify",
            description="Request modification",
        ),
    ]
    
    return queue.create_decision(
        entity_id=entity_id,
        decision_type="assumption_change",
        title=f"Approve assumption change: {driver_key}",
        description=f"Change {driver_key} from {old_value} to {new_value}. Estimated impact: €{abs(impact_amount):,.0f}.",
        options=options,
        context={
            "impact_amount": float(impact_amount),
            "driver_key": driver_key,
        },
        recommended_option="approve",
        recommendation_reasoning=f"Impact of €{abs(impact_amount):,.0f} is within acceptable range.",
        plan_id=plan_id,
    )
