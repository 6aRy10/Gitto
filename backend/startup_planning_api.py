"""
Startup/Midmarket Driver-Based Planning API

Opinionated planning endpoints for startups:
- Headcount, Compensation, SaaS Revenue, Churn, CAC, DSO/DPO
- Outputs: P&L, Cashflow Bridge, Runway, Hiring Capacity
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field
from decimal import Decimal

from database import get_db
from startup_planning_service import StartupPlanningService
from startup_planning_models import (
    StartupPlanningScenario, PlanningAssumptions, HeadcountPlan,
    SaaSRevenueDriver, VendorCommitment, PlanningOutput,
    PlanningScenarioStatus, Department, ExpenseCategory
)


router = APIRouter(prefix="/startup-planning", tags=["Startup Planning"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class AssumptionsUpdate(BaseModel):
    """Update planning assumptions."""
    starting_mrr: Optional[float] = None
    mrr_growth_rate_pct: Optional[float] = Field(None, ge=0, le=100)
    monthly_churn_rate_pct: Optional[float] = Field(None, ge=0, le=100)
    average_contract_value: Optional[float] = None
    customer_acquisition_cost: Optional[float] = None
    ltv_to_cac_target: Optional[float] = None
    benefits_pct_of_salary: Optional[float] = Field(None, ge=0, le=100)
    payroll_tax_pct: Optional[float] = Field(None, ge=0, le=100)
    annual_raise_pct: Optional[float] = Field(None, ge=0, le=100)
    dso_days: Optional[int] = Field(None, ge=0, le=365)
    dpo_days: Optional[int] = Field(None, ge=0, le=365)
    annual_prepay_pct: Optional[float] = Field(None, ge=0, le=100)
    saas_cost_per_employee: Optional[float] = None
    infra_pct_of_revenue: Optional[float] = Field(None, ge=0, le=100)
    marketing_pct_of_new_arr: Optional[float] = Field(None, ge=0, le=100)
    office_cost_per_employee: Optional[float] = None
    starting_cash: Optional[float] = None
    min_cash_buffer: Optional[float] = None
    avg_salaries_by_dept: Optional[dict] = None


class HeadcountCreate(BaseModel):
    """Create a headcount plan entry."""
    department: str
    role_title: str
    seniority_level: Optional[str] = None
    annual_salary: float
    start_month: date
    end_month: Optional[date] = None
    headcount: int = 1
    is_backfill: bool = False
    notes: Optional[str] = None


class VendorCommitmentCreate(BaseModel):
    """Create a vendor commitment."""
    vendor_name: str
    category: str = "saas_tools"
    monthly_amount: float
    annual_amount: Optional[float] = None
    payment_frequency: str = "monthly"
    payment_terms_days: int = 30
    start_date: date
    end_date: Optional[date] = None
    auto_renews: bool = True
    notes: Optional[str] = None


class RevenueDriverCreate(BaseModel):
    """Create/update a revenue driver for a specific month."""
    period_month: date
    starting_customers: int = 0
    new_customers: int = 0
    churned_customers: int = 0
    starting_mrr: float = 0
    new_mrr: float = 0
    expansion_mrr: float = 0
    churned_mrr: float = 0
    cac_spend: float = 0
    notes: Optional[str] = None


class ScenarioCreate(BaseModel):
    """Create a planning scenario."""
    entity_id: int
    name: str
    description: Optional[str] = None
    start_month: date
    end_month: date
    is_base: bool = False
    base_currency: str = "USD"


class BranchCreate(BaseModel):
    """Create a branch from existing scenario."""
    branch_name: str
    branch_reason: str


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/scenarios")
def create_scenario(data: ScenarioCreate, db: Session = Depends(get_db)):
    """Create a new planning scenario."""
    service = StartupPlanningService(db)
    scenario = service.create_scenario(
        entity_id=data.entity_id,
        name=data.name,
        start_month=data.start_month,
        end_month=data.end_month,
        is_base=data.is_base,
        description=data.description,
        base_currency=data.base_currency
    )
    return _format_scenario(scenario)


@router.get("/scenarios")
def list_scenarios(
    entity_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all scenarios for an entity."""
    service = StartupPlanningService(db)
    scenarios = service.get_scenarios(entity_id)
    
    if status:
        scenarios = [s for s in scenarios if s.status.value == status]
    
    return [_format_scenario(s) for s in scenarios]


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Get a specific scenario with all details."""
    service = StartupPlanningService(db)
    scenario = service.get_scenario(scenario_id)
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return _format_scenario_detail(scenario)


@router.post("/scenarios/{scenario_id}/branch")
def branch_scenario(
    scenario_id: int,
    data: BranchCreate,
    db: Session = Depends(get_db)
):
    """Create a branch from an existing scenario."""
    service = StartupPlanningService(db)
    
    try:
        branch = service.branch_scenario(
            parent_scenario_id=scenario_id,
            branch_name=data.branch_name,
            branch_reason=data.branch_reason
        )
        return _format_scenario(branch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/scenarios/{scenario_id}/submit")
def submit_for_approval(
    scenario_id: int,
    submitted_by: str = Query(...),
    db: Session = Depends(get_db)
):
    """Submit scenario for approval."""
    service = StartupPlanningService(db)
    
    try:
        scenario = service.submit_for_approval(scenario_id, submitted_by)
        return {"status": "submitted", "scenario_id": scenario_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/scenarios/{scenario_id}/approve")
def approve_scenario(
    scenario_id: int,
    approved_by: str = Query(...),
    approval_notes: Optional[str] = None,
    snapshot_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Approve a scenario."""
    service = StartupPlanningService(db)
    
    try:
        scenario = service.approve_scenario(
            scenario_id, approved_by, approval_notes, snapshot_id
        )
        return {
            "status": "approved",
            "scenario_id": scenario_id,
            "version": scenario.version
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ASSUMPTIONS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/scenarios/{scenario_id}/assumptions")
def get_assumptions(scenario_id: int, db: Session = Depends(get_db)):
    """Get assumptions for a scenario."""
    scenario = db.query(StartupPlanningScenario).filter(
        StartupPlanningScenario.id == scenario_id
    ).first()
    
    if not scenario or not scenario.assumptions:
        raise HTTPException(status_code=404, detail="Scenario or assumptions not found")
    
    return _format_assumptions(scenario.assumptions)


@router.put("/scenarios/{scenario_id}/assumptions")
def update_assumptions(
    scenario_id: int,
    data: AssumptionsUpdate,
    db: Session = Depends(get_db)
):
    """Update assumptions for a scenario."""
    scenario = db.query(StartupPlanningScenario).filter(
        StartupPlanningScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if scenario.status == PlanningScenarioStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Cannot modify approved scenario")
    
    assumptions = scenario.assumptions
    if not assumptions:
        assumptions = PlanningAssumptions(scenario_id=scenario_id)
        db.add(assumptions)
    
    # Update fields
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "avg_salaries_by_dept":
            assumptions.avg_salaries_by_dept_json = value
        elif hasattr(assumptions, field):
            setattr(assumptions, field, Decimal(str(value)) if value is not None else None)
    
    assumptions.version += 1
    db.commit()
    
    return _format_assumptions(assumptions)


# ═══════════════════════════════════════════════════════════════════════════════
# HEADCOUNT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/scenarios/{scenario_id}/headcount")
def get_headcount(scenario_id: int, db: Session = Depends(get_db)):
    """Get headcount plan for a scenario."""
    headcount = db.query(HeadcountPlan).filter(
        HeadcountPlan.scenario_id == scenario_id
    ).all()
    
    return [_format_headcount(h) for h in headcount]


@router.post("/scenarios/{scenario_id}/headcount")
def add_headcount(
    scenario_id: int,
    data: HeadcountCreate,
    db: Session = Depends(get_db)
):
    """Add a headcount entry."""
    scenario = db.query(StartupPlanningScenario).filter(
        StartupPlanningScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    if scenario.status == PlanningScenarioStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Cannot modify approved scenario")
    
    try:
        dept = Department(data.department)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid department: {data.department}")
    
    hc = HeadcountPlan(
        scenario_id=scenario_id,
        department=dept,
        role_title=data.role_title,
        seniority_level=data.seniority_level,
        annual_salary=Decimal(str(data.annual_salary)),
        start_month=data.start_month,
        end_month=data.end_month,
        headcount=data.headcount,
        is_backfill=data.is_backfill,
        notes=data.notes
    )
    db.add(hc)
    db.commit()
    
    return _format_headcount(hc)


@router.delete("/scenarios/{scenario_id}/headcount/{headcount_id}")
def delete_headcount(
    scenario_id: int,
    headcount_id: int,
    db: Session = Depends(get_db)
):
    """Delete a headcount entry."""
    hc = db.query(HeadcountPlan).filter(
        HeadcountPlan.id == headcount_id,
        HeadcountPlan.scenario_id == scenario_id
    ).first()
    
    if not hc:
        raise HTTPException(status_code=404, detail="Headcount entry not found")
    
    db.delete(hc)
    db.commit()
    
    return {"deleted": True, "id": headcount_id}


# ═══════════════════════════════════════════════════════════════════════════════
# VENDOR COMMITMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/scenarios/{scenario_id}/vendors")
def get_vendors(scenario_id: int, db: Session = Depends(get_db)):
    """Get vendor commitments for a scenario."""
    vendors = db.query(VendorCommitment).filter(
        VendorCommitment.scenario_id == scenario_id
    ).all()
    
    return [_format_vendor(v) for v in vendors]


@router.post("/scenarios/{scenario_id}/vendors")
def add_vendor(
    scenario_id: int,
    data: VendorCommitmentCreate,
    db: Session = Depends(get_db)
):
    """Add a vendor commitment."""
    scenario = db.query(StartupPlanningScenario).filter(
        StartupPlanningScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    try:
        category = ExpenseCategory(data.category)
    except ValueError:
        category = ExpenseCategory.OTHER
    
    vendor = VendorCommitment(
        scenario_id=scenario_id,
        vendor_name=data.vendor_name,
        category=category,
        monthly_amount=Decimal(str(data.monthly_amount)),
        annual_amount=Decimal(str(data.annual_amount)) if data.annual_amount else None,
        payment_frequency=data.payment_frequency,
        payment_terms_days=data.payment_terms_days,
        start_date=data.start_date,
        end_date=data.end_date,
        auto_renews=data.auto_renews,
        notes=data.notes
    )
    db.add(vendor)
    db.commit()
    
    return _format_vendor(vendor)


# ═══════════════════════════════════════════════════════════════════════════════
# REVENUE DRIVER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/scenarios/{scenario_id}/revenue-drivers")
def get_revenue_drivers(scenario_id: int, db: Session = Depends(get_db)):
    """Get revenue drivers for a scenario."""
    drivers = db.query(SaaSRevenueDriver).filter(
        SaaSRevenueDriver.scenario_id == scenario_id
    ).order_by(SaaSRevenueDriver.period_month).all()
    
    return [_format_revenue_driver(d) for d in drivers]


@router.post("/scenarios/{scenario_id}/revenue-drivers")
def add_revenue_driver(
    scenario_id: int,
    data: RevenueDriverCreate,
    db: Session = Depends(get_db)
):
    """Add or update a revenue driver for a month."""
    scenario = db.query(StartupPlanningScenario).filter(
        StartupPlanningScenario.id == scenario_id
    ).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Check for existing driver for this month
    existing = db.query(SaaSRevenueDriver).filter(
        SaaSRevenueDriver.scenario_id == scenario_id,
        SaaSRevenueDriver.period_month == data.period_month
    ).first()
    
    if existing:
        # Update existing
        existing.starting_customers = data.starting_customers
        existing.new_customers = data.new_customers
        existing.churned_customers = data.churned_customers
        existing.ending_customers = data.starting_customers + data.new_customers - data.churned_customers
        existing.starting_mrr = Decimal(str(data.starting_mrr))
        existing.new_mrr = Decimal(str(data.new_mrr))
        existing.expansion_mrr = Decimal(str(data.expansion_mrr))
        existing.churned_mrr = Decimal(str(data.churned_mrr))
        existing.ending_mrr = Decimal(str(data.starting_mrr + data.new_mrr + data.expansion_mrr - data.churned_mrr))
        existing.ending_arr = existing.ending_mrr * 12
        existing.cac_spend = Decimal(str(data.cac_spend))
        existing.notes = data.notes
        driver = existing
    else:
        # Create new
        ending_customers = data.starting_customers + data.new_customers - data.churned_customers
        ending_mrr = data.starting_mrr + data.new_mrr + data.expansion_mrr - data.churned_mrr
        
        driver = SaaSRevenueDriver(
            scenario_id=scenario_id,
            period_month=data.period_month,
            starting_customers=data.starting_customers,
            new_customers=data.new_customers,
            churned_customers=data.churned_customers,
            ending_customers=ending_customers,
            starting_mrr=Decimal(str(data.starting_mrr)),
            new_mrr=Decimal(str(data.new_mrr)),
            expansion_mrr=Decimal(str(data.expansion_mrr)),
            churned_mrr=Decimal(str(data.churned_mrr)),
            ending_mrr=Decimal(str(ending_mrr)),
            ending_arr=Decimal(str(ending_mrr * 12)),
            cac_spend=Decimal(str(data.cac_spend)),
            notes=data.notes
        )
        db.add(driver)
    
    db.commit()
    return _format_revenue_driver(driver)


# ═══════════════════════════════════════════════════════════════════════════════
# OUTPUT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/scenarios/{scenario_id}/generate")
def generate_outputs(scenario_id: int, db: Session = Depends(get_db)):
    """Generate all outputs for a scenario."""
    service = StartupPlanningService(db)
    
    try:
        output = service.generate_outputs(scenario_id)
        return _format_output(output)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scenarios/{scenario_id}/outputs")
def get_outputs(scenario_id: int, db: Session = Depends(get_db)):
    """Get generated outputs for a scenario."""
    service = StartupPlanningService(db)
    output = service.get_output(scenario_id)
    
    if not output:
        raise HTTPException(status_code=404, detail="Outputs not generated yet")
    
    return _format_output(output)


@router.get("/scenarios/{scenario_id}/pnl")
def get_pnl(scenario_id: int, db: Session = Depends(get_db)):
    """Get P&L for a scenario."""
    service = StartupPlanningService(db)
    output = service.get_output(scenario_id)
    
    if not output:
        raise HTTPException(status_code=404, detail="Outputs not generated yet")
    
    return {
        "scenario_id": scenario_id,
        "monthly_pnl": output.monthly_pnl_json,
        "total_revenue": float(output.total_revenue or 0),
        "total_expenses": float(output.total_expenses or 0),
        "ending_mrr": float(output.ending_mrr or 0),
        "ending_arr": float(output.ending_arr or 0)
    }


@router.get("/scenarios/{scenario_id}/cashflow")
def get_cashflow(scenario_id: int, db: Session = Depends(get_db)):
    """Get cashflow bridge for a scenario."""
    service = StartupPlanningService(db)
    output = service.get_output(scenario_id)
    
    if not output:
        raise HTTPException(status_code=404, detail="Outputs not generated yet")
    
    return {
        "scenario_id": scenario_id,
        "monthly_cashflow": output.monthly_cashflow_json,
        "ending_cash": float(output.ending_cash or 0)
    }


@router.get("/scenarios/{scenario_id}/runway")
def get_runway(scenario_id: int, db: Session = Depends(get_db)):
    """Get runway analysis for a scenario."""
    service = StartupPlanningService(db)
    output = service.get_output(scenario_id)
    
    if not output:
        raise HTTPException(status_code=404, detail="Outputs not generated yet")
    
    return {
        "scenario_id": scenario_id,
        "runway_months": output.runway_months,
        "cash_zero_date": output.cash_zero_date.isoformat() if output.cash_zero_date else None,
        "analysis": output.runway_analysis_json
    }


@router.get("/scenarios/{scenario_id}/hiring-capacity")
def get_hiring_capacity(scenario_id: int, db: Session = Depends(get_db)):
    """Get hiring capacity analysis for a scenario."""
    service = StartupPlanningService(db)
    output = service.get_output(scenario_id)
    
    if not output:
        raise HTTPException(status_code=404, detail="Outputs not generated yet")
    
    return {
        "scenario_id": scenario_id,
        "max_additional_hires": output.max_additional_hires,
        "analysis": output.hiring_capacity_details_json
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/compare")
def compare_scenarios(
    base_scenario_id: int = Query(...),
    compare_scenario_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Compare two scenarios."""
    service = StartupPlanningService(db)
    
    try:
        comparison = service.compare_scenarios(base_scenario_id, compare_scenario_id)
        return {
            "base_scenario_id": base_scenario_id,
            "compare_scenario_id": compare_scenario_id,
            "comparison": comparison.comparison_json,
            "summary": comparison.summary
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _format_scenario(s: StartupPlanningScenario) -> dict:
    return {
        "id": s.id,
        "entity_id": s.entity_id,
        "name": s.name,
        "description": s.description,
        "version": s.version,
        "is_base": s.is_base,
        "parent_scenario_id": s.parent_scenario_id,
        "start_month": s.start_month.isoformat() if s.start_month else None,
        "end_month": s.end_month.isoformat() if s.end_month else None,
        "status": s.status.value,
        "base_currency": s.base_currency,
        "created_at": s.created_at.isoformat() if s.created_at else None
    }


def _format_scenario_detail(s: StartupPlanningScenario) -> dict:
    result = _format_scenario(s)
    result["assumptions"] = _format_assumptions(s.assumptions) if s.assumptions else None
    result["headcount_count"] = len(s.headcount_plan) if s.headcount_plan else 0
    result["vendor_count"] = len(s.vendor_commitments) if s.vendor_commitments else 0
    result["approval"] = {
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        "submitted_by": s.submitted_by,
        "approved_at": s.approved_at.isoformat() if s.approved_at else None,
        "approved_by": s.approved_by,
        "approval_notes": s.approval_notes,
        "snapshot_id": s.snapshot_id
    }
    return result


def _format_assumptions(a: PlanningAssumptions) -> dict:
    return {
        "id": a.id,
        "version": a.version,
        "revenue": {
            "starting_mrr": float(a.starting_mrr or 0),
            "mrr_growth_rate_pct": float(a.mrr_growth_rate_pct or 0),
            "monthly_churn_rate_pct": float(a.monthly_churn_rate_pct or 0),
            "average_contract_value": float(a.average_contract_value or 0),
            "customer_acquisition_cost": float(a.customer_acquisition_cost or 0),
            "ltv_to_cac_target": float(a.ltv_to_cac_target or 0)
        },
        "compensation": {
            "benefits_pct_of_salary": float(a.benefits_pct_of_salary or 0),
            "payroll_tax_pct": float(a.payroll_tax_pct or 0),
            "annual_raise_pct": float(a.annual_raise_pct or 0),
            "avg_salaries_by_dept": a.avg_salaries_by_dept_json or {}
        },
        "working_capital": {
            "dso_days": a.dso_days or 0,
            "dpo_days": a.dpo_days or 0,
            "annual_prepay_pct": float(a.annual_prepay_pct or 0)
        },
        "operating": {
            "saas_cost_per_employee": float(a.saas_cost_per_employee or 0),
            "infra_pct_of_revenue": float(a.infra_pct_of_revenue or 0),
            "marketing_pct_of_new_arr": float(a.marketing_pct_of_new_arr or 0),
            "office_cost_per_employee": float(a.office_cost_per_employee or 0)
        },
        "cash": {
            "starting_cash": float(a.starting_cash or 0),
            "min_cash_buffer": float(a.min_cash_buffer or 0)
        }
    }


def _format_headcount(h: HeadcountPlan) -> dict:
    return {
        "id": h.id,
        "department": h.department.value if h.department else None,
        "role_title": h.role_title,
        "seniority_level": h.seniority_level,
        "annual_salary": float(h.annual_salary or 0),
        "start_month": h.start_month.isoformat() if h.start_month else None,
        "end_month": h.end_month.isoformat() if h.end_month else None,
        "headcount": h.headcount,
        "is_backfill": h.is_backfill,
        "notes": h.notes
    }


def _format_vendor(v: VendorCommitment) -> dict:
    return {
        "id": v.id,
        "vendor_name": v.vendor_name,
        "category": v.category.value if v.category else None,
        "monthly_amount": float(v.monthly_amount or 0),
        "annual_amount": float(v.annual_amount or 0) if v.annual_amount else None,
        "payment_frequency": v.payment_frequency,
        "payment_terms_days": v.payment_terms_days,
        "start_date": v.start_date.isoformat() if v.start_date else None,
        "end_date": v.end_date.isoformat() if v.end_date else None,
        "auto_renews": v.auto_renews,
        "notes": v.notes
    }


def _format_revenue_driver(d: SaaSRevenueDriver) -> dict:
    return {
        "id": d.id,
        "period_month": d.period_month.isoformat() if d.period_month else None,
        "customers": {
            "starting": d.starting_customers,
            "new": d.new_customers,
            "churned": d.churned_customers,
            "ending": d.ending_customers
        },
        "mrr": {
            "starting": float(d.starting_mrr or 0),
            "new": float(d.new_mrr or 0),
            "expansion": float(d.expansion_mrr or 0),
            "churned": float(d.churned_mrr or 0),
            "ending": float(d.ending_mrr or 0)
        },
        "arr": float(d.ending_arr or 0),
        "cac_spend": float(d.cac_spend or 0),
        "notes": d.notes
    }


def _format_output(o: PlanningOutput) -> dict:
    return {
        "id": o.id,
        "scenario_id": o.scenario_id,
        "generated_at": o.generated_at.isoformat() if o.generated_at else None,
        "assumptions_version": o.assumptions_version,
        "summary": {
            "runway_months": o.runway_months,
            "cash_zero_date": o.cash_zero_date.isoformat() if o.cash_zero_date else None,
            "max_additional_hires": o.max_additional_hires,
            "ending_mrr": float(o.ending_mrr or 0),
            "ending_arr": float(o.ending_arr or 0),
            "ending_customers": o.ending_customers,
            "total_revenue": float(o.total_revenue or 0),
            "total_expenses": float(o.total_expenses or 0),
            "total_burn": float(o.total_burn or 0),
            "ending_cash": float(o.ending_cash or 0)
        },
        "monthly_pnl": o.monthly_pnl_json,
        "monthly_cashflow": o.monthly_cashflow_json,
        "monthly_headcount": o.monthly_headcount_json,
        "runway_analysis": o.runway_analysis_json,
        "hiring_analysis": o.hiring_analysis_json
    }
