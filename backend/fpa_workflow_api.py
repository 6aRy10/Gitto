"""
FP&A Workflow API Endpoints

API for running workflows, managing decisions, and generating reports.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from fpa_models import FPAArtifact, FPADecision, VarianceReport
from fpa_workflows import (
    FPAWorkflowOrchestrator,
    MorningBriefingOutput,
    WeeklyForecastOutput,
    MonthEndCloseOutput,
)
from fpa_decision_queue import FPADecisionQueue, DecisionOption
from fpa_narrative_generator import FPANarrativeGenerator
from fpa_evaluation import FPAEvaluationHarness, FPATrustReport

router = APIRouter(prefix="/fpa/workflows", tags=["FP&A Workflows"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class RunMorningBriefingRequest(BaseModel):
    entity_id: int
    briefing_date: Optional[date] = None
    generate_narrative: bool = True


class RunWeeklyForecastRequest(BaseModel):
    entity_id: int
    plan_id: int
    week_ending: Optional[date] = None
    generate_narrative: bool = True


class RunMonthEndCloseRequest(BaseModel):
    entity_id: int
    period_month: date


class ProcessDecisionRequest(BaseModel):
    user_id: str
    user_role: str
    option_selected: str
    note: Optional[str] = None


class DismissDecisionRequest(BaseModel):
    user_id: str
    reason: str


class GenerateNarrativeRequest(BaseModel):
    artifact_id: int


class TrustReportRequest(BaseModel):
    entity_id: int
    plan_id: Optional[int] = None


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================

@router.post("/morning-briefing")
async def run_morning_briefing(
    request: RunMorningBriefingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Run morning briefing workflow.
    
    Generates a cash position overview and attention items for the day.
    """
    orchestrator = FPAWorkflowOrchestrator(db)
    
    output = orchestrator.run_morning_briefing(
        entity_id=request.entity_id,
        briefing_date=request.briefing_date,
    )
    
    # Generate narrative in background if requested
    if request.generate_narrative:
        # Find the artifact that was just created
        artifact = db.query(FPAArtifact).filter(
            FPAArtifact.entity_id == request.entity_id,
            FPAArtifact.artifact_type == "morning_briefing",
            FPAArtifact.artifact_date == output.briefing_date,
        ).order_by(FPAArtifact.created_at.desc()).first()
        
        if artifact:
            background_tasks.add_task(
                _generate_narrative_async,
                db,
                artifact.id,
                "morning_briefing",
            )
    
    return {
        "status": "success",
        "output": output.to_dict(),
    }


@router.post("/weekly-forecast")
async def run_weekly_forecast(
    request: RunWeeklyForecastRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Run weekly forecast update workflow.
    
    Computes new forecast, compares to prior week, generates talking points.
    """
    orchestrator = FPAWorkflowOrchestrator(db)
    
    output = orchestrator.run_weekly_forecast_update(
        entity_id=request.entity_id,
        plan_id=request.plan_id,
        week_ending=request.week_ending,
    )
    
    if request.generate_narrative:
        artifact = db.query(FPAArtifact).filter(
            FPAArtifact.entity_id == request.entity_id,
            FPAArtifact.artifact_type == "weekly_forecast",
            FPAArtifact.artifact_date == output.week_ending,
        ).order_by(FPAArtifact.created_at.desc()).first()
        
        if artifact:
            background_tasks.add_task(
                _generate_narrative_async,
                db,
                artifact.id,
                "weekly_forecast",
            )
    
    return {
        "status": "success",
        "output": output.to_dict(),
    }


@router.post("/month-end-close")
async def run_month_end_close(
    request: RunMonthEndCloseRequest,
    db: Session = Depends(get_db),
):
    """
    Run month-end close workflow.
    
    Checks data completeness, reconciliation status, and variance analysis.
    """
    orchestrator = FPAWorkflowOrchestrator(db)
    
    output = orchestrator.run_month_end_close(
        entity_id=request.entity_id,
        period_month=request.period_month,
    )
    
    return {
        "status": "success",
        "output": output.to_dict(),
    }


@router.get("/monitoring/{entity_id}")
async def run_continuous_monitoring(
    entity_id: int,
    db: Session = Depends(get_db),
):
    """
    Run continuous monitoring checks.
    
    Returns current alerts and issues.
    """
    orchestrator = FPAWorkflowOrchestrator(db)
    
    alerts = orchestrator.run_continuous_monitoring(entity_id)
    
    return {
        "status": "success",
        "alerts": alerts,
        "alert_count": len(alerts),
    }


# =============================================================================
# DECISION QUEUE ENDPOINTS
# =============================================================================

@router.get("/decisions/{entity_id}")
async def get_pending_decisions(
    entity_id: int,
    decision_type: Optional[str] = None,
    user_role: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get pending decisions for an entity"""
    queue = FPADecisionQueue(db)
    
    decisions = queue.get_pending_decisions(
        entity_id=entity_id,
        decision_type=decision_type,
        user_role=user_role,
    )
    
    return {
        "decisions": [d.to_dict() for d in decisions],
        "count": len(decisions),
    }


@router.get("/decisions/{entity_id}/expiring")
async def get_expiring_decisions(
    entity_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Get decisions expiring within specified hours"""
    queue = FPADecisionQueue(db)
    
    decisions = queue.get_expiring_decisions(
        entity_id=entity_id,
        hours=hours,
    )
    
    return {
        "decisions": [d.to_dict() for d in decisions],
        "count": len(decisions),
        "expiry_window_hours": hours,
    }


@router.post("/decisions/{decision_id}/approve")
async def approve_decision(
    decision_id: int,
    request: ProcessDecisionRequest,
    db: Session = Depends(get_db),
):
    """Process an approval for a decision"""
    queue = FPADecisionQueue(db)
    
    try:
        decision = queue.process_approval(
            decision_id=decision_id,
            user_id=request.user_id,
            user_role=request.user_role,
            option_selected=request.option_selected,
            note=request.note,
        )
        
        return {
            "status": "success",
            "decision": decision.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decisions/{decision_id}/dismiss")
async def dismiss_decision(
    decision_id: int,
    request: DismissDecisionRequest,
    db: Session = Depends(get_db),
):
    """Dismiss a decision"""
    queue = FPADecisionQueue(db)
    
    try:
        decision = queue.dismiss_decision(
            decision_id=decision_id,
            user_id=request.user_id,
            reason=request.reason,
        )
        
        return {
            "status": "success",
            "decision": decision.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# NARRATIVE ENDPOINTS
# =============================================================================

@router.post("/narrative/generate")
async def generate_narrative(
    request: GenerateNarrativeRequest,
    db: Session = Depends(get_db),
):
    """Generate narrative for an artifact"""
    generator = FPANarrativeGenerator(db)
    
    artifact = db.query(FPAArtifact).filter(
        FPAArtifact.id == request.artifact_id
    ).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Generate based on type
    if artifact.artifact_type == "morning_briefing":
        narrative = generator.generate_morning_briefing_narrative(artifact)
    elif artifact.artifact_type == "weekly_forecast":
        narrative = generator.generate_weekly_forecast_narrative(artifact)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported artifact type: {artifact.artifact_type}")
    
    # Save to artifact
    generator.save_narrative_to_artifact(artifact.id, narrative)
    
    return {
        "status": "success",
        "narrative": narrative.to_dict(),
    }


@router.get("/artifacts/{entity_id}")
async def get_artifacts(
    entity_id: int,
    artifact_type: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get artifacts for an entity"""
    query = db.query(FPAArtifact).filter(FPAArtifact.entity_id == entity_id)
    
    if artifact_type:
        query = query.filter(FPAArtifact.artifact_type == artifact_type)
    
    artifacts = query.order_by(FPAArtifact.created_at.desc()).limit(limit).all()
    
    return {
        "artifacts": [a.to_dict() for a in artifacts],
        "count": len(artifacts),
    }


@router.get("/artifacts/detail/{artifact_id}")
async def get_artifact(
    artifact_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific artifact"""
    artifact = db.query(FPAArtifact).filter(FPAArtifact.id == artifact_id).first()
    
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return artifact.to_dict()


# =============================================================================
# TRUST REPORT ENDPOINTS
# =============================================================================

@router.post("/trust-report")
async def generate_trust_report(
    request: TrustReportRequest,
    db: Session = Depends(get_db),
):
    """Generate trust report for entity"""
    harness = FPAEvaluationHarness(db)
    
    report = harness.generate_trust_report(
        entity_id=request.entity_id,
        plan_id=request.plan_id,
    )
    
    return {
        "status": "success",
        "report": report.to_dict(),
    }


@router.get("/trust-report/{entity_id}")
async def get_latest_trust_report(
    entity_id: int,
    plan_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get latest trust report (generates if none exists)"""
    harness = FPAEvaluationHarness(db)
    
    report = harness.generate_trust_report(
        entity_id=entity_id,
        plan_id=plan_id,
    )
    
    return report.to_dict()


@router.get("/invariants/{entity_id}")
async def check_invariants(
    entity_id: int,
    plan_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Run invariant checks"""
    harness = FPAEvaluationHarness(db)
    
    results = harness.check_all_invariants(
        entity_id=entity_id,
        plan_id=plan_id,
    )
    
    passed_count = sum(1 for r in results if r.passed)
    
    return {
        "results": [r.to_dict() for r in results],
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _generate_narrative_async(
    db: Session,
    artifact_id: int,
    artifact_type: str,
):
    """Background task to generate narrative"""
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        generator = FPANarrativeGenerator(db)
        artifact = db.query(FPAArtifact).filter(FPAArtifact.id == artifact_id).first()
        
        if not artifact:
            return
        
        if artifact_type == "morning_briefing":
            narrative = generator.generate_morning_briefing_narrative(artifact)
        elif artifact_type == "weekly_forecast":
            narrative = generator.generate_weekly_forecast_narrative(artifact)
        else:
            return
        
        generator.save_narrative_to_artifact(artifact_id, narrative)
    finally:
        db.close()
