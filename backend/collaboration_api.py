"""
Finance-Native Collaboration API
"GitHub for Cash" - REST endpoints for treasury collaboration.

Implements the full API surface:
- Snapshots (create/compare/lock)
- Workspace (13-week + drilldowns)
- Reconciliation (queues/approve/allocate)
- Exceptions (assign/resolve)
- Scenarios (submit/approve)
- Actions (approve/status)
- Comments
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

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
import collaboration_service as collab
from rbac_service import has_permission, get_user_role, ROLES

router = APIRouter(prefix="/api/v1", tags=["collaboration"])


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE DEPENDENCY
# ═══════════════════════════════════════════════════════════════════════════════

# Use shared database configuration to avoid duplicate connections
from database import get_db


def get_current_user(
    x_user_email: str = Header(default="treasury@gitto.io", alias="X-User-Email"),
    x_user_role: str = Header(default="treasury_manager", alias="X-User-Role")
) -> Dict[str, str]:
    """Extract user info from headers."""
    return {"email": x_user_email, "role": x_user_role}


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateSnapshotRequest(BaseModel):
    entity_id: int
    bank_as_of: datetime
    erp_as_of: Optional[datetime] = None
    fx_version: Optional[str] = None


class LockSnapshotRequest(BaseModel):
    lock_reason: str


class AssignExceptionRequest(BaseModel):
    assignee_id: str
    sla_hours: int = 24


class ResolveExceptionRequest(BaseModel):
    resolution_type: str
    resolution_note: str


class EscalateExceptionRequest(BaseModel):
    escalate_to: str
    reason: str


class AllocationItem(BaseModel):
    invoice_id: Optional[int] = None
    vendor_bill_id: Optional[int] = None
    amount: float


class CreateAllocationRequest(BaseModel):
    bank_transaction_id: int
    allocations: List[AllocationItem]
    match_type: str = "manual"


class CreateScenarioRequest(BaseModel):
    base_snapshot_id: int
    name: str
    description: Optional[str] = None
    assumptions: Dict = Field(default_factory=dict)


class RejectRequest(BaseModel):
    reason: str


class CreateActionRequest(BaseModel):
    action_type: str
    description: str
    owner_id: str
    expected_impact: Dict
    scenario_id: Optional[int] = None
    snapshot_id: Optional[int] = None
    target_refs: Optional[List[Dict]] = None
    due_date: Optional[datetime] = None
    requires_approval: bool = True


class UpdateActionStatusRequest(BaseModel):
    status: str
    realized_impact: Optional[Dict] = None


class CreateCommentRequest(BaseModel):
    parent_type: str
    parent_id: int
    text: str
    snapshot_id: Optional[int] = None
    reply_to_id: Optional[int] = None
    evidence: Optional[List[Dict]] = None


# ═══════════════════════════════════════════════════════════════════════════════
# SNAPSHOT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/snapshots")
def create_snapshot(
    request: CreateSnapshotRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    POST /snapshots - Create snapshot from latest sync.
    Required permission: snapshot:create
    """
    if not has_permission(user["role"], "snapshot:create"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:create")
    
    snapshot = collab.create_snapshot(
        db,
        entity_id=request.entity_id,
        bank_as_of=request.bank_as_of,
        created_by=user["email"],
        erp_as_of=request.erp_as_of,
        fx_version=request.fx_version
    )
    
    return {
        "id": snapshot.id,
        "status": snapshot.status,
        "entity_id": snapshot.entity_id,
        "bank_as_of": snapshot.bank_as_of.isoformat(),
        "created_by": snapshot.created_by,
        "created_at": snapshot.created_at.isoformat()
    }


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /snapshots/{id} - Get snapshot details."""
    if not has_permission(user["role"], "snapshot:view"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:view")
    
    snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return {
        "id": snapshot.id,
        "entity_id": snapshot.entity_id,
        "status": snapshot.status,
        "bank_as_of": snapshot.bank_as_of.isoformat() if snapshot.bank_as_of else None,
        "erp_as_of": snapshot.erp_as_of.isoformat() if snapshot.erp_as_of else None,
        "fx_version": snapshot.fx_version,
        "is_locked": bool(snapshot.is_locked),
        "locked_by": snapshot.locked_by,
        "locked_at": snapshot.locked_at.isoformat() if snapshot.locked_at else None,
        "lock_reason": snapshot.lock_reason,
        "created_by": snapshot.created_by,
        "created_at": snapshot.created_at.isoformat(),
        "metrics": {
            "total_bank_balance": snapshot.total_bank_balance,
            "cash_explained_pct": snapshot.cash_explained_pct,
            "unknown_bucket_amount": snapshot.unknown_bucket_amount,
            "exception_count": snapshot.exception_count
        }
    }


@router.post("/snapshots/{snapshot_id}/ready")
def mark_snapshot_ready(
    snapshot_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /snapshots/{id}/ready - Mark snapshot ready for review."""
    if not has_permission(user["role"], "snapshot:ready"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:ready")
    
    snapshot = collab.mark_snapshot_ready(
        db, snapshot_id, user["email"], user["role"]
    )
    
    return {
        "id": snapshot.id,
        "status": snapshot.status,
        "ready_at": snapshot.ready_at.isoformat(),
        "ready_by": snapshot.ready_by
    }


@router.post("/snapshots/{snapshot_id}/lock")
def lock_snapshot(
    snapshot_id: int,
    request: LockSnapshotRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    POST /snapshots/{id}/lock - Lock snapshot (CFO only).
    Hard rule: Only CFO can lock.
    """
    if not has_permission(user["role"], "snapshot:lock"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:lock")
    
    snapshot = collab.lock_snapshot(
        db, snapshot_id, user["email"], user["role"], request.lock_reason
    )
    
    return {
        "id": snapshot.id,
        "status": snapshot.status,
        "is_locked": True,
        "locked_at": snapshot.locked_at.isoformat(),
        "locked_by": snapshot.locked_by,
        "lock_reason": snapshot.lock_reason
    }


@router.get("/snapshots/compare")
def compare_snapshots(
    a: int = Query(..., description="Snapshot A ID"),
    b: int = Query(..., description="Snapshot B ID"),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /snapshots/compare?a=...&b=... - Compare two snapshots (variance diff)."""
    if not has_permission(user["role"], "snapshot:view"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:view")
    
    return collab.compare_snapshots(db, a, b)


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE ENDPOINTS (13-Week + Drilldowns)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/workspace/13w")
def get_13_week_workspace(
    snapshot_id: int = Query(...),
    view: str = Query(default="p50", description="View type: p25|p50|p75"),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    GET /workspace/13w?snapshot_id=...&view=p50|p25|p75
    Returns the 13-week cash forecast grid.
    """
    if not has_permission(user["role"], "snapshot:view"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:view")
    
    # Get snapshot
    snapshot = db.query(models.Snapshot).filter(
        models.Snapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Build 13-week grid (simplified - would pull from forecast service)
    weeks = []
    current_date = datetime.utcnow()
    
    for week in range(1, 14):
        week_start = current_date + timedelta(weeks=week-1)
        
        # Calculate week totals from invoices
        week_end = week_start + timedelta(days=6)
        
        inflows = db.query(func.sum(models.Invoice.amount)).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.expected_due_date >= week_start,
            models.Invoice.expected_due_date <= week_end,
            models.Invoice.amount > 0
        ).scalar() or 0
        
        outflows = db.query(func.sum(models.VendorBill.amount)).filter(
            models.VendorBill.snapshot_id == snapshot_id,
            models.VendorBill.due_date >= week_start,
            models.VendorBill.due_date <= week_end
        ).scalar() or 0
        
        weeks.append({
            "week": week,
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_label": f"W{week}",
            "cash_in": round(inflows, 2),
            "cash_out": round(outflows, 2),
            "net_flow": round(inflows - outflows, 2),
            "is_red_week": (inflows - outflows) < 0,
            "source_badge": "modeled"  # bank-true, reconciled, modeled, unknown
        })
    
    return {
        "snapshot_id": snapshot_id,
        "view": view,
        "opening_balance": snapshot.opening_bank_balance,
        "min_cash_threshold": snapshot.min_cash_threshold,
        "weeks": weeks
    }


@router.get("/workspace/13w/drilldown")
def get_drilldown(
    snapshot_id: int = Query(...),
    week: int = Query(..., description="Week number 1-13"),
    bucket: str = Query(default="cash_in", description="Bucket: cash_in|cash_out|unknown"),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    GET /workspace/13w/drilldown?snapshot_id=...&week=...&bucket=cash_in|cash_out|unknown
    Returns row-level detail for a grid cell.
    
    INVARIANT: Grid cell total == drilldown sum (within rounding)
    """
    if not has_permission(user["role"], "snapshot:view"):
        raise HTTPException(status_code=403, detail="Permission denied: snapshot:view")
    
    current_date = datetime.utcnow()
    week_start = current_date + timedelta(weeks=week-1)
    week_end = week_start + timedelta(days=6)
    
    items = []
    
    if bucket == "cash_in":
        # AR invoices
        invoices = db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.expected_due_date >= week_start,
            models.Invoice.expected_due_date <= week_end,
            models.Invoice.amount > 0
        ).all()
        
        for inv in invoices:
            items.append({
                "type": "invoice",
                "id": inv.id,
                "document_number": inv.document_number,
                "customer": inv.customer,
                "amount": inv.amount,
                "currency": inv.currency,
                "due_date": inv.expected_due_date.strftime("%Y-%m-%d") if inv.expected_due_date else None,
                "truth_label": inv.truth_label
            })
    
    elif bucket == "cash_out":
        # AP bills
        bills = db.query(models.VendorBill).filter(
            models.VendorBill.snapshot_id == snapshot_id,
            models.VendorBill.due_date >= week_start,
            models.VendorBill.due_date <= week_end
        ).all()
        
        for bill in bills:
            items.append({
                "type": "vendor_bill",
                "id": bill.id,
                "document_number": bill.document_number,
                "vendor": bill.vendor_name,
                "amount": bill.amount,
                "currency": bill.currency,
                "due_date": bill.due_date.strftime("%Y-%m-%d") if bill.due_date else None,
                "hold_status": bool(bill.hold_status)
            })
    
    total = sum(item["amount"] for item in items)
    
    return {
        "snapshot_id": snapshot_id,
        "week": week,
        "bucket": bucket,
        "item_count": len(items),
        "total": round(total, 2),
        "items": items
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RECONCILIATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/recon/unmatched")
def get_unmatched_queue(
    snapshot_id: int = Query(...),
    limit: int = Query(default=100),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /recon/unmatched?snapshot_id=... - Get unmatched transactions queue."""
    if not has_permission(user["role"], "reconciliation:view"):
        raise HTTPException(status_code=403, detail="Permission denied: reconciliation:view")
    
    transactions = collab.get_unmatched_transactions(db, snapshot_id, limit)
    
    return {
        "snapshot_id": snapshot_id,
        "count": len(transactions),
        "transactions": [
            {
                "id": txn.id,
                "transaction_date": txn.transaction_date.strftime("%Y-%m-%d") if txn.transaction_date else None,
                "amount": txn.amount,
                "currency": txn.currency,
                "reference": txn.reference,
                "counterparty": txn.counterparty,
                "transaction_type": txn.transaction_type,
                "days_unmatched": txn.days_unmatched,
                "lifecycle_status": txn.lifecycle_status
            }
            for txn in transactions
        ]
    }


@router.get("/recon/suggestions")
def get_suggested_matches(
    snapshot_id: int = Query(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /recon/suggestions?snapshot_id=... - Get suggested matches pending approval."""
    if not has_permission(user["role"], "reconciliation:view"):
        raise HTTPException(status_code=403, detail="Permission denied: reconciliation:view")
    
    matches = collab.get_suggested_matches(db, snapshot_id)
    
    return {
        "snapshot_id": snapshot_id,
        "count": len(matches),
        "suggestions": [
            {
                "id": m.id,
                "match_type": m.match_type,
                "confidence": m.confidence,
                "status": m.status,
                "created_at": m.created_at.isoformat(),
                "allocations": [
                    {
                        "bank_transaction_id": a.bank_transaction_id,
                        "invoice_id": a.invoice_id,
                        "vendor_bill_id": a.vendor_bill_id,
                        "amount": a.allocated_amount
                    }
                    for a in m.allocations
                ]
            }
            for m in matches
        ]
    }


@router.post("/recon/approve")
def approve_match(
    match_id: int = Query(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    POST /recon/approve?match_id=... - Approve suggested match.
    INVARIANT: Suggested matches never auto-apply.
    """
    if not has_permission(user["role"], "reconciliation:approve"):
        raise HTTPException(status_code=403, detail="Permission denied: reconciliation:approve")
    
    match = collab.approve_match(db, match_id, user["email"], user["role"])
    
    return {
        "id": match.id,
        "status": match.status,
        "approved_by": match.approved_by,
        "approved_at": match.approved_at.isoformat()
    }


@router.post("/recon/reject")
def reject_match(
    request: RejectRequest,
    match_id: int = Query(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /recon/reject?match_id=... - Reject suggested match."""
    if not has_permission(user["role"], "reconciliation:approve"):
        raise HTTPException(status_code=403, detail="Permission denied: reconciliation:approve")
    
    match = collab.reject_match(db, match_id, request.reason, user["email"], user["role"])
    
    return {
        "id": match.id,
        "status": match.status,
        "rejection_reason": match.rejection_reason
    }


@router.post("/recon/allocate")
def create_allocation(
    request: CreateAllocationRequest,
    snapshot_id: int = Query(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    POST /recon/allocate - Manual split allocations.
    
    INVARIANTS:
    - Sum allocations per txn == txn amount
    - Sum allocations to invoice ≤ open amount
    """
    if not has_permission(user["role"], "reconciliation:allocate"):
        raise HTTPException(status_code=403, detail="Permission denied: reconciliation:allocate")
    
    allocations = [
        {
            "invoice_id": a.invoice_id,
            "vendor_bill_id": a.vendor_bill_id,
            "amount": a.amount
        }
        for a in request.allocations
    ]
    
    match = collab.create_allocation(
        db, snapshot_id, request.bank_transaction_id,
        allocations, user["email"], user["role"], request.match_type
    )
    
    return {
        "id": match.id,
        "status": match.status,
        "allocation_count": len(match.allocations)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/exceptions")
def get_exceptions(
    snapshot_id: int = Query(...),
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    assignee_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /exceptions?snapshot_id=... - Get exceptions for snapshot."""
    if not has_permission(user["role"], "exception:view"):
        raise HTTPException(status_code=403, detail="Permission denied: exception:view")
    
    exceptions = collab.get_exceptions(db, snapshot_id, status, severity, assignee_id)
    
    return {
        "snapshot_id": snapshot_id,
        "count": len(exceptions),
        "exceptions": [
            {
                "id": e.id,
                "type": e.exception_type,
                "severity": e.severity,
                "status": e.status,
                "amount": e.amount,
                "currency": e.currency,
                "assignee_id": e.assignee_id,
                "sla_due_at": e.sla_due_at.isoformat() if e.sla_due_at else None,
                "created_at": e.created_at.isoformat()
            }
            for e in exceptions
        ]
    }


@router.post("/exceptions/{exception_id}/assign")
def assign_exception(
    exception_id: int,
    request: AssignExceptionRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /exceptions/{id}/assign - Assign exception to user."""
    if not has_permission(user["role"], "exception:assign"):
        raise HTTPException(status_code=403, detail="Permission denied: exception:assign")
    
    exception = collab.assign_exception(
        db, exception_id, request.assignee_id,
        user["email"], user["role"], request.sla_hours
    )
    
    return {
        "id": exception.id,
        "status": exception.status,
        "assignee_id": exception.assignee_id,
        "sla_due_at": exception.sla_due_at.isoformat()
    }


@router.post("/exceptions/{exception_id}/resolve")
def resolve_exception(
    exception_id: int,
    request: ResolveExceptionRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /exceptions/{id}/resolve - Resolve exception."""
    if not has_permission(user["role"], "exception:resolve"):
        raise HTTPException(status_code=403, detail="Permission denied: exception:resolve")
    
    exception = collab.resolve_exception(
        db, exception_id, request.resolution_type,
        request.resolution_note, user["email"], user["role"]
    )
    
    return {
        "id": exception.id,
        "status": exception.status,
        "resolved_by": exception.resolved_by,
        "resolved_at": exception.resolved_at.isoformat()
    }


@router.post("/exceptions/{exception_id}/escalate")
def escalate_exception(
    exception_id: int,
    request: EscalateExceptionRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /exceptions/{id}/escalate - Escalate exception."""
    if not has_permission(user["role"], "exception:escalate"):
        raise HTTPException(status_code=403, detail="Permission denied: exception:escalate")
    
    exception = collab.escalate_exception(
        db, exception_id, request.escalate_to,
        request.reason, user["email"], user["role"]
    )
    
    return {
        "id": exception.id,
        "status": exception.status,
        "escalated_to": exception.escalated_to
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/scenarios")
def create_scenario(
    request: CreateScenarioRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /scenarios - Create scenario from base snapshot."""
    if not has_permission(user["role"], "scenario:create"):
        raise HTTPException(status_code=403, detail="Permission denied: scenario:create")
    
    scenario = collab.create_scenario(
        db, request.base_snapshot_id, request.name,
        request.description, request.assumptions,
        user["email"], user["role"]
    )
    
    return {
        "id": scenario.id,
        "name": scenario.name,
        "status": scenario.status,
        "base_snapshot_id": scenario.base_snapshot_id,
        "created_at": scenario.created_at.isoformat()
    }


@router.get("/scenarios/{scenario_id}")
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /scenarios/{id} - Get scenario details."""
    if not has_permission(user["role"], "scenario:view"):
        raise HTTPException(status_code=403, detail="Permission denied: scenario:view")
    
    scenario = db.query(CollaborationScenario).filter(
        CollaborationScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "status": scenario.status,
        "base_snapshot_id": scenario.base_snapshot_id,
        "assumptions": scenario.assumptions_json,
        "impact_summary": scenario.impact_summary_json,
        "created_by": scenario.created_by,
        "created_at": scenario.created_at.isoformat(),
        "approved_by": scenario.approved_by,
        "approved_at": scenario.approved_at.isoformat() if scenario.approved_at else None,
        "actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "description": a.description,
                "status": a.status
            }
            for a in scenario.actions
        ]
    }


@router.post("/scenarios/{scenario_id}/submit")
def submit_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /scenarios/{id}/submit - Submit scenario for approval."""
    if not has_permission(user["role"], "scenario:submit"):
        raise HTTPException(status_code=403, detail="Permission denied: scenario:submit")
    
    scenario = collab.submit_scenario(db, scenario_id, user["email"], user["role"])
    
    return {
        "id": scenario.id,
        "status": scenario.status,
        "submitted_at": scenario.submitted_at.isoformat()
    }


@router.post("/scenarios/{scenario_id}/approve")
def approve_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /scenarios/{id}/approve - Approve scenario (CFO only)."""
    if not has_permission(user["role"], "scenario:approve"):
        raise HTTPException(status_code=403, detail="Permission denied: scenario:approve")
    
    scenario = collab.approve_scenario(db, scenario_id, user["email"], user["role"])
    
    return {
        "id": scenario.id,
        "status": scenario.status,
        "approved_by": scenario.approved_by,
        "approved_at": scenario.approved_at.isoformat()
    }


@router.post("/scenarios/{scenario_id}/reject")
def reject_scenario(
    scenario_id: int,
    request: RejectRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /scenarios/{id}/reject - Reject scenario."""
    if not has_permission(user["role"], "scenario:reject"):
        raise HTTPException(status_code=403, detail="Permission denied: scenario:reject")
    
    scenario = collab.reject_scenario(db, scenario_id, request.reason, user["email"], user["role"])
    
    return {
        "id": scenario.id,
        "status": scenario.status,
        "rejection_reason": scenario.rejection_reason
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ACTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/actions")
def create_action(
    request: CreateActionRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /actions - Create action."""
    if not has_permission(user["role"], "action:create"):
        raise HTTPException(status_code=403, detail="Permission denied: action:create")
    
    action = collab.create_action(
        db, request.action_type, request.description,
        request.owner_id, request.expected_impact,
        user["email"], user["role"],
        scenario_id=request.scenario_id,
        snapshot_id=request.snapshot_id,
        target_refs=request.target_refs,
        due_date=request.due_date,
        requires_approval=request.requires_approval
    )
    
    return {
        "id": action.id,
        "action_type": action.action_type,
        "status": action.status,
        "created_at": action.created_at.isoformat()
    }


@router.post("/actions/{action_id}/submit")
def submit_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /actions/{id}/submit - Submit action for approval."""
    if not has_permission(user["role"], "action:submit"):
        raise HTTPException(status_code=403, detail="Permission denied: action:submit")
    
    action = collab.submit_action_for_approval(db, action_id, user["email"], user["role"])
    
    return {
        "id": action.id,
        "status": action.status
    }


@router.post("/actions/{action_id}/approve")
def approve_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /actions/{id}/approve - Approve action."""
    if not has_permission(user["role"], "action:approve"):
        raise HTTPException(status_code=403, detail="Permission denied: action:approve")
    
    action = collab.approve_action(db, action_id, user["email"], user["role"])
    
    return {
        "id": action.id,
        "status": action.status,
        "approved_by": action.approved_by,
        "approved_at": action.approved_at.isoformat()
    }


@router.post("/actions/{action_id}/status")
def update_action_status(
    action_id: int,
    request: UpdateActionStatusRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /actions/{id}/status - Update action status."""
    if not has_permission(user["role"], "action:execute"):
        raise HTTPException(status_code=403, detail="Permission denied: action:execute")
    
    action = collab.update_action_status(
        db, action_id, request.status,
        user["email"], user["role"], request.realized_impact
    )
    
    return {
        "id": action.id,
        "status": action.status,
        "started_at": action.started_at.isoformat() if action.started_at else None,
        "completed_at": action.completed_at.isoformat() if action.completed_at else None
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/comments")
def create_comment(
    request: CreateCommentRequest,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /comments - Create comment with evidence links."""
    if not has_permission(user["role"], "comment:create"):
        raise HTTPException(status_code=403, detail="Permission denied: comment:create")
    
    comment = collab.create_comment(
        db, request.parent_type, request.parent_id,
        request.text, user["email"],
        snapshot_id=request.snapshot_id,
        reply_to_id=request.reply_to_id,
        evidence=request.evidence
    )
    
    return {
        "id": comment.id,
        "parent_type": comment.parent_type,
        "parent_id": comment.parent_id,
        "author_id": comment.author_id,
        "created_at": comment.created_at.isoformat(),
        "evidence_count": len(comment.evidence_links)
    }


@router.get("/comments")
def get_comments(
    parent_type: str = Query(...),
    parent_id: int = Query(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /comments?parent_type=...&parent_id=... - Get comments for resource."""
    if not has_permission(user["role"], "comment:view"):
        raise HTTPException(status_code=403, detail="Permission denied: comment:view")
    
    comments = collab.get_comments(db, parent_type, parent_id)
    
    return {
        "parent_type": parent_type,
        "parent_id": parent_id,
        "count": len(comments),
        "comments": [
            {
                "id": c.id,
                "text": c.text,
                "author_id": c.author_id,
                "reply_to_id": c.reply_to_id,
                "created_at": c.created_at.isoformat(),
                "evidence": [
                    {"type": e.evidence_type, "id": e.evidence_id}
                    for e in c.evidence_links
                ]
            }
            for c in comments
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WEEKLY PACK ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/packs/generate")
def generate_weekly_pack(
    snapshot_id: int = Query(...),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """POST /packs/generate?snapshot_id=... - Generate weekly meeting pack."""
    if not has_permission(user["role"], "pack:generate"):
        raise HTTPException(status_code=403, detail="Permission denied: pack:generate")
    
    pack = collab.generate_weekly_pack(db, snapshot_id, user["email"])
    
    return {
        "id": pack.id,
        "snapshot_id": pack.snapshot_id,
        "generated_at": pack.generated_at.isoformat(),
        "content": pack.content_json
    }


@router.get("/packs/{pack_id}")
def get_weekly_pack(
    pack_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /packs/{id} - Get weekly pack."""
    if not has_permission(user["role"], "pack:view"):
        raise HTTPException(status_code=403, detail="Permission denied: pack:view")
    
    pack = db.query(WeeklyPack).filter(WeeklyPack.id == pack_id).first()
    
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    
    return {
        "id": pack.id,
        "snapshot_id": pack.snapshot_id,
        "generated_at": pack.generated_at.isoformat(),
        "generated_by": pack.generated_by,
        "content": pack.content_json
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MEETING MODE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/meeting-mode/{snapshot_id}")
def get_meeting_mode_data(
    snapshot_id: int,
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """
    GET /meeting-mode/{snapshot_id}
    Returns all data needed for "Meeting Mode" - the guided presenter flow.
    
    Flow:
    1. Cash today (bank truth)
    2. Forecast (P50/P75)
    3. Red weeks + causes
    4. Variance diff
    5. Decisions (approve actions)
    6. Lock snapshot
    """
    if not has_permission(user["role"], "snapshot:view"):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get collaboration snapshot
    collab_snapshot = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.id == snapshot_id
    ).first()
    
    # Get legacy snapshot for forecast data
    snapshot = db.query(models.Snapshot).filter(
        models.Snapshot.id == snapshot_id
    ).first()
    
    if not snapshot and not collab_snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Get last locked for variance
    last_locked = db.query(CollaborationSnapshot).filter(
        CollaborationSnapshot.is_locked == 1,
        CollaborationSnapshot.id != snapshot_id
    ).order_by(CollaborationSnapshot.locked_at.desc()).first()
    
    # Get pending actions
    pending_actions = db.query(CollaborationAction).filter(
        CollaborationAction.snapshot_id == snapshot_id,
        CollaborationAction.status == ActionStatus.PENDING_APPROVAL
    ).all()
    
    # Get open exceptions
    open_exceptions = db.query(CollaborationException).filter(
        CollaborationException.snapshot_id == snapshot_id,
        CollaborationException.status.in_([ExceptionStatus.OPEN, ExceptionStatus.IN_REVIEW])
    ).order_by(CollaborationException.severity.desc()).limit(5).all()
    
    return {
        "snapshot_id": snapshot_id,
        "status": collab_snapshot.status if collab_snapshot else "unknown",
        "is_locked": bool(collab_snapshot.is_locked) if collab_snapshot else False,
        
        "steps": {
            "1_cash_today": {
                "label": "Cash Today",
                "bank_balance": snapshot.opening_bank_balance if snapshot else 0,
                "cash_explained_pct": collab_snapshot.cash_explained_pct if collab_snapshot else 0,
                "unknown_bucket": collab_snapshot.unknown_bucket_amount if collab_snapshot else 0
            },
            "2_forecast": {
                "label": "13-Week Forecast",
                "min_cash_threshold": snapshot.min_cash_threshold if snapshot else 0,
                "endpoint": f"/api/v1/workspace/13w?snapshot_id={snapshot_id}"
            },
            "3_red_weeks": {
                "label": "Red Weeks",
                "description": "Weeks with net outflow below minimum",
                "count": 0  # Would be computed from forecast
            },
            "4_variance": {
                "label": "Variance vs Last",
                "vs_snapshot_id": last_locked.id if last_locked else None,
                "bank_delta": (
                    collab_snapshot.total_bank_balance - last_locked.total_bank_balance
                ) if last_locked and collab_snapshot else None
            },
            "5_actions": {
                "label": "Pending Decisions",
                "pending_count": len(pending_actions),
                "actions": [
                    {
                        "id": a.id,
                        "type": a.action_type,
                        "description": a.description,
                        "owner": a.owner_id
                    }
                    for a in pending_actions
                ]
            },
            "6_lock": {
                "label": "Lock Snapshot",
                "can_lock": user["role"] in ["admin", "cfo"],
                "blockers": {
                    "critical_exceptions": len([e for e in open_exceptions if e.severity == "critical"]),
                    "pending_approvals": len(pending_actions)
                }
            }
        },
        
        "exceptions_summary": [
            {
                "id": e.id,
                "type": e.exception_type,
                "severity": e.severity
            }
            for e in open_exceptions
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/audit-log")
def get_audit_log(
    snapshot_id: Optional[int] = Query(default=None),
    resource_type: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100),
    db: Session = Depends(get_db),
    user: Dict = Depends(get_current_user)
):
    """GET /audit-log - Get collaboration audit log."""
    if not has_permission(user["role"], "audit:view"):
        raise HTTPException(status_code=403, detail="Permission denied: audit:view")
    
    query = db.query(CollaborationAuditLog)
    
    if snapshot_id:
        query = query.filter(CollaborationAuditLog.snapshot_id == snapshot_id)
    if resource_type:
        query = query.filter(CollaborationAuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(CollaborationAuditLog.user_id == user_id)
    
    logs = query.order_by(CollaborationAuditLog.timestamp.desc()).limit(limit).all()
    
    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "user_id": log.user_id,
                "user_role": log.user_role,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "changes": log.changes_json
            }
            for log in logs
        ]
    }

