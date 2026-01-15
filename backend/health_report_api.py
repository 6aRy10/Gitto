"""
Health Report API Endpoints

Provides:
- GET /datasets/{id}/health - Get health report for dataset
- GET /connections/{id}/health/latest - Get latest health report for connection
- POST /datasets/{id}/health/generate - Generate new health report
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db
from health_report_service import HealthReportService
from health_report_models import DataHealthReportRecord, HealthFinding


router = APIRouter(tags=["Health Reports"])


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def finding_response(finding: HealthFinding) -> Dict[str, Any]:
    """Build finding response."""
    return {
        "id": finding.id,
        "category": finding.category,
        "severity": finding.severity,
        "metric_key": finding.metric_key,
        "metric_label": finding.metric_label,
        "metric_value": finding.metric_value,
        "exposure_amount_base": finding.exposure_amount_base,
        "exposure_currency": finding.exposure_currency,
        "count_rows": finding.count_rows,
        "sample_evidence": finding.sample_evidence_json or [],
        "threshold_value": finding.threshold_value,
        "threshold_type": finding.threshold_type
    }


def report_response(report: DataHealthReportRecord) -> Dict[str, Any]:
    """Build report response."""
    findings = report.findings if report.findings else []
    
    # Group findings by severity
    critical = [f for f in findings if f.severity == "critical"]
    warnings = [f for f in findings if f.severity == "warn"]
    info = [f for f in findings if f.severity == "info"]
    
    return {
        "id": report.id,
        "dataset_id": report.dataset_id,
        "connection_id": report.connection_id,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "severity_score": report.severity_score,
        "summary": report.summary_json or {},
        "schema_fingerprint": report.schema_fingerprint,
        "findings": {
            "critical": [finding_response(f) for f in critical],
            "warnings": [finding_response(f) for f in warnings],
            "info": [finding_response(f) for f in info],
            "total_count": len(findings)
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATASET HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/datasets/{dataset_id}/health")
def get_dataset_health(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """
    Get health report for a dataset.
    
    Returns the latest health report with all findings.
    If no report exists, generates one automatically.
    """
    service = HealthReportService(db)
    report = service.get_report(dataset_id)
    
    if not report:
        # Auto-generate if not exists
        try:
            report = service.generate_report(dataset_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    return report_response(report)


@router.post("/datasets/{dataset_id}/health/generate")
def generate_dataset_health(
    dataset_id: int,
    connection_id: Optional[int] = Query(None, description="Connection ID for schema drift comparison"),
    base_currency: str = Query("EUR", description="Base currency for exposure calculation"),
    db: Session = Depends(get_db)
):
    """
    Generate a new health report for a dataset.
    
    Creates a fresh health report with all findings.
    Previous reports are preserved for history.
    """
    service = HealthReportService(db, base_currency=base_currency)
    
    try:
        report = service.generate_report(dataset_id, connection_id)
        return report_response(report)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/datasets/{dataset_id}/health/findings")
def get_dataset_findings(
    dataset_id: int,
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warn, info"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Get health findings for a dataset.
    
    Returns detailed findings with filtering options.
    """
    service = HealthReportService(db)
    report = service.get_report(dataset_id)
    
    if not report:
        raise HTTPException(status_code=404, detail=f"No health report found for dataset {dataset_id}")
    
    findings = report.findings or []
    
    # Apply filters
    if severity:
        findings = [f for f in findings if f.severity == severity]
    if category:
        findings = [f for f in findings if f.category == category]
    
    return {
        "dataset_id": dataset_id,
        "report_id": report.id,
        "total_findings": len(findings),
        "findings": [finding_response(f) for f in findings]
    }


@router.get("/datasets/{dataset_id}/health/history")
def get_dataset_health_history(
    dataset_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get health report history for a dataset.
    
    Returns historical severity scores and summaries.
    """
    reports = db.query(DataHealthReportRecord).filter(
        DataHealthReportRecord.dataset_id == dataset_id
    ).order_by(DataHealthReportRecord.created_at.desc()).limit(limit).all()
    
    return {
        "dataset_id": dataset_id,
        "report_count": len(reports),
        "reports": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "severity_score": r.severity_score,
                "quality_level": (r.summary_json or {}).get("quality_level"),
                "critical_count": (r.summary_json or {}).get("critical_count", 0),
                "warning_count": (r.summary_json or {}).get("warning_count", 0)
            }
            for r in reports
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION HEALTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/connections/{connection_id}/health/latest")
def get_connection_latest_health(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """
    Get latest health report for a connection.
    
    Returns the most recent health report from any dataset
    synced through this connection.
    """
    service = HealthReportService(db)
    report = service.get_connection_latest_report(connection_id)
    
    if not report:
        raise HTTPException(
            status_code=404, 
            detail=f"No health report found for connection {connection_id}"
        )
    
    return report_response(report)


@router.get("/connections/{connection_id}/health/trend")
def get_connection_health_trend(
    connection_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get health trend for a connection over time.
    
    Returns severity scores and key metrics from recent reports.
    """
    reports = db.query(DataHealthReportRecord).filter(
        DataHealthReportRecord.connection_id == connection_id
    ).order_by(DataHealthReportRecord.created_at.desc()).limit(limit).all()
    
    if not reports:
        return {
            "connection_id": connection_id,
            "report_count": 0,
            "trend": [],
            "average_severity": None
        }
    
    # Calculate trend
    trend = [
        {
            "report_id": r.id,
            "dataset_id": r.dataset_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "severity_score": r.severity_score,
            "quality_level": (r.summary_json or {}).get("quality_level"),
            "total_rows": (r.summary_json or {}).get("total_rows", 0),
            "amount_with_issues": (r.summary_json or {}).get("amount_with_issues", 0)
        }
        for r in reports
    ]
    
    avg_severity = sum(r.severity_score for r in reports) / len(reports)
    
    return {
        "connection_id": connection_id,
        "report_count": len(reports),
        "trend": trend,
        "average_severity": avg_severity
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health/summary")
def get_overall_health_summary(
    entity_id: Optional[int] = Query(None, description="Filter by entity"),
    db: Session = Depends(get_db)
):
    """
    Get overall health summary across all datasets.
    
    Returns aggregate metrics and top issues.
    """
    from sqlalchemy import func
    from lineage_models import LineageDataset
    
    query = db.query(DataHealthReportRecord)
    
    if entity_id:
        # Join with datasets to filter by entity
        query = query.join(
            LineageDataset, 
            DataHealthReportRecord.dataset_id == LineageDataset.id
        ).filter(LineageDataset.entity_id == entity_id)
    
    # Get latest report per dataset
    subquery = db.query(
        DataHealthReportRecord.dataset_id,
        func.max(DataHealthReportRecord.created_at).label('max_created')
    ).group_by(DataHealthReportRecord.dataset_id).subquery()
    
    latest_reports = query.join(
        subquery,
        (DataHealthReportRecord.dataset_id == subquery.c.dataset_id) &
        (DataHealthReportRecord.created_at == subquery.c.max_created)
    ).all()
    
    if not latest_reports:
        return {
            "total_datasets": 0,
            "average_severity": 0,
            "quality_distribution": {},
            "top_issues": []
        }
    
    # Calculate aggregate metrics
    total = len(latest_reports)
    avg_severity = sum(r.severity_score for r in latest_reports) / total
    
    # Quality distribution
    quality_dist = {}
    for r in latest_reports:
        level = (r.summary_json or {}).get("quality_level", "unknown")
        quality_dist[level] = quality_dist.get(level, 0) + 1
    
    # Get top issues across all reports
    all_findings = db.query(HealthFinding).filter(
        HealthFinding.report_id.in_([r.id for r in latest_reports]),
        HealthFinding.severity.in_(["critical", "warn"])
    ).order_by(HealthFinding.exposure_amount_base.desc()).limit(10).all()
    
    return {
        "total_datasets": total,
        "average_severity": avg_severity,
        "quality_distribution": quality_dist,
        "top_issues": [
            {
                "metric_key": f.metric_key,
                "metric_label": f.metric_label,
                "severity": f.severity,
                "total_exposure": f.exposure_amount_base,
                "dataset_id": db.query(DataHealthReportRecord).filter(
                    DataHealthReportRecord.id == f.report_id
                ).first().dataset_id if f.report_id else None
            }
            for f in all_findings
        ]
    }
