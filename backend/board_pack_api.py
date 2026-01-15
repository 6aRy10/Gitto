"""
Board Pack Autopilot API

Generate and manage board pack reports.
All numbers deterministically derived from snapshot + plan outputs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from database import get_db
from board_pack_service import BoardPackService
from board_pack_models import BoardPack, BoardPackStatus


router = APIRouter(prefix="/board-pack", tags=["Board Pack"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class SignOffRequest(BaseModel):
    """CFO sign-off request."""
    signed_off_by: str
    signoff_statement: str = Field(..., min_length=20)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("")
def get_board_pack(
    plan_id: Optional[int] = Query(None, description="Planning scenario ID"),
    snapshot_id: int = Query(..., description="Snapshot ID"),
    entity_id: int = Query(..., description="Entity ID"),
    regenerate: bool = Query(False, description="Force regenerate"),
    previous_pack_id: Optional[int] = Query(None, description="Previous pack for comparison"),
    db: Session = Depends(get_db)
):
    """
    GET /board-pack?plan_id=&snapshot_id=&entity_id=
    
    Generates a 10-slide-equivalent board pack report:
    1. Cover
    2. Executive Summary
    3. Key Highlights
    4. Runway Analysis
    5. Forecast vs Last Month
    6. Revenue Drivers
    7. Expense Drivers
    8. Risks & Mitigations
    9. Action Plan
    10. Appendix
    
    All numbers are deterministically derived from snapshot + plan outputs.
    Narratives only describe computed results.
    """
    service = BoardPackService(db)
    
    # Check for existing pack
    if not regenerate:
        existing = db.query(BoardPack).filter(
            BoardPack.snapshot_id == snapshot_id,
            BoardPack.plan_id == plan_id if plan_id else True,
            BoardPack.entity_id == entity_id
        ).order_by(BoardPack.created_at.desc()).first()
        
        if existing:
            return _format_pack_response(existing, service)
    
    # Generate new pack
    try:
        pack = service.generate_board_pack(
            entity_id=entity_id,
            snapshot_id=snapshot_id,
            plan_id=plan_id,
            previous_pack_id=previous_pack_id
        )
        return _format_pack_response(pack, service)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{pack_id}")
def get_pack_by_id(pack_id: int, db: Session = Depends(get_db)):
    """Get a specific board pack by ID."""
    service = BoardPackService(db)
    pack = service.get_pack(pack_id)
    
    if not pack:
        raise HTTPException(status_code=404, detail="Board pack not found")
    
    return _format_pack_response(pack, service)


@router.get("/{pack_id}/slides")
def get_slides(pack_id: int, db: Session = Depends(get_db)):
    """Get all slides for a board pack."""
    service = BoardPackService(db)
    slides = service.get_slides(pack_id)
    
    return [_format_slide(s) for s in slides]


@router.get("/{pack_id}/slides/{slide_number}")
def get_slide(pack_id: int, slide_number: int, db: Session = Depends(get_db)):
    """Get a specific slide."""
    service = BoardPackService(db)
    slides = service.get_slides(pack_id)
    
    slide = next((s for s in slides if s.slide_number == slide_number), None)
    if not slide:
        raise HTTPException(status_code=404, detail="Slide not found")
    
    return _format_slide(slide)


@router.get("/{pack_id}/risks")
def get_risks(pack_id: int, db: Session = Depends(get_db)):
    """Get all risks identified in the board pack."""
    service = BoardPackService(db)
    risks = service.get_risks(pack_id)
    
    return [_format_risk(r) for r in risks]


@router.get("/{pack_id}/actions")
def get_actions(pack_id: int, db: Session = Depends(get_db)):
    """Get all action items from the board pack."""
    service = BoardPackService(db)
    actions = service.get_actions(pack_id)
    
    return [_format_action(a) for a in actions]


# ═══════════════════════════════════════════════════════════════════════════════
# CFO SIGN-OFF
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{pack_id}/sign-off")
def sign_off_pack(
    pack_id: int,
    request: SignOffRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    CFO sign-off on board pack.
    
    Requires acknowledgment statement of at least 20 characters.
    Creates audit log entry.
    """
    service = BoardPackService(db)
    
    # Get client IP
    ip_address = req.client.host if req.client else None
    
    try:
        pack = service.sign_off(
            pack_id=pack_id,
            signed_off_by=request.signed_off_by,
            signoff_statement=request.signoff_statement,
            ip_address=ip_address
        )
        return {
            "status": "signed_off",
            "pack_id": pack_id,
            "signed_off_by": pack.signed_off_by,
            "signed_off_at": pack.signed_off_at.isoformat() if pack.signed_off_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{pack_id}/audit-log")
def get_audit_log(pack_id: int, db: Session = Depends(get_db)):
    """Get audit log for a board pack."""
    service = BoardPackService(db)
    logs = service.get_audit_log(pack_id)
    
    return [
        {
            "id": log.id,
            "action": log.action,
            "actor": log.actor,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "details": log.details_json,
            "signoff_statement": log.signoff_statement,
            "ip_address": log.ip_address
        }
        for log in logs
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# PACK LISTING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/entity/{entity_id}/packs")
def list_packs(
    entity_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all board packs for an entity."""
    service = BoardPackService(db)
    packs = service.get_packs(entity_id)
    
    if status:
        packs = [p for p in packs if p.status.value == status]
    
    return [_format_pack_summary(p) for p in packs]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _format_pack_response(pack: BoardPack, service: BoardPackService) -> dict:
    """Format complete pack response."""
    slides = service.get_slides(pack.id)
    risks = service.get_risks(pack.id)
    actions = service.get_actions(pack.id)
    
    return {
        "id": pack.id,
        "title": pack.title,
        "period": pack.period_label,
        "as_of_date": pack.as_of_date.isoformat() if pack.as_of_date else None,
        "status": pack.status.value,
        "source": {
            "snapshot_id": pack.snapshot_id,
            "plan_id": pack.plan_id,
            "previous_pack_id": pack.previous_pack_id
        },
        "summary": {
            "runway_months": pack.runway_months,
            "ending_cash": float(pack.ending_cash or 0),
            "ending_arr": float(pack.ending_arr or 0),
            "monthly_burn": float(pack.monthly_burn or 0),
            "headcount": pack.headcount
        },
        "changes": {
            "arr_change_pct": float(pack.arr_change_pct or 0),
            "burn_change_pct": float(pack.burn_change_pct or 0),
            "runway_change_months": pack.runway_change_months
        },
        "risk_summary": {
            "critical": pack.critical_risks_count,
            "high": pack.high_risks_count
        },
        "slides": [_format_slide(s) for s in slides],
        "risks": [_format_risk(r) for r in risks],
        "actions": [_format_action(a) for a in actions],
        "signoff": {
            "signed_off": pack.status == BoardPackStatus.SIGNED_OFF,
            "signed_off_at": pack.signed_off_at.isoformat() if pack.signed_off_at else None,
            "signed_off_by": pack.signed_off_by,
            "statement": pack.signoff_statement
        },
        "generated_at": pack.generated_at.isoformat() if pack.generated_at else None,
        "currency": pack.base_currency
    }


def _format_pack_summary(pack: BoardPack) -> dict:
    """Format pack summary for listing."""
    return {
        "id": pack.id,
        "title": pack.title,
        "period": pack.period_label,
        "status": pack.status.value,
        "runway_months": pack.runway_months,
        "ending_arr": float(pack.ending_arr or 0),
        "critical_risks": pack.critical_risks_count,
        "signed_off": pack.status == BoardPackStatus.SIGNED_OFF,
        "created_at": pack.created_at.isoformat() if pack.created_at else None
    }


def _format_slide(slide) -> dict:
    """Format slide for response."""
    return {
        "slide_number": slide.slide_number,
        "type": slide.slide_type.value if slide.slide_type else None,
        "title": slide.title,
        "headline": slide.headline,
        "narrative": slide.narrative,
        "metrics": slide.metrics_json,
        "charts": slide.charts_json,
        "tables": slide.tables_json,
        "bullets": slide.bullets_json,
        "evidence_refs": slide.evidence_refs_json
    }


def _format_risk(risk) -> dict:
    """Format risk for response."""
    return {
        "id": risk.id,
        "title": risk.risk_title,
        "description": risk.risk_description,
        "severity": risk.severity.value if risk.severity else None,
        "exposure_amount": float(risk.exposure_amount or 0),
        "detection_method": risk.detection_method,
        "threshold_breached": risk.threshold_breached,
        "mitigation": risk.mitigation,
        "mitigation_owner": risk.mitigation_owner,
        "evidence_refs": risk.evidence_refs_json
    }


def _format_action(action) -> dict:
    """Format action for response."""
    return {
        "id": action.id,
        "title": action.action_title,
        "description": action.action_description,
        "owner": action.owner,
        "deadline": action.deadline.isoformat() if action.deadline else None,
        "priority": action.priority,
        "status": action.status,
        "triggered_by": action.triggered_by
    }
