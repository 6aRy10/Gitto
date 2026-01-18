"""
FP&A API Endpoints

CRUD operations and workflow triggers for financial planning and analysis.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import get_db
from fpa_models import (
    Plan, PlanStatus, AssumptionSet, Driver, DriverSource,
    ActualsSnapshot, ForecastRun, Scenario, ScenarioStatus, ScenarioDiff,
    FPAArtifact, FPADecision, FPAApproval, VarianceReport, FPAAuditLog
)

router = APIRouter(prefix="/fpa", tags=["FP&A Planning"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreatePlanRequest(BaseModel):
    entity_id: int
    name: str
    description: Optional[str] = None
    period_start: date
    period_end: date
    base_currency: str = "EUR"
    fiscal_year_start_month: int = 1
    created_by: Optional[str] = None


class CreateAssumptionSetRequest(BaseModel):
    version_label: Optional[str] = None
    notes: Optional[str] = None
    parent_version_id: Optional[int] = None
    created_by: Optional[str] = None
    drivers: List[Dict[str, Any]] = Field(default_factory=list)


class CreateDriverRequest(BaseModel):
    key: str
    value: float
    category: Optional[str] = None
    subcategory: Optional[str] = None
    unit: Optional[str] = None
    effective_month: Optional[date] = None
    source: str = "manual"
    source_system: Optional[str] = None
    description: Optional[str] = None
    evidence_refs_json: Optional[Dict] = None


class CreateActualsSnapshotRequest(BaseModel):
    entity_id: int
    period_month: date
    period_label: Optional[str] = None
    source_dataset_id: Optional[int] = None
    gl_data_json: Optional[Dict] = None
    ar_aggregates_json: Optional[Dict] = None
    ap_aggregates_json: Optional[Dict] = None
    bank_data_json: Optional[Dict] = None


class LockActualsRequest(BaseModel):
    locked_by: str
    lock_reason: Optional[str] = None


class RunForecastRequest(BaseModel):
    assumption_set_id: int
    actuals_snapshot_id: Optional[int] = None
    run_label: Optional[str] = None
    forecast_horizon_months: int = 12
    created_by: Optional[str] = None


class CreateScenarioRequest(BaseModel):
    base_assumption_set_id: int
    name: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    driver_changes: Dict[str, Any] = Field(default_factory=dict)


class ApproveDecisionRequest(BaseModel):
    user_id: str
    option_selected: str
    note: Optional[str] = None


# =============================================================================
# PLAN ENDPOINTS
# =============================================================================

@router.post("/plans")
async def create_plan(
    request: CreatePlanRequest,
    db: Session = Depends(get_db),
):
    """Create a new planning cycle"""
    plan = Plan(
        entity_id=request.entity_id,
        name=request.name,
        description=request.description,
        period_start=request.period_start,
        period_end=request.period_end,
        base_currency=request.base_currency,
        fiscal_year_start_month=request.fiscal_year_start_month,
        created_by=request.created_by,
        status=PlanStatus.DRAFT,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Log
    _log_action(db, plan.entity_id, "create", "plan", plan.id, request.created_by)
    
    return plan.to_dict()


@router.get("/plans")
async def list_plans(
    entity_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List plans for an entity"""
    query = db.query(Plan).filter(Plan.entity_id == entity_id)
    
    if status:
        query = query.filter(Plan.status == PlanStatus(status))
    
    plans = query.order_by(Plan.created_at.desc()).all()
    return {"plans": [p.to_dict() for p in plans]}


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific plan"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {
        **plan.to_dict(),
        "assumption_sets": [a.to_dict() for a in plan.assumption_sets],
        "scenarios": [s.to_dict() for s in plan.scenarios],
    }


@router.patch("/plans/{plan_id}/status")
async def update_plan_status(
    plan_id: int,
    status: str,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Update plan status"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.status = PlanStatus(status)
    db.commit()
    
    _log_action(db, plan.entity_id, "update_status", "plan", plan.id, user_id, {"status": status})
    
    return plan.to_dict()


# =============================================================================
# ASSUMPTION SET ENDPOINTS
# =============================================================================

@router.post("/plans/{plan_id}/assumptions")
async def create_assumption_set(
    plan_id: int,
    request: CreateAssumptionSetRequest,
    db: Session = Depends(get_db),
):
    """Create a new version of assumptions"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Get next version number
    max_version = db.query(AssumptionSet).filter(
        AssumptionSet.plan_id == plan_id
    ).count()
    
    assumption_set = AssumptionSet(
        plan_id=plan_id,
        version=max_version + 1,
        version_label=request.version_label,
        notes=request.notes,
        parent_version_id=request.parent_version_id,
        created_by=request.created_by,
    )
    db.add(assumption_set)
    db.flush()  # Get ID
    
    # Add drivers
    for driver_data in request.drivers:
        driver = Driver(
            assumption_set_id=assumption_set.id,
            key=driver_data["key"],
            value=Decimal(str(driver_data["value"])),
            category=driver_data.get("category"),
            subcategory=driver_data.get("subcategory"),
            unit=driver_data.get("unit"),
            effective_month=driver_data.get("effective_month"),
            source=DriverSource(driver_data.get("source", "manual")),
            source_system=driver_data.get("source_system"),
            description=driver_data.get("description"),
            evidence_refs_json=driver_data.get("evidence_refs_json"),
        )
        db.add(driver)
    
    db.commit()
    db.refresh(assumption_set)
    
    _log_action(db, plan.entity_id, "create", "assumption_set", assumption_set.id, request.created_by)
    
    return assumption_set.to_dict()


@router.get("/plans/{plan_id}/assumptions")
async def list_assumption_sets(
    plan_id: int,
    db: Session = Depends(get_db),
):
    """List all assumption set versions for a plan"""
    sets = db.query(AssumptionSet).filter(
        AssumptionSet.plan_id == plan_id
    ).order_by(AssumptionSet.version.desc()).all()
    
    return {"assumption_sets": [s.to_dict() for s in sets]}


@router.get("/assumptions/{assumption_set_id}")
async def get_assumption_set(
    assumption_set_id: int,
    db: Session = Depends(get_db),
):
    """Get an assumption set with all drivers"""
    assumption_set = db.query(AssumptionSet).filter(
        AssumptionSet.id == assumption_set_id
    ).first()
    
    if not assumption_set:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    return {
        **assumption_set.to_dict(),
        "drivers": [d.to_dict() for d in assumption_set.drivers],
    }


@router.post("/assumptions/{assumption_set_id}/drivers")
async def add_driver(
    assumption_set_id: int,
    request: CreateDriverRequest,
    db: Session = Depends(get_db),
):
    """Add a driver to an assumption set"""
    assumption_set = db.query(AssumptionSet).filter(
        AssumptionSet.id == assumption_set_id
    ).first()
    
    if not assumption_set:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    driver = Driver(
        assumption_set_id=assumption_set_id,
        key=request.key,
        value=Decimal(str(request.value)),
        category=request.category,
        subcategory=request.subcategory,
        unit=request.unit,
        effective_month=request.effective_month,
        source=DriverSource(request.source),
        source_system=request.source_system,
        description=request.description,
        evidence_refs_json=request.evidence_refs_json,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    
    return driver.to_dict()


# =============================================================================
# ACTUALS SNAPSHOT ENDPOINTS
# =============================================================================

@router.post("/actuals-snapshots")
async def create_actuals_snapshot(
    request: CreateActualsSnapshotRequest,
    db: Session = Depends(get_db),
):
    """Create an actuals snapshot"""
    # Check for existing snapshot for this period
    existing = db.query(ActualsSnapshot).filter(
        ActualsSnapshot.entity_id == request.entity_id,
        ActualsSnapshot.period_month == request.period_month,
    ).first()
    
    if existing and existing.locked:
        raise HTTPException(
            status_code=400,
            detail="Locked snapshot already exists for this period"
        )
    
    if existing:
        # Update existing unlocked snapshot
        existing.gl_data_json = request.gl_data_json
        existing.ar_aggregates_json = request.ar_aggregates_json
        existing.ap_aggregates_json = request.ap_aggregates_json
        existing.bank_data_json = request.bank_data_json
        existing.source_dataset_id = request.source_dataset_id
        db.commit()
        db.refresh(existing)
        return existing.to_dict()
    
    snapshot = ActualsSnapshot(
        entity_id=request.entity_id,
        period_month=request.period_month,
        period_label=request.period_label,
        source_dataset_id=request.source_dataset_id,
        gl_data_json=request.gl_data_json,
        ar_aggregates_json=request.ar_aggregates_json,
        ap_aggregates_json=request.ap_aggregates_json,
        bank_data_json=request.bank_data_json,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    _log_action(db, request.entity_id, "create", "actuals_snapshot", snapshot.id)
    
    return snapshot.to_dict()


@router.get("/actuals-snapshots")
async def list_actuals_snapshots(
    entity_id: int,
    locked_only: bool = False,
    db: Session = Depends(get_db),
):
    """List actuals snapshots for an entity"""
    query = db.query(ActualsSnapshot).filter(
        ActualsSnapshot.entity_id == entity_id
    )
    
    if locked_only:
        query = query.filter(ActualsSnapshot.locked == True)
    
    snapshots = query.order_by(ActualsSnapshot.period_month.desc()).all()
    return {"snapshots": [s.to_dict() for s in snapshots]}


@router.post("/actuals-snapshots/{snapshot_id}/lock")
async def lock_actuals_snapshot(
    snapshot_id: int,
    request: LockActualsRequest,
    db: Session = Depends(get_db),
):
    """Lock an actuals snapshot (makes it immutable)"""
    snapshot = db.query(ActualsSnapshot).filter(
        ActualsSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    if snapshot.locked:
        raise HTTPException(status_code=400, detail="Snapshot is already locked")
    
    snapshot.locked = True
    snapshot.locked_at = datetime.utcnow()
    snapshot.locked_by = request.locked_by
    snapshot.lock_reason = request.lock_reason
    
    db.commit()
    db.refresh(snapshot)
    
    _log_action(db, snapshot.entity_id, "lock", "actuals_snapshot", snapshot.id, request.locked_by)
    
    return snapshot.to_dict()


# =============================================================================
# FORECAST ENDPOINTS
# =============================================================================

@router.post("/plans/{plan_id}/forecast")
async def run_forecast(
    plan_id: int,
    request: RunForecastRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Run a forecast computation"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    assumption_set = db.query(AssumptionSet).filter(
        AssumptionSet.id == request.assumption_set_id
    ).first()
    if not assumption_set:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    
    # Create forecast run record
    forecast_run = ForecastRun(
        plan_id=plan_id,
        assumption_set_id=request.assumption_set_id,
        actuals_snapshot_id=request.actuals_snapshot_id,
        run_label=request.run_label,
        forecast_horizon_months=request.forecast_horizon_months,
        created_by=request.created_by,
    )
    db.add(forecast_run)
    db.commit()
    db.refresh(forecast_run)
    
    # Run computation in background
    background_tasks.add_task(
        _compute_forecast,
        forecast_run.id,
    )
    
    _log_action(db, plan.entity_id, "run_forecast", "forecast_run", forecast_run.id, request.created_by)
    
    return {
        "message": "Forecast computation started",
        "forecast_run_id": forecast_run.id,
    }


@router.get("/forecast-runs/{run_id}")
async def get_forecast_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    """Get forecast run results"""
    run = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    
    return run.to_dict()


@router.get("/plans/{plan_id}/forecast-runs")
async def list_forecast_runs(
    plan_id: int,
    db: Session = Depends(get_db),
):
    """List all forecast runs for a plan"""
    runs = db.query(ForecastRun).filter(
        ForecastRun.plan_id == plan_id
    ).order_by(ForecastRun.created_at.desc()).all()
    
    return {"forecast_runs": [r.to_dict() for r in runs]}


# =============================================================================
# SCENARIO ENDPOINTS
# =============================================================================

@router.post("/plans/{plan_id}/scenarios")
async def create_scenario(
    plan_id: int,
    request: CreateScenarioRequest,
    db: Session = Depends(get_db),
):
    """Create a what-if scenario"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    scenario = Scenario(
        plan_id=plan_id,
        base_assumption_set_id=request.base_assumption_set_id,
        name=request.name,
        description=request.description,
        created_by=request.created_by,
        status=ScenarioStatus.DRAFT,
    )
    db.add(scenario)
    db.flush()
    
    # Create initial diff if driver changes provided
    if request.driver_changes:
        diff = ScenarioDiff(
            scenario_id=scenario.id,
            diff_json=request.driver_changes,
        )
        db.add(diff)
    
    db.commit()
    db.refresh(scenario)
    
    _log_action(db, plan.entity_id, "create", "scenario", scenario.id, request.created_by)
    
    return scenario.to_dict()


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
):
    """Get a scenario with its diffs"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return {
        **scenario.to_dict(),
        "diffs": [d.to_dict() for d in scenario.diffs],
    }


@router.get("/scenarios/{scenario_id}/compare")
async def compare_scenarios(
    scenario_id: int,
    compare_to_scenario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Compare a scenario to base or another scenario"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Get the latest diff for this scenario
    latest_diff = db.query(ScenarioDiff).filter(
        ScenarioDiff.scenario_id == scenario_id
    ).order_by(ScenarioDiff.created_at.desc()).first()
    
    comparison = {
        "scenario": scenario.to_dict(),
        "diff": latest_diff.to_dict() if latest_diff else None,
        "impact_summary": latest_diff.impact_summary_json if latest_diff else None,
    }
    
    if compare_to_scenario_id:
        compare_scenario = db.query(Scenario).filter(
            Scenario.id == compare_to_scenario_id
        ).first()
        if compare_scenario:
            comparison["compare_to"] = compare_scenario.to_dict()
    
    return comparison


# =============================================================================
# DECISION ENDPOINTS
# =============================================================================

@router.get("/decisions")
async def list_decisions(
    entity_id: int,
    status: Optional[str] = None,
    decision_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List decisions for an entity"""
    query = db.query(FPADecision).filter(FPADecision.entity_id == entity_id)
    
    if status:
        query = query.filter(FPADecision.status == status)
    if decision_type:
        query = query.filter(FPADecision.decision_type == decision_type)
    
    decisions = query.order_by(FPADecision.created_at.desc()).all()
    return {"decisions": [d.to_dict() for d in decisions]}


@router.get("/decisions/{decision_id}")
async def get_decision(
    decision_id: int,
    db: Session = Depends(get_db),
):
    """Get a decision with approvals"""
    decision = db.query(FPADecision).filter(FPADecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return {
        **decision.to_dict(),
        "approvals": [a.to_dict() for a in decision.approvals],
    }


@router.post("/decisions/{decision_id}/approve")
async def approve_decision(
    decision_id: int,
    request: ApproveDecisionRequest,
    db: Session = Depends(get_db),
):
    """Approve or reject a decision"""
    decision = db.query(FPADecision).filter(FPADecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    if decision.status != "pending":
        raise HTTPException(status_code=400, detail="Decision is not pending")
    
    # Create approval record
    approval = FPAApproval(
        decision_id=decision_id,
        user_id=request.user_id,
        option_selected=request.option_selected,
        note=request.note,
    )
    db.add(approval)
    
    # Update decision status
    decision.status = "approved" if request.option_selected != "reject" else "rejected"
    decision.resolved_at = datetime.utcnow()
    
    db.commit()
    
    _log_action(db, decision.entity_id, "approve", "decision", decision.id, request.user_id)
    
    return decision.to_dict()


# =============================================================================
# VARIANCE REPORT ENDPOINTS
# =============================================================================

@router.get("/variance-reports")
async def list_variance_reports(
    entity_id: int,
    comparison_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List variance reports for an entity"""
    query = db.query(VarianceReport).filter(VarianceReport.entity_id == entity_id)
    
    if comparison_type:
        query = query.filter(VarianceReport.comparison_type == comparison_type)
    
    reports = query.order_by(VarianceReport.created_at.desc()).all()
    return {"reports": [r.to_dict() for r in reports]}


@router.get("/variance-reports/{report_id}")
async def get_variance_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Get a variance report"""
    report = db.query(VarianceReport).filter(VarianceReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report.to_dict()


# =============================================================================
# ARTIFACT ENDPOINTS
# =============================================================================

@router.get("/artifacts")
async def list_artifacts(
    entity_id: int,
    artifact_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List artifacts for an entity"""
    query = db.query(FPAArtifact).filter(FPAArtifact.entity_id == entity_id)
    
    if artifact_type:
        query = query.filter(FPAArtifact.artifact_type == artifact_type)
    
    artifacts = query.order_by(FPAArtifact.artifact_date.desc()).all()
    return {"artifacts": [a.to_dict() for a in artifacts]}


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: int,
    db: Session = Depends(get_db),
):
    """Get an artifact"""
    artifact = db.query(FPAArtifact).filter(FPAArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return artifact.to_dict()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _log_action(
    db: Session,
    entity_id: int,
    action: str,
    resource_type: str,
    resource_id: int,
    user_id: Optional[str] = None,
    details: Optional[Dict] = None,
):
    """Log an FPA action"""
    log = FPAAuditLog(
        entity_id=entity_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        details_json=details,
    )
    db.add(log)
    db.commit()


async def _compute_forecast(forecast_run_id: int):
    """Background task to compute forecast"""
    # This will be implemented in the compute engine
    from database import SessionLocal
    from fpa_compute_engine import FPAComputeEngine
    
    db = SessionLocal()
    try:
        engine = FPAComputeEngine(db)
        engine.run_forecast(forecast_run_id)
    finally:
        db.close()
