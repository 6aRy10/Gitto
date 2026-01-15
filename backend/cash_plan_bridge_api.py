"""
Cash-to-Plan Bridge API

Endpoints for generating and querying Cash-to-Plan bridges.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
from decimal import Decimal

from database import get_db
from cash_plan_bridge_service import CashToPlanBridgeService
from cash_plan_bridge_models import (
    FPAPlan, PlanDriver, CashToPlanBridge, BridgeLine, WeeklyPlanOverlay,
    PlanStatus, DriverType, BridgeLineType
)


router = APIRouter(prefix="/plan", tags=["Cash-to-Plan Bridge"])


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class PlanDriverCreate(BaseModel):
    driver_type: str  # "revenue", "cogs", "opex", "capex", "financing", "other"
    category: str
    subcategory: Optional[str] = None
    period_month: date
    amount_plan: float
    currency: str = "EUR"
    days_to_cash: Optional[int] = None
    days_to_pay: Optional[int] = None
    cash_timing_distribution: Optional[dict] = None
    driver_formula: Optional[str] = None
    notes: Optional[str] = None


class PlanCreate(BaseModel):
    entity_id: int
    name: str
    description: Optional[str] = None
    plan_version: str = "v1"
    start_month: date
    end_month: date
    base_currency: str = "EUR"
    assumptions: Optional[dict] = None
    drivers: Optional[List[PlanDriverCreate]] = None


class PlanResponse(BaseModel):
    id: int
    entity_id: int
    name: str
    description: Optional[str]
    plan_version: str
    start_month: date
    end_month: date
    status: str
    base_currency: str
    assumptions: Optional[dict]
    created_at: str
    driver_count: int

    class Config:
        from_attributes = True


class BridgeLineResponse(BaseModel):
    id: int
    line_type: str
    category: str
    description: Optional[str]
    period_month: Optional[str]
    period_week: Optional[str]
    plan_amount: float
    plan_cash_amount: float
    actual_amount: float
    variance: float
    timing_days: Optional[int]
    has_evidence: bool
    evidence_type: Optional[str]
    is_unknown: bool
    invoice_count: int
    bank_txn_count: int
    vendor_bill_count: int

    class Config:
        from_attributes = True


class WeeklyOverlayResponse(BaseModel):
    week_number: int
    week_start: str
    week_end: str
    opening_balance_plan: float
    plan_inflows: float
    plan_outflows: float
    closing_balance_plan: float
    actual_inflows: float
    actual_outflows: float
    closing_balance_actual: float
    min_cash_required: float
    is_red_week: bool
    cash_shortfall: float

    class Config:
        from_attributes = True


class BridgeSummary(BaseModel):
    plan_revenue: float
    plan_cash_inflows: float
    actual_cash_inflows: float
    plan_expenses: float
    plan_cash_outflows: float
    actual_cash_outflows: float
    inflow_variance: float
    outflow_variance: float
    net_variance: float
    ar_change: float
    ap_change: float
    unknown_inflows: float
    unknown_outflows: float


class RedWeeksSummary(BaseModel):
    count: int
    total_shortfall: float
    weeks: List[dict]


class BridgeResponse(BaseModel):
    id: int
    plan_id: int
    snapshot_id: int
    name: Optional[str]
    generated_at: str
    summary: BridgeSummary
    red_weeks: RedWeeksSummary
    weekly_overlay: List[dict]
    bridge_lines: List[dict]
    currency: str

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/plans", response_model=PlanResponse)
def create_plan(plan_data: PlanCreate, db: Session = Depends(get_db)):
    """Create a new FP&A plan with driver-based assumptions."""
    # Create plan
    plan = FPAPlan(
        entity_id=plan_data.entity_id,
        name=plan_data.name,
        description=plan_data.description,
        plan_version=plan_data.plan_version,
        start_month=plan_data.start_month,
        end_month=plan_data.end_month,
        base_currency=plan_data.base_currency,
        assumptions_json=plan_data.assumptions or {},
        status=PlanStatus.DRAFT
    )
    db.add(plan)
    db.flush()
    
    # Add drivers if provided
    if plan_data.drivers:
        for driver_data in plan_data.drivers:
            driver = PlanDriver(
                plan_id=plan.id,
                driver_type=DriverType(driver_data.driver_type),
                category=driver_data.category,
                subcategory=driver_data.subcategory,
                period_month=driver_data.period_month,
                amount_plan=Decimal(str(driver_data.amount_plan)),
                currency=driver_data.currency,
                days_to_cash=driver_data.days_to_cash,
                days_to_pay=driver_data.days_to_pay,
                cash_timing_distribution=driver_data.cash_timing_distribution,
                driver_formula=driver_data.driver_formula,
                notes=driver_data.notes
            )
            db.add(driver)
    
    db.commit()
    db.refresh(plan)
    
    return PlanResponse(
        id=plan.id,
        entity_id=plan.entity_id,
        name=plan.name,
        description=plan.description,
        plan_version=plan.plan_version,
        start_month=plan.start_month,
        end_month=plan.end_month,
        status=plan.status.value,
        base_currency=plan.base_currency,
        assumptions=plan.assumptions_json,
        created_at=plan.created_at.isoformat(),
        driver_count=len(plan.drivers) if plan.drivers else 0
    )


@router.get("/plans", response_model=List[PlanResponse])
def list_plans(
    entity_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all FP&A plans, optionally filtered."""
    query = db.query(FPAPlan)
    
    if entity_id:
        query = query.filter(FPAPlan.entity_id == entity_id)
    if status:
        query = query.filter(FPAPlan.status == PlanStatus(status))
    
    plans = query.order_by(FPAPlan.created_at.desc()).all()
    
    return [
        PlanResponse(
            id=p.id,
            entity_id=p.entity_id,
            name=p.name,
            description=p.description,
            plan_version=p.plan_version,
            start_month=p.start_month,
            end_month=p.end_month,
            status=p.status.value,
            base_currency=p.base_currency,
            assumptions=p.assumptions_json,
            created_at=p.created_at.isoformat(),
            driver_count=len(p.drivers) if p.drivers else 0
        )
        for p in plans
    ]


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a specific FP&A plan with all drivers."""
    plan = db.query(FPAPlan).filter(FPAPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    drivers = db.query(PlanDriver).filter(PlanDriver.plan_id == plan_id).all()
    
    return {
        "id": plan.id,
        "entity_id": plan.entity_id,
        "name": plan.name,
        "description": plan.description,
        "plan_version": plan.plan_version,
        "start_month": plan.start_month.isoformat(),
        "end_month": plan.end_month.isoformat(),
        "status": plan.status.value,
        "base_currency": plan.base_currency,
        "assumptions": plan.assumptions_json,
        "created_at": plan.created_at.isoformat(),
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
        "drivers": [
            {
                "id": d.id,
                "driver_type": d.driver_type.value,
                "category": d.category,
                "subcategory": d.subcategory,
                "period_month": d.period_month.isoformat(),
                "amount_plan": float(d.amount_plan or 0),
                "currency": d.currency,
                "days_to_cash": d.days_to_cash,
                "days_to_pay": d.days_to_pay,
                "cash_timing_distribution": d.cash_timing_distribution,
                "driver_formula": d.driver_formula,
                "notes": d.notes
            }
            for d in drivers
        ]
    }


@router.post("/plans/{plan_id}/drivers")
def add_driver(plan_id: int, driver_data: PlanDriverCreate, db: Session = Depends(get_db)):
    """Add a driver to an existing plan."""
    plan = db.query(FPAPlan).filter(FPAPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    if plan.status == PlanStatus.LOCKED:
        raise HTTPException(status_code=400, detail="Cannot modify locked plan")
    
    driver = PlanDriver(
        plan_id=plan_id,
        driver_type=DriverType(driver_data.driver_type),
        category=driver_data.category,
        subcategory=driver_data.subcategory,
        period_month=driver_data.period_month,
        amount_plan=Decimal(str(driver_data.amount_plan)),
        currency=driver_data.currency,
        days_to_cash=driver_data.days_to_cash,
        days_to_pay=driver_data.days_to_pay,
        cash_timing_distribution=driver_data.cash_timing_distribution,
        driver_formula=driver_data.driver_formula,
        notes=driver_data.notes
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    
    return {
        "id": driver.id,
        "plan_id": driver.plan_id,
        "driver_type": driver.driver_type.value,
        "category": driver.category,
        "period_month": driver.period_month.isoformat(),
        "amount_plan": float(driver.amount_plan or 0)
    }


@router.post("/plans/{plan_id}/lock")
def lock_plan(plan_id: int, db: Session = Depends(get_db)):
    """Lock a plan (no further modifications allowed)."""
    plan = db.query(FPAPlan).filter(FPAPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.status = PlanStatus.LOCKED
    db.commit()
    
    return {"status": "locked", "plan_id": plan_id}


# ═══════════════════════════════════════════════════════════════════════════════
# BRIDGE GENERATION AND QUERY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/bridge")
def get_bridge(
    plan_id: int = Query(..., description="FP&A Plan ID"),
    snapshot_id: int = Query(..., description="Locked Snapshot ID"),
    regenerate: bool = Query(False, description="Force regenerate bridge"),
    db: Session = Depends(get_db)
):
    """
    Get Cash-to-Plan Bridge.
    
    This endpoint computes an accrual-to-cash bridge explaining how 
    revenue/COGS/opex translate into bank movement via working capital timing.
    
    Every bridge line links to evidence (invoice IDs, bank txn IDs, bill IDs)
    or is marked as Unknown.
    
    Returns:
    - Monthly plan + weekly liquidity overlay
    - Red weeks where plan violates cash constraints
    - Full evidence linking for audit trail
    """
    service = CashToPlanBridgeService(db)
    
    # Check for existing bridge
    existing = service.get_bridge_by_plan_and_snapshot(plan_id, snapshot_id)
    
    if existing and not regenerate:
        # Return existing bridge
        return _format_bridge_response(existing, db)
    
    # Generate new bridge
    try:
        bridge = service.generate_bridge(plan_id, snapshot_id)
        return _format_bridge_response(bridge, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bridge generation failed: {str(e)}")


@router.get("/bridge/{bridge_id}")
def get_bridge_by_id(bridge_id: int, db: Session = Depends(get_db)):
    """Get a specific bridge by ID."""
    service = CashToPlanBridgeService(db)
    bridge = service.get_bridge(bridge_id)
    
    if not bridge:
        raise HTTPException(status_code=404, detail="Bridge not found")
    
    return _format_bridge_response(bridge, db)


@router.get("/bridge/{bridge_id}/lines")
def get_bridge_lines(
    bridge_id: int,
    line_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get bridge lines, optionally filtered by type."""
    service = CashToPlanBridgeService(db)
    
    lt = BridgeLineType(line_type) if line_type else None
    lines = service.get_bridge_lines(bridge_id, lt)
    
    return [
        {
            "id": l.id,
            "line_type": l.line_type.value if l.line_type else None,
            "category": l.category,
            "description": l.description,
            "period_month": l.period_month.isoformat() if l.period_month else None,
            "period_week": l.period_week.isoformat() if l.period_week else None,
            "plan_amount": float(l.plan_amount or 0),
            "plan_cash_amount": float(l.plan_cash_amount or 0),
            "actual_amount": float(l.actual_amount or 0),
            "variance": float(l.variance or 0),
            "timing_days": l.timing_days,
            "has_evidence": l.has_evidence,
            "evidence_type": l.evidence_type.value if l.evidence_type else None,
            "is_unknown": l.is_unknown,
            "unknown_reason": l.unknown_reason,
            "evidence_count": {
                "invoices": l.invoice_count,
                "bank_txns": l.bank_txn_count,
                "vendor_bills": l.vendor_bill_count
            }
        }
        for l in lines
    ]


@router.get("/bridge/{bridge_id}/weekly")
def get_weekly_overlay(bridge_id: int, db: Session = Depends(get_db)):
    """Get weekly overlay for a bridge showing red weeks and cash constraints."""
    service = CashToPlanBridgeService(db)
    overlays = service.get_weekly_overlay(bridge_id)
    
    return [
        {
            "week_number": o.week_number,
            "week_start": o.week_start_date.isoformat() if o.week_start_date else None,
            "week_end": o.week_end_date.isoformat() if o.week_end_date else None,
            "opening_balance_plan": float(o.opening_balance_plan or 0),
            "plan_inflows": float(o.plan_inflows or 0),
            "plan_outflows": float(o.plan_outflows or 0),
            "closing_balance_plan": float(o.closing_balance_plan or 0),
            "actual_inflows": float(o.actual_inflows or 0),
            "actual_outflows": float(o.actual_outflows or 0),
            "closing_balance_actual": float(o.closing_balance_actual or 0),
            "min_cash_required": float(o.min_cash_required or 0),
            "is_red_week": o.is_red_week,
            "cash_shortfall": float(o.cash_shortfall or 0),
            "inflow_variance": float(o.inflow_variance or 0),
            "outflow_variance": float(o.outflow_variance or 0)
        }
        for o in overlays
    ]


@router.get("/bridge/{bridge_id}/lines/{line_id}/evidence")
def get_line_evidence(bridge_id: int, line_id: int, db: Session = Depends(get_db)):
    """
    Get detailed evidence for a specific bridge line.
    
    Returns linked invoices, bank transactions, and vendor bills with full details.
    """
    service = CashToPlanBridgeService(db)
    evidence = service.get_evidence_for_line(line_id)
    
    if "error" in evidence:
        raise HTTPException(status_code=404, detail=evidence["error"])
    
    return evidence


@router.get("/bridge/{bridge_id}/red-weeks")
def get_red_weeks(bridge_id: int, db: Session = Depends(get_db)):
    """Get detailed information about red weeks (cash constraint violations)."""
    bridge = db.query(CashToPlanBridge).filter(CashToPlanBridge.id == bridge_id).first()
    if not bridge:
        raise HTTPException(status_code=404, detail="Bridge not found")
    
    overlays = db.query(WeeklyPlanOverlay).filter(
        WeeklyPlanOverlay.bridge_id == bridge_id,
        WeeklyPlanOverlay.is_red_week == True
    ).order_by(WeeklyPlanOverlay.week_number).all()
    
    return {
        "bridge_id": bridge_id,
        "red_weeks_count": bridge.red_weeks_count,
        "total_shortfall": float(bridge.min_cash_violation_amount or 0),
        "currency": bridge.base_currency,
        "red_weeks": [
            {
                "week_number": o.week_number,
                "week_start": o.week_start_date.isoformat() if o.week_start_date else None,
                "week_end": o.week_end_date.isoformat() if o.week_end_date else None,
                "closing_balance_plan": float(o.closing_balance_plan or 0),
                "min_cash_required": float(o.min_cash_required or 0),
                "shortfall": float(o.cash_shortfall or 0),
                "plan_inflows": float(o.plan_inflows or 0),
                "plan_outflows": float(o.plan_outflows or 0)
            }
            for o in overlays
        ]
    }


@router.get("/bridge/{bridge_id}/unknown")
def get_unknown_items(bridge_id: int, db: Session = Depends(get_db)):
    """Get all unknown/unexplained items from a bridge."""
    service = CashToPlanBridgeService(db)
    lines = service.get_bridge_lines(bridge_id, BridgeLineType.UNKNOWN)
    
    return {
        "bridge_id": bridge_id,
        "unknown_lines": [
            {
                "id": l.id,
                "category": l.category,
                "description": l.description,
                "amount": float(l.actual_amount or 0),
                "unknown_reason": l.unknown_reason,
                "evidence_refs": l.evidence_refs_json,
                "bank_txn_count": l.bank_txn_count
            }
            for l in lines
        ],
        "total_unknown_inflows": sum(
            float(l.actual_amount or 0) for l in lines 
            if (l.actual_amount or 0) > 0
        ),
        "total_unknown_outflows": abs(sum(
            float(l.actual_amount or 0) for l in lines
            if (l.actual_amount or 0) < 0
        ))
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _format_bridge_response(bridge: CashToPlanBridge, db: Session) -> dict:
    """Format bridge for API response."""
    return {
        "id": bridge.id,
        "plan_id": bridge.plan_id,
        "snapshot_id": bridge.snapshot_id,
        "name": bridge.name,
        "generated_at": bridge.generated_at.isoformat() if bridge.generated_at else None,
        "currency": bridge.base_currency,
        "summary": {
            "plan_revenue": float(bridge.total_plan_revenue or 0),
            "plan_cash_inflows": float(bridge.total_plan_cash_inflows or 0),
            "actual_cash_inflows": float(bridge.total_actual_cash_inflows or 0),
            "plan_expenses": float(bridge.total_plan_expenses or 0),
            "plan_cash_outflows": float(bridge.total_plan_cash_outflows or 0),
            "actual_cash_outflows": float(bridge.total_actual_cash_outflows or 0),
            "inflow_variance": float(bridge.total_inflow_variance or 0),
            "outflow_variance": float(bridge.total_outflow_variance or 0),
            "net_variance": float(bridge.net_variance or 0),
            "ar_change": float(bridge.ar_change or 0),
            "ap_change": float(bridge.ap_change or 0),
            "unknown_inflows": float(bridge.unknown_inflows or 0),
            "unknown_outflows": float(bridge.unknown_outflows or 0)
        },
        "red_weeks": {
            "count": bridge.red_weeks_count,
            "total_shortfall": float(bridge.min_cash_violation_amount or 0),
            "weeks": bridge.red_weeks_json or []
        },
        "weekly_overlay": bridge.weekly_overlay_json or [],
        "bridge_output": bridge.bridge_output_json or {}
    }
