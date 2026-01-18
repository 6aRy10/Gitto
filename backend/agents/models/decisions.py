"""
Decision Models

Data structures for the Decision Queue system - where the AI surfaces
decisions that need human input, presents options, and tracks approvals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from decimal import Decimal
import uuid


class DecisionPriority(str, Enum):
    """Priority levels for decisions"""
    CRITICAL = "critical"  # Requires immediate attention
    HIGH = "high"          # Should be addressed today
    MEDIUM = "medium"      # Can wait a few days
    LOW = "low"            # Informational


class DecisionStatus(str, Enum):
    """Status of a decision"""
    PENDING = "pending"           # Awaiting human decision
    APPROVED = "approved"         # Human approved an option
    DISMISSED = "dismissed"       # Human dismissed (no action)
    AUTO_APPROVED = "auto_approved"  # System auto-approved per policy
    EXPIRED = "expired"           # Decision window passed
    EXECUTING = "executing"       # Action in progress
    COMPLETED = "completed"       # Action completed successfully
    FAILED = "failed"             # Action failed


class DecisionCategory(str, Enum):
    """Categories of FP&A decisions"""
    CASH_SHORTFALL = "cash_shortfall"
    PAYMENT_TIMING = "payment_timing"
    COLLECTION_ACCELERATION = "collection_acceleration"
    CREDIT_LINE = "credit_line"
    RECONCILIATION_ESCALATION = "reconciliation_escalation"
    ANOMALY_INVESTIGATION = "anomaly_investigation"
    FORECAST_ADJUSTMENT = "forecast_adjustment"
    VENDOR_NEGOTIATION = "vendor_negotiation"
    PERIOD_CLOSE = "period_close"
    OTHER = "other"


@dataclass
class DecisionOption:
    """A single option within a decision"""
    id: str
    label: str                          # e.g., "A) Delay TechVendor payment"
    description: str                    # Detailed explanation
    risk_level: str                     # "low", "medium", "high"
    risk_explanation: str               # Why this risk level
    impact_amount: Decimal              # € impact
    impact_description: str             # What this achieves
    recommended: bool = False           # Is this the AI's recommendation?
    auto_executable: bool = False       # Can be auto-executed if policy allows
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "risk_level": self.risk_level,
            "risk_explanation": self.risk_explanation,
            "impact_amount": str(self.impact_amount),
            "impact_description": self.impact_description,
            "recommended": self.recommended,
            "auto_executable": self.auto_executable,
            "metadata": self.metadata,
        }


@dataclass
class DecisionApproval:
    """Record of a decision approval/dismissal"""
    decision_id: str
    approved_by: str                    # User ID or "system"
    approved_at: datetime
    selected_options: List[str]         # Option IDs that were approved
    notes: Optional[str] = None
    auto_approved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat(),
            "selected_options": self.selected_options,
            "notes": self.notes,
            "auto_approved": self.auto_approved,
        }


@dataclass
class Decision:
    """
    A decision that needs human input.
    
    The AI identifies situations, presents options with pros/cons,
    makes a recommendation, and waits for approval on high-stakes items.
    """
    id: str
    title: str
    description: str
    category: DecisionCategory
    priority: DecisionPriority
    status: DecisionStatus
    
    # Financial context
    entity_id: int
    snapshot_id: Optional[int]
    amount_at_stake: Decimal            # Total € involved
    
    # Options
    options: List[DecisionOption]
    recommended_option_ids: List[str]   # AI's recommendation
    recommendation_reasoning: str        # Why AI recommends this
    
    # Timing
    created_at: datetime
    expires_at: Optional[datetime]      # When decision window closes
    
    # Resolution
    approval: Optional[DecisionApproval] = None
    execution_result: Optional[Dict[str, Any]] = None
    
    # Metadata
    source_workflow: str = ""           # Which workflow created this
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        category: DecisionCategory,
        priority: DecisionPriority,
        entity_id: int,
        amount_at_stake: Decimal,
        options: List[DecisionOption],
        recommended_option_ids: List[str],
        recommendation_reasoning: str,
        snapshot_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        source_workflow: str = "",
        evidence_refs: List[Dict[str, Any]] = None,
    ) -> 'Decision':
        """Factory method to create a new decision"""
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=DecisionStatus.PENDING,
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            amount_at_stake=amount_at_stake,
            options=options,
            recommended_option_ids=recommended_option_ids,
            recommendation_reasoning=recommendation_reasoning,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            source_workflow=source_workflow,
            evidence_refs=evidence_refs or [],
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "entity_id": self.entity_id,
            "snapshot_id": self.snapshot_id,
            "amount_at_stake": str(self.amount_at_stake),
            "options": [o.to_dict() for o in self.options],
            "recommended_option_ids": self.recommended_option_ids,
            "recommendation_reasoning": self.recommendation_reasoning,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "approval": self.approval.to_dict() if self.approval else None,
            "execution_result": self.execution_result,
            "source_workflow": self.source_workflow,
            "evidence_refs": self.evidence_refs,
            "metadata": self.metadata,
        }


@dataclass
class DecisionPolicy:
    """
    Policies that govern auto-approval and decision routing.
    
    These can be configured per entity or globally.
    """
    # Auto-approve thresholds
    auto_approve_reconciliation_under: Decimal = Decimal("1000")  # €
    auto_approve_payment_delay_days: int = 3
    auto_approve_forecast_adjustment_pct: float = 0.05  # 5%
    
    # Always require human approval for these
    require_approval_amount_over: Decimal = Decimal("10000")  # €
    require_approval_for_categories: List[DecisionCategory] = field(
        default_factory=lambda: [
            DecisionCategory.CREDIT_LINE,
            DecisionCategory.VENDOR_NEGOTIATION,
        ]
    )
    
    # Escalation settings
    escalate_unresolved_after_hours: int = 24
    escalate_to_roles: List[str] = field(default_factory=lambda: ["cfo", "controller"])
    
    # Feature flags
    auto_execute_enabled: bool = False  # If True, auto-approved decisions are executed
    
    def can_auto_approve(self, decision: Decision) -> bool:
        """Check if a decision can be auto-approved per policy"""
        # Never auto-approve high-stakes decisions
        if decision.amount_at_stake > self.require_approval_amount_over:
            return False
        
        # Never auto-approve certain categories
        if decision.category in self.require_approval_for_categories:
            return False
        
        # Check category-specific rules
        if decision.category == DecisionCategory.RECONCILIATION_ESCALATION:
            return decision.amount_at_stake <= self.auto_approve_reconciliation_under
        
        # Default: require approval
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "auto_approve_reconciliation_under": str(self.auto_approve_reconciliation_under),
            "auto_approve_payment_delay_days": self.auto_approve_payment_delay_days,
            "auto_approve_forecast_adjustment_pct": self.auto_approve_forecast_adjustment_pct,
            "require_approval_amount_over": str(self.require_approval_amount_over),
            "require_approval_for_categories": [c.value for c in self.require_approval_for_categories],
            "escalate_unresolved_after_hours": self.escalate_unresolved_after_hours,
            "escalate_to_roles": self.escalate_to_roles,
            "auto_execute_enabled": self.auto_execute_enabled,
        }
