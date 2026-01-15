"""
Finance-Native Collaboration Service
"GitHub for Cash" - Core workflow logic for treasury collaboration.

Implements:
- Snapshot workflows (DRAFT → READY_FOR_REVIEW → LOCKED)
- Exception management (assign, resolve, escalate)
- Match approval (suggested matches never auto-apply)
- Scenario workflows (DRAFT → PROPOSED → APPROVED)
- Action workflows (DRAFT → PENDING_APPROVAL → APPROVED → IN_PROGRESS → DONE)
- Comments with evidence links
- Invariant enforcement
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException
import json

import models
from models import (
    CollaborationSnapshot, SnapshotStatus,
    CollaborationException, ExceptionType, ExceptionStatus,
    CollaborationMatch, MatchType, MatchStatus, MatchAllocation,
    CollaborationScenario, ScenarioStatus,
    CollaborationAction, ActionType, ActionStatus,
    CollaborationComment, EvidenceLink,
    WeeklyPack, CollaborationAuditLog
)
from rbac_service import has_permission, LOCK_CAPABLE_ROLES


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def log_collaboration_action(
    db: Session,
    user_id: str,
    user_role: str,
    action: str,
    resource_type: str,
    resource_id: int,
    snapshot_id: Optional[int] = None,
    entity_id: Optional[int] = None,
    changes: Optional[Dict] = None,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """Log all collaboration actions for audit trail."""
    log = CollaborationAuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        snapshot_id=snapshot_id,
        entity_id=entity_id,
        changes_json=changes,
        notes=notes,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()
    return log


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════════

def create_snapshot(
    db: Session,
    entity_id: int,
    bank_as_of: datetime,
    created_by: str,
    erp_as_of: Optional[datetime] = None,
    fx_version: Optional[str] = None
) -> CollaborationSnapshot:
    """
    Create a new snapshot from latest sync.
    Snapshot starts in DRAFT status.
    """
    snapshot = CollaborationSnapshot(
        entity_id=entity_id,
        status=SnapshotStatus.DRAFT,
        bank_as_of=bank_as_of,
        erp_as_of=erp_as_of,
        fx_version=fx_version,
        created_by=created_by
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    log_collaboration_action(
        db, created_by, None, "create", "snapshot", snapshot.id,
        snapshot_id=snapshot.id, entity_id=entity_id
    )
    
    return snapshot


def mark_snapshot_ready(
    db: Session,
    snapshot_id: int,
    user_id: str,
    user_role: str
) -> CollaborationSnapshot:
    """
    Mark snapshot as ready for review.
    Validates all critical exceptions are resolved.
    """
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    if snapshot.is_locked:
        raise HTTPException(status_code=400, detail="Cannot modify locked snapshot")
    
    if snapshot.status != SnapshotStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Snapshot must be in DRAFT status")
    
    # Check for blocking exceptions
    critical_exceptions = db.query(CollaborationException).filter(
        CollaborationException.snapshot_id == snapshot_id,
        CollaborationException.severity == "critical",
        CollaborationException.status.in_([ExceptionStatus.OPEN, ExceptionStatus.IN_REVIEW])
    ).count()
    
    if critical_exceptions > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark ready: {critical_exceptions} critical exceptions unresolved"
        )
    
    old_status = snapshot.status
    snapshot.status = SnapshotStatus.READY_FOR_REVIEW
    snapshot.ready_at = datetime.utcnow()
    snapshot.ready_by = user_id
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "ready", "snapshot", snapshot_id,
        snapshot_id=snapshot_id, entity_id=snapshot.entity_id,
        changes={"status": {"old": old_status, "new": SnapshotStatus.READY_FOR_REVIEW}}
    )
    
    return snapshot


def lock_snapshot(
    db: Session,
    snapshot_id: int,
    user_id: str,
    user_role: str,
    lock_reason: str
) -> CollaborationSnapshot:
    """
    Lock snapshot - CFO only.
    Locked snapshots are IMMUTABLE (enforced by DB constraint + app check).
    """
    # Hard rule: Only CFO can lock
    if user_role not in LOCK_CAPABLE_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Only {', '.join(LOCK_CAPABLE_ROLES)} can lock snapshots"
        )
    
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    if snapshot.is_locked:
        raise HTTPException(status_code=400, detail="Snapshot already locked")
    
    if snapshot.status != SnapshotStatus.READY_FOR_REVIEW:
        raise HTTPException(status_code=400, detail="Snapshot must be READY_FOR_REVIEW before locking")
    
    # Lock the snapshot
    snapshot.status = SnapshotStatus.LOCKED
    snapshot.is_locked = 1
    snapshot.locked_by = user_id
    snapshot.locked_at = datetime.utcnow()
    snapshot.lock_reason = lock_reason
    
    # Freeze policies at lock time
    snapshot.policies_json = _capture_policies(db, snapshot.entity_id)
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "lock", "snapshot", snapshot_id,
        snapshot_id=snapshot_id, entity_id=snapshot.entity_id,
        changes={"is_locked": {"old": 0, "new": 1}, "lock_reason": lock_reason}
    )
    
    return snapshot


def _capture_policies(db: Session, entity_id: int) -> Dict:
    """Capture current policies for snapshot freeze."""
    # Get matching policies
    policies = db.query(models.MatchingPolicy).filter(
        or_(
            models.MatchingPolicy.entity_id == entity_id,
            models.MatchingPolicy.entity_id.is_(None)
        )
    ).all()
    
    return {
        "matching_policies": [
            {
                "id": p.id,
                "amount_tolerance": p.amount_tolerance,
                "date_window_days": p.date_window_days,
                "deterministic_enabled": p.deterministic_enabled,
                "rules_enabled": p.rules_enabled,
                "suggested_enabled": p.suggested_enabled
            }
            for p in policies
        ],
        "captured_at": datetime.utcnow().isoformat()
    }


def compare_snapshots(
    db: Session,
    snapshot_a_id: int,
    snapshot_b_id: int
) -> Dict[str, Any]:
    """
    Compare two snapshots - variance "diff" view.
    Returns changes categorized by type.
    """
    snapshot_a = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_a_id
    ).first()
    snapshot_b = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_b_id
    ).first()
    
    if not snapshot_a or not snapshot_b:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return {
        "snapshot_a": {
            "id": snapshot_a.id,
            "status": snapshot_a.status,
            "bank_as_of": snapshot_a.bank_as_of.isoformat() if snapshot_a.bank_as_of else None,
            "total_bank_balance": snapshot_a.total_bank_balance,
            "cash_explained_pct": snapshot_a.cash_explained_pct,
            "unknown_bucket_amount": snapshot_a.unknown_bucket_amount,
            "exception_count": snapshot_a.exception_count
        },
        "snapshot_b": {
            "id": snapshot_b.id,
            "status": snapshot_b.status,
            "bank_as_of": snapshot_b.bank_as_of.isoformat() if snapshot_b.bank_as_of else None,
            "total_bank_balance": snapshot_b.total_bank_balance,
            "cash_explained_pct": snapshot_b.cash_explained_pct,
            "unknown_bucket_amount": snapshot_b.unknown_bucket_amount,
            "exception_count": snapshot_b.exception_count
        },
        "deltas": {
            "bank_balance_delta": snapshot_b.total_bank_balance - snapshot_a.total_bank_balance,
            "cash_explained_delta": snapshot_b.cash_explained_pct - snapshot_a.cash_explained_pct,
            "unknown_bucket_delta": snapshot_b.unknown_bucket_amount - snapshot_a.unknown_bucket_amount,
            "exception_count_delta": snapshot_b.exception_count - snapshot_a.exception_count
        }
    }


def assert_snapshot_not_locked(snapshot: CollaborationSnapshot):
    """
    INVARIANT: Locked snapshots are immutable.
    Call this before any modification.
    """
    if snapshot.is_locked:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify locked snapshot. Locked snapshots are immutable."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════════

def get_exceptions(
    db: Session,
    snapshot_id: int,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    assignee_id: Optional[str] = None
) -> List[CollaborationException]:
    """Get exceptions for a snapshot with optional filters."""
    query = db.query(CollaborationException).filter(
        CollaborationException.snapshot_id == snapshot_id
    )
    
    if status:
        query = query.filter(CollaborationException.status == status)
    if severity:
        query = query.filter(CollaborationException.severity == severity)
    if assignee_id:
        query = query.filter(CollaborationException.assignee_id == assignee_id)
    
    return query.order_by(
        CollaborationException.severity.desc(),
        CollaborationException.created_at.desc()
    ).all()


def assign_exception(
    db: Session,
    exception_id: int,
    assignee_id: str,
    user_id: str,
    user_role: str,
    sla_hours: int = 24
) -> CollaborationException:
    """Assign exception to a user."""
    exception = db.query(CollaborationException).filter(
        CollaborationException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    # Check snapshot not locked
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == exception.snapshot_id
    ).first()
    assert_snapshot_not_locked(snapshot)
    
    old_assignee = exception.assignee_id
    old_status = exception.status
    
    exception.assignee_id = assignee_id
    exception.assigned_at = datetime.utcnow()
    exception.assigned_by = user_id
    exception.sla_due_at = datetime.utcnow() + timedelta(hours=sla_hours)
    
    if exception.status == ExceptionStatus.OPEN:
        exception.status = ExceptionStatus.IN_REVIEW
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "assign", "exception", exception_id,
        snapshot_id=exception.snapshot_id,
        changes={
            "assignee_id": {"old": old_assignee, "new": assignee_id},
            "status": {"old": old_status, "new": exception.status}
        }
    )
    
    return exception


def resolve_exception(
    db: Session,
    exception_id: int,
    resolution_type: str,
    resolution_note: str,
    user_id: str,
    user_role: str
) -> CollaborationException:
    """Resolve an exception."""
    exception = db.query(CollaborationException).filter(
        CollaborationException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    # Check snapshot not locked
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == exception.snapshot_id
    ).first()
    assert_snapshot_not_locked(snapshot)
    
    old_status = exception.status
    
    exception.status = ExceptionStatus.RESOLVED
    exception.resolution_type = resolution_type
    exception.resolution_note = resolution_note
    exception.resolved_by = user_id
    exception.resolved_at = datetime.utcnow()
    
    # Update snapshot exception count
    snapshot.exception_count = db.query(CollaborationException).filter(
        CollaborationException.snapshot_id == exception.snapshot_id,
        CollaborationException.status.in_([ExceptionStatus.OPEN, ExceptionStatus.IN_REVIEW])
    ).count()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "resolve", "exception", exception_id,
        snapshot_id=exception.snapshot_id,
        changes={"status": {"old": old_status, "new": ExceptionStatus.RESOLVED}}
    )
    
    return exception


def escalate_exception(
    db: Session,
    exception_id: int,
    escalate_to: str,
    reason: str,
    user_id: str,
    user_role: str
) -> CollaborationException:
    """Escalate an exception."""
    exception = db.query(CollaborationException).filter(
        CollaborationException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    old_status = exception.status
    
    exception.status = ExceptionStatus.ESCALATED
    exception.escalated_to = escalate_to
    exception.escalation_reason = reason
    exception.escalated_at = datetime.utcnow()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "escalate", "exception", exception_id,
        snapshot_id=exception.snapshot_id,
        changes={"status": {"old": old_status, "new": ExceptionStatus.ESCALATED}}
    )
    
    return exception


# ═══════════════════════════════════════════════════════════════════════════════
# RECONCILIATION / MATCH WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════════

def get_unmatched_transactions(
    db: Session,
    snapshot_id: int,
    limit: int = 100
) -> List[models.BankTransaction]:
    """Get unmatched bank transactions for reconciliation queue."""
    # Get transactions that don't have reconciled matches
    matched_txn_ids = db.query(MatchAllocation.bank_transaction_id).join(
        CollaborationMatch
    ).filter(
        CollaborationMatch.snapshot_id == snapshot_id,
        CollaborationMatch.status == MatchStatus.RECONCILED
    ).distinct()
    
    return db.query(models.BankTransaction).filter(
        ~models.BankTransaction.id.in_(matched_txn_ids),
        models.BankTransaction.is_reconciled == 0
    ).order_by(
        models.BankTransaction.transaction_date.desc()
    ).limit(limit).all()


def get_suggested_matches(
    db: Session,
    snapshot_id: int
) -> List[CollaborationMatch]:
    """Get suggested matches pending approval."""
    return db.query(CollaborationMatch).filter(
        CollaborationMatch.snapshot_id == snapshot_id,
        CollaborationMatch.match_type == MatchType.SUGGESTED,
        CollaborationMatch.status == MatchStatus.PENDING_APPROVAL
    ).order_by(
        CollaborationMatch.confidence.desc()
    ).all()


def approve_match(
    db: Session,
    match_id: int,
    user_id: str,
    user_role: str
) -> CollaborationMatch:
    """
    Approve a suggested match.
    INVARIANT: Suggested matches NEVER auto-apply - must be explicitly approved.
    """
    match = db.query(CollaborationMatch).filter(
        CollaborationMatch.id == match_id
    ).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Check snapshot not locked
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == match.snapshot_id
    ).first()
    assert_snapshot_not_locked(snapshot)
    
    if match.status != MatchStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Match is not pending approval")
    
    old_status = match.status
    
    match.status = MatchStatus.RECONCILED
    match.approved_by = user_id
    match.approved_at = datetime.utcnow()
    
    # Mark underlying transactions as reconciled
    for allocation in match.allocations:
        txn = db.query(models.BankTransaction).filter(
            models.BankTransaction.id == allocation.bank_transaction_id
        ).first()
        if txn:
            txn.is_reconciled = 1
            txn.reconciliation_type = match.match_type
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "approve", "match", match_id,
        snapshot_id=match.snapshot_id,
        changes={"status": {"old": old_status, "new": MatchStatus.RECONCILED}}
    )
    
    return match


def reject_match(
    db: Session,
    match_id: int,
    reason: str,
    user_id: str,
    user_role: str
) -> CollaborationMatch:
    """Reject a suggested match."""
    match = db.query(CollaborationMatch).filter(
        CollaborationMatch.id == match_id
    ).first()
    
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    old_status = match.status
    
    match.status = MatchStatus.REJECTED
    match.rejection_reason = reason
    match.approved_by = user_id  # Track who rejected
    match.approved_at = datetime.utcnow()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "reject", "match", match_id,
        snapshot_id=match.snapshot_id,
        changes={"status": {"old": old_status, "new": MatchStatus.REJECTED}}
    )
    
    return match


def create_allocation(
    db: Session,
    snapshot_id: int,
    bank_transaction_id: int,
    allocations: List[Dict],  # [{invoice_id, amount} or {vendor_bill_id, amount}]
    user_id: str,
    user_role: str,
    match_type: str = MatchType.MANUAL
) -> CollaborationMatch:
    """
    Create manual allocations (split transaction across invoices).
    
    INVARIANTS:
    - Sum of allocations == transaction amount
    - Each invoice allocation <= invoice open amount
    """
    # Get transaction
    txn = db.query(models.BankTransaction).filter(
        models.BankTransaction.id == bank_transaction_id
    ).first()
    
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Validate allocation sum == transaction amount
    total_allocated = sum(a.get("amount", 0) for a in allocations)
    if abs(total_allocated - abs(txn.amount)) > 0.01:  # Allow 1 cent tolerance
        raise HTTPException(
            status_code=400,
            detail=f"Allocation sum ({total_allocated}) must equal transaction amount ({abs(txn.amount)})"
        )
    
    # Validate each invoice allocation
    for alloc in allocations:
        if "invoice_id" in alloc:
            invoice = db.query(models.Invoice).filter(
                models.Invoice.id == alloc["invoice_id"]
            ).first()
            if invoice and alloc["amount"] > invoice.amount:
                raise HTTPException(
                    status_code=400,
                    detail=f"Allocation {alloc['amount']} exceeds invoice amount {invoice.amount}"
                )
    
    # Create match
    match = CollaborationMatch(
        snapshot_id=snapshot_id,
        match_type=match_type,
        status=MatchStatus.RECONCILED if match_type != MatchType.SUGGESTED else MatchStatus.PENDING_APPROVAL,
        created_by=user_id,
        approved_by=user_id if match_type != MatchType.SUGGESTED else None,
        approved_at=datetime.utcnow() if match_type != MatchType.SUGGESTED else None
    )
    db.add(match)
    db.flush()
    
    # Create allocations
    for alloc in allocations:
        allocation = MatchAllocation(
            match_id=match.id,
            bank_transaction_id=bank_transaction_id,
            invoice_id=alloc.get("invoice_id"),
            vendor_bill_id=alloc.get("vendor_bill_id"),
            allocated_amount=alloc["amount"],
            currency=txn.currency
        )
        db.add(allocation)
    
    # Mark transaction as reconciled
    if match_type != MatchType.SUGGESTED:
        txn.is_reconciled = 1
        txn.reconciliation_type = match_type
    
    db.commit()
    db.refresh(match)
    
    log_collaboration_action(
        db, user_id, user_role, "allocate", "match", match.id,
        snapshot_id=snapshot_id,
        changes={"allocations": allocations}
    )
    
    return match


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════════

def create_scenario(
    db: Session,
    base_snapshot_id: int,
    name: str,
    description: str,
    assumptions: Dict,
    user_id: str,
    user_role: str
) -> CollaborationScenario:
    """Create a new scenario from base snapshot."""
    scenario = CollaborationScenario(
        base_snapshot_id=base_snapshot_id,
        name=name,
        description=description,
        assumptions_json=assumptions,
        status=ScenarioStatus.DRAFT,
        created_by=user_id
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    log_collaboration_action(
        db, user_id, user_role, "create", "scenario", scenario.id,
        snapshot_id=base_snapshot_id,
        changes={"name": name, "assumptions": assumptions}
    )
    
    return scenario


def submit_scenario(
    db: Session,
    scenario_id: int,
    user_id: str,
    user_role: str
) -> CollaborationScenario:
    """Submit scenario for approval."""
    scenario = db.query(CollaborationScenario).filter(
        CollaborationScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if scenario.status != ScenarioStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only submit draft scenarios")
    
    old_status = scenario.status
    
    scenario.status = ScenarioStatus.PROPOSED
    scenario.submitted_by = user_id
    scenario.submitted_at = datetime.utcnow()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "submit", "scenario", scenario_id,
        snapshot_id=scenario.base_snapshot_id,
        changes={"status": {"old": old_status, "new": ScenarioStatus.PROPOSED}}
    )
    
    return scenario


def approve_scenario(
    db: Session,
    scenario_id: int,
    user_id: str,
    user_role: str
) -> CollaborationScenario:
    """Approve scenario (CFO only)."""
    if user_role not in LOCK_CAPABLE_ROLES:
        raise HTTPException(status_code=403, detail="Only CFO can approve scenarios")
    
    scenario = db.query(CollaborationScenario).filter(
        CollaborationScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if scenario.status != ScenarioStatus.PROPOSED:
        raise HTTPException(status_code=400, detail="Can only approve proposed scenarios")
    
    old_status = scenario.status
    
    scenario.status = ScenarioStatus.APPROVED
    scenario.approved_by = user_id
    scenario.approved_at = datetime.utcnow()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "approve", "scenario", scenario_id,
        snapshot_id=scenario.base_snapshot_id,
        changes={"status": {"old": old_status, "new": ScenarioStatus.APPROVED}}
    )
    
    return scenario


def reject_scenario(
    db: Session,
    scenario_id: int,
    reason: str,
    user_id: str,
    user_role: str
) -> CollaborationScenario:
    """Reject scenario."""
    scenario = db.query(CollaborationScenario).filter(
        CollaborationScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    old_status = scenario.status
    
    scenario.status = ScenarioStatus.REJECTED
    scenario.rejection_reason = reason
    scenario.approved_by = user_id
    scenario.approved_at = datetime.utcnow()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "reject", "scenario", scenario_id,
        snapshot_id=scenario.base_snapshot_id,
        changes={"status": {"old": old_status, "new": ScenarioStatus.REJECTED}}
    )
    
    return scenario


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════════

def create_action(
    db: Session,
    action_type: str,
    description: str,
    owner_id: str,
    expected_impact: Dict,
    user_id: str,
    user_role: str,
    scenario_id: Optional[int] = None,
    snapshot_id: Optional[int] = None,
    target_refs: Optional[List[Dict]] = None,
    due_date: Optional[datetime] = None,
    requires_approval: bool = True
) -> CollaborationAction:
    """Create a new action."""
    if not scenario_id and not snapshot_id:
        raise HTTPException(status_code=400, detail="Must specify scenario_id or snapshot_id")
    
    action = CollaborationAction(
        scenario_id=scenario_id,
        snapshot_id=snapshot_id,
        action_type=action_type,
        description=description,
        target_refs=target_refs,
        owner_id=owner_id,
        due_date=due_date,
        expected_cash_impact_json=expected_impact,
        status=ActionStatus.DRAFT,
        requires_approval=1 if requires_approval else 0,
        created_by=user_id
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    
    log_collaboration_action(
        db, user_id, user_role, "create", "action", action.id,
        snapshot_id=snapshot_id,
        changes={"action_type": action_type, "expected_impact": expected_impact}
    )
    
    return action


def submit_action_for_approval(
    db: Session,
    action_id: int,
    user_id: str,
    user_role: str
) -> CollaborationAction:
    """Submit action for approval."""
    action = db.query(CollaborationAction).filter(
        CollaborationAction.id == action_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    if action.status != ActionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only submit draft actions")
    
    old_status = action.status
    action.status = ActionStatus.PENDING_APPROVAL
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "submit", "action", action_id,
        snapshot_id=action.snapshot_id,
        changes={"status": {"old": old_status, "new": ActionStatus.PENDING_APPROVAL}}
    )
    
    return action


def approve_action(
    db: Session,
    action_id: int,
    user_id: str,
    user_role: str
) -> CollaborationAction:
    """Approve action (CFO only for actions requiring approval)."""
    action = db.query(CollaborationAction).filter(
        CollaborationAction.id == action_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    if action.requires_approval and user_role not in LOCK_CAPABLE_ROLES:
        raise HTTPException(status_code=403, detail="Only CFO can approve this action")
    
    if action.status != ActionStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Action not pending approval")
    
    old_status = action.status
    
    action.status = ActionStatus.APPROVED
    action.approved_by = user_id
    action.approved_at = datetime.utcnow()
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "approve", "action", action_id,
        snapshot_id=action.snapshot_id,
        changes={"status": {"old": old_status, "new": ActionStatus.APPROVED}}
    )
    
    return action


def update_action_status(
    db: Session,
    action_id: int,
    new_status: str,
    user_id: str,
    user_role: str,
    realized_impact: Optional[Dict] = None
) -> CollaborationAction:
    """Update action status (IN_PROGRESS, DONE, CANCELLED)."""
    action = db.query(CollaborationAction).filter(
        CollaborationAction.id == action_id
    ).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    valid_transitions = {
        ActionStatus.APPROVED: [ActionStatus.IN_PROGRESS, ActionStatus.CANCELLED],
        ActionStatus.IN_PROGRESS: [ActionStatus.DONE, ActionStatus.CANCELLED],
    }
    
    if action.status not in valid_transitions or new_status not in valid_transitions.get(action.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {action.status} to {new_status}"
        )
    
    old_status = action.status
    action.status = new_status
    
    if new_status == ActionStatus.IN_PROGRESS:
        action.started_at = datetime.utcnow()
    elif new_status == ActionStatus.DONE:
        action.completed_at = datetime.utcnow()
        if realized_impact:
            action.realized_cash_impact_json = realized_impact
    
    db.commit()
    
    log_collaboration_action(
        db, user_id, user_role, "status_update", "action", action_id,
        snapshot_id=action.snapshot_id,
        changes={"status": {"old": old_status, "new": new_status}}
    )
    
    return action


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENTS & EVIDENCE
# ═══════════════════════════════════════════════════════════════════════════════

def create_comment(
    db: Session,
    parent_type: str,
    parent_id: int,
    text: str,
    author_id: str,
    snapshot_id: Optional[int] = None,
    reply_to_id: Optional[int] = None,
    evidence: Optional[List[Dict]] = None  # [{type, id}]
) -> CollaborationComment:
    """Create a comment with optional evidence links."""
    comment = CollaborationComment(
        parent_type=parent_type,
        parent_id=parent_id,
        snapshot_id=snapshot_id,
        text=text,
        author_id=author_id,
        reply_to_id=reply_to_id
    )
    db.add(comment)
    db.flush()
    
    # Add evidence links
    if evidence:
        for ev in evidence:
            link = EvidenceLink(
                comment_id=comment.id,
                evidence_type=ev["type"],
                evidence_id=str(ev["id"])
            )
            db.add(link)
    
    db.commit()
    db.refresh(comment)
    
    return comment


def get_comments(
    db: Session,
    parent_type: str,
    parent_id: int
) -> List[CollaborationComment]:
    """Get comments for a resource."""
    return db.query(CollaborationComment).filter(
        CollaborationComment.parent_type == parent_type,
        CollaborationComment.parent_id == parent_id,
        CollaborationComment.is_deleted == 0
    ).order_by(CollaborationComment.created_at.asc()).all()


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY PACK GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_weekly_pack(
    db: Session,
    snapshot_id: int,
    user_id: str
) -> WeeklyPack:
    """
    Generate weekly meeting pack from snapshot.
    
    Contents:
    - Cash today (bank truth)
    - 13-week expected + downside
    - Red weeks
    - Variance vs last locked snapshot
    - Unknown bucket
    - Top exceptions
    - Approved actions / scenarios
    """
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Get last locked snapshot for variance
    last_locked = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.entity_id == snapshot.entity_id,
        CollaborationSnapshot.is_locked == 1,
        CollaborationSnapshot.id != snapshot_id
    ).order_by(CollaborationSnapshot.locked_at.desc()).first()
    
    # Get open exceptions
    exceptions = db.query(CollaborationException).filter(
        CollaborationException.snapshot_id == snapshot_id,
        CollaborationException.status.in_([ExceptionStatus.OPEN, ExceptionStatus.IN_REVIEW])
    ).order_by(CollaborationException.severity.desc()).limit(10).all()
    
    # Get approved scenarios
    approved_scenarios = db.query(CollaborationScenario).filter(
        CollaborationScenario.base_snapshot_id == snapshot_id,
        CollaborationScenario.status == ScenarioStatus.APPROVED
    ).all()
    
    # Get approved/in-progress actions
    active_actions = db.query(CollaborationAction).filter(
        CollaborationAction.snapshot_id == snapshot_id,
        CollaborationAction.status.in_([ActionStatus.APPROVED, ActionStatus.IN_PROGRESS])
    ).all()
    
    content = {
        "generated_at": datetime.utcnow().isoformat(),
        "snapshot": {
            "id": snapshot.id,
            "status": snapshot.status,
            "bank_as_of": snapshot.bank_as_of.isoformat() if snapshot.bank_as_of else None,
            "total_bank_balance": snapshot.total_bank_balance,
            "cash_explained_pct": snapshot.cash_explained_pct,
            "unknown_bucket_amount": snapshot.unknown_bucket_amount
        },
        "variance": {
            "vs_snapshot_id": last_locked.id if last_locked else None,
            "bank_balance_delta": (
                snapshot.total_bank_balance - last_locked.total_bank_balance
            ) if last_locked else None
        },
        "exceptions": [
            {
                "id": e.id,
                "type": e.exception_type,
                "severity": e.severity,
                "amount": e.amount,
                "status": e.status
            }
            for e in exceptions
        ],
        "approved_scenarios": [
            {"id": s.id, "name": s.name}
            for s in approved_scenarios
        ],
        "active_actions": [
            {
                "id": a.id,
                "type": a.action_type,
                "description": a.description,
                "status": a.status,
                "owner": a.owner_id
            }
            for a in active_actions
        ]
    }
    
    pack = WeeklyPack(
        snapshot_id=snapshot_id,
        content_json=content,
        generated_by=user_id
    )
    db.add(pack)
    db.commit()
    db.refresh(pack)
    
    return pack


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def validate_allocation_conservation(
    db: Session,
    bank_transaction_id: int
) -> Tuple[bool, str]:
    """
    INVARIANT: Sum of allocations for a transaction == transaction amount.
    """
    txn = db.query(models.BankTransaction).filter(
        models.BankTransaction.id == bank_transaction_id
    ).first()
    
    if not txn:
        return False, "Transaction not found"
    
    total_allocated = db.query(func.sum(MatchAllocation.allocated_amount)).filter(
        MatchAllocation.bank_transaction_id == bank_transaction_id
    ).scalar() or 0
    
    if abs(total_allocated - abs(txn.amount)) > 0.01:
        return False, f"Allocation sum ({total_allocated}) != transaction amount ({abs(txn.amount)})"
    
    return True, "OK"


def validate_weekly_cash_math(
    db: Session,
    snapshot_id: int,
    week: int,
    open_balance: float,
    inflows: float,
    outflows: float,
    close_balance: float
) -> Tuple[bool, str]:
    """
    INVARIANT: Weekly cash math: close = open + in - out
    """
    expected_close = open_balance + inflows - outflows
    
    if abs(expected_close - close_balance) > 0.01:
        return False, f"Cash math violated: {open_balance} + {inflows} - {outflows} = {expected_close}, got {close_balance}"
    
    return True, "OK"


def check_missing_fx_rate(
    db: Session,
    snapshot_id: int,
    from_currency: str,
    to_currency: str
) -> Tuple[bool, Optional[float]]:
    """
    INVARIANT: Missing FX never silently converts (routes to Unknown).
    Returns (has_rate, rate_value).
    """
    # Get the legacy snapshot to check FX rates
    snapshot = db.query(models.Snapshot).filter(
        models.Snapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        return False, None
    
    # Check for FX rate
    fx_rate = db.query(models.WeeklyFXRate).filter(
        models.WeeklyFXRate.snapshot_id == snapshot_id,
        models.WeeklyFXRate.from_currency == from_currency,
        models.WeeklyFXRate.to_currency == to_currency
    ).first()
    
    if fx_rate:
        return True, fx_rate.rate
    
    # NEVER silently return 1.0 - this routes to Unknown
    return False, None


