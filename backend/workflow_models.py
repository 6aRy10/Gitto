"""
First-Class Workflow Objects

- Exception: type, severity, amount, status, assignee, aging, resolution_note
- Scenario: branch from base snapshot with actions and approval
- Action: owner, expected impact, status transitions, approvals
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.orm import relationship
import datetime

# Import Base from models to ensure same declarative base
from models import Base


class ExceptionType:
    """Exception types"""
    UNMATCHED_BANK_TXN = "unmatched_bank_txn"
    SUGGESTED_MATCH_PENDING = "suggested_match_pending"
    MISSING_DUE_DATE = "missing_due_date"
    MISSING_FX_RATE = "missing_fx_rate"
    DUPLICATE_IDENTITY = "duplicate_identity"
    OUTLIER_DELAY = "outlier_delay"
    INTERCOMPANY_WASH = "intercompany_wash"
    STALE_DATA = "stale_data"
    UNEXPLAINED_CASH = "unexplained_cash"
    CASH_THRESHOLD_BREACH = "cash_threshold_breach"


class ExceptionSeverity:
    """Exception severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExceptionStatus:
    """Exception workflow states"""
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class WorkflowException(Base):
    """
    First-class Exception object.
    
    Fields:
    - type: ExceptionType
    - severity: ExceptionSeverity
    - amount: Impact amount
    - status: ExceptionStatus
    - assignee: Assigned user
    - aging: Days since creation
    - resolution_note: Resolution details
    """
    __tablename__ = "workflow_exceptions"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    
    # Exception type and severity
    exception_type = Column(String(50), nullable=False)
    severity = Column(String(20), default=ExceptionSeverity.WARNING, nullable=False)
    
    # Impact
    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="EUR")
    
    # Status workflow: OPEN -> ASSIGNED -> IN_REVIEW -> (RESOLVED | WONT_FIX)
    status = Column(String(20), default=ExceptionStatus.OPEN, nullable=False)
    
    # Assignment
    assignee = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    assigned_by = Column(String(100), nullable=True)
    
    # Aging
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Resolution
    resolution_note = Column(String(1000), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Escalation
    escalated_to = Column(String(100), nullable=True)
    escalation_reason = Column(String(200), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    
    # Evidence references (JSON array of {type, id} objects)
    evidence_refs = Column(JSON, nullable=True)
    
    # Relationships
    snapshot = relationship("Snapshot", backref="workflow_exceptions")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'assigned', 'in_review', 'escalated', 'resolved', 'wont_fix')",
            name="ck_workflow_exception_status"
        ),
        CheckConstraint(
            "severity IN ('info', 'warning', 'error', 'critical')",
            name="ck_workflow_exception_severity"
        ),
    )
    
    @property
    def aging_days(self) -> int:
        """Calculate days since exception was created."""
        if self.created_at:
            return (datetime.datetime.utcnow() - self.created_at).days
        return 0


class ScenarioStatus:
    """Scenario workflow states"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    ARCHIVED = "archived"


class WorkflowScenario(Base):
    """
    First-class Scenario object.
    
    Branches from a base snapshot with actions and approval workflow.
    """
    __tablename__ = "workflow_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    base_snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    
    # Scenario metadata
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    branch_name = Column(String(100), nullable=True)  # Git-like branch name
    
    # Status workflow: DRAFT -> PENDING_APPROVAL -> (APPROVED | REJECTED) -> ACTIVE
    status = Column(String(30), default=ScenarioStatus.DRAFT, nullable=False)
    
    # Approval workflow
    approval_required = Column(Integer, default=1)  # 0 or 1
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    rejected_by = Column(String(100), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Actions in this scenario
    actions = relationship("WorkflowAction", back_populates="scenario", cascade="all, delete-orphan")
    
    # Audit
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    base_snapshot = relationship("Snapshot", backref="workflow_scenarios")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'rejected', 'active', 'archived')",
            name="ck_workflow_scenario_status"
        ),
    )


class ActionType:
    """Action types"""
    COLLECTION_PUSH = "collection_push"
    AP_HOLD = "ap_hold"
    REVOLVER_DRAW = "revolver_draw"
    FX_HEDGE = "fx_hedge"
    PAYMENT_DELAY = "payment_delay"
    INVOICE_DISPUTE = "invoice_dispute"
    CUSTOM = "custom"


class ActionStatus:
    """Action workflow states"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkflowAction(Base):
    """
    First-class Action object.
    
    Fields:
    - owner: Action owner
    - expected_impact: Expected cash impact
    - status: ActionStatus with transitions
    - approvals: Approval chain
    """
    __tablename__ = "workflow_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("workflow_scenarios.id"), nullable=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=True)
    
    # Action metadata
    action_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Owner and assignment
    owner = Column(String(100), nullable=False)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    assigned_by = Column(String(100), nullable=True)
    
    # Expected impact
    expected_impact = Column(Float, nullable=False)  # Cash impact (positive = inflow, negative = outflow)
    expected_impact_currency = Column(String(10), default="EUR")
    expected_impact_date = Column(DateTime, nullable=True)  # When impact expected
    
    # Status workflow: DRAFT -> PENDING_APPROVAL -> APPROVED -> IN_PROGRESS -> COMPLETED
    status = Column(String(30), default=ActionStatus.DRAFT, nullable=False)
    
    # Status transitions (JSON array of {from_status, to_status, timestamp, user})
    status_transitions = Column(JSON, default=list, nullable=True)
    
    # Approvals (JSON array of {approver, approved_at, approved, reason})
    approvals = Column(JSON, default=list, nullable=True)
    
    # Target references (JSON object with type and id)
    target_ref = Column(JSON, nullable=True)  # e.g., {"type": "invoice", "id": 123}
    
    # Actual impact (filled in after completion)
    realized_impact = Column(Float, nullable=True)
    realized_impact_date = Column(DateTime, nullable=True)
    
    # Audit
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    scenario = relationship("WorkflowScenario", back_populates="actions")
    snapshot = relationship("Snapshot", backref="workflow_actions")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'rejected', 'in_progress', 'completed', 'cancelled')",
            name="ck_workflow_action_status"
        ),
    )
    
    def add_status_transition(self, from_status: str, to_status: str, user: str):
        """Add a status transition to the history."""
        if not self.status_transitions:
            self.status_transitions = []
        
        self.status_transitions.append({
            "from_status": from_status,
            "to_status": to_status,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "user": user
        })
        self.status = to_status
    
    def add_approval(self, approver: str, approved: bool, reason: str = None):
        """Add an approval to the approval chain."""
        if not self.approvals:
            self.approvals = []
        
        self.approvals.append({
            "approver": approver,
            "approved": approved,
            "approved_at": datetime.datetime.utcnow().isoformat(),
            "reason": reason
        })

