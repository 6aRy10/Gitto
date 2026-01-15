"""
External System Certification API

Endpoints for importing external TMS data and generating certification reports.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import json

from database import get_db
from external_certification_service import ExternalCertificationService
from external_certification_models import (
    ExternalSystemImport, CertificationReport, CertificationDiscrepancy,
    AccountComparison, CertificationStatus, DiscrepancyCategory
)


router = APIRouter(prefix="/external-certification", tags=["External Certification"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class ImportResponse(BaseModel):
    id: int
    snapshot_id: int
    system_name: str
    file_name: str
    external_as_of: datetime
    gitto_as_of: datetime
    row_count: int
    external_total_base: float
    message: str

    class Config:
        from_attributes = True


class DiscrepancyResponse(BaseModel):
    id: int
    category: str
    description: Optional[str]
    amount_base: float
    currency: Optional[str]
    evidence_refs: Optional[List[dict]]
    is_resolved: bool

    class Config:
        from_attributes = True


class AccountComparisonResponse(BaseModel):
    id: int
    external_account_id: Optional[str]
    external_account_name: Optional[str]
    external_amount_base: Optional[float]
    gitto_account_id: Optional[int]
    gitto_account_name: Optional[str]
    gitto_amount_base: Optional[float]
    difference_base: Optional[float]
    is_matched: bool
    primary_category: Optional[str]

    class Config:
        from_attributes = True


class CertificationReportResponse(BaseModel):
    id: int
    snapshot_id: int
    import_id: int
    created_at: datetime
    status: str
    
    external_total_base: float
    gitto_total_base: float
    gross_difference_base: float
    net_difference_base: float
    
    explained_by_unmatched: float
    explained_by_fx_policy: float
    explained_by_stale_data: float
    explained_by_mapping_gap: float
    explained_by_timing: float
    explained_by_rounding: float
    unexplained_amount: float
    
    certification_score: float
    is_certified: bool
    certified_at: Optional[datetime]
    certified_by: Optional[str]
    
    discrepancies: List[DiscrepancyResponse]
    account_comparisons: List[AccountComparisonResponse]

    class Config:
        from_attributes = True


class CertifyRequest(BaseModel):
    certified_by: str
    notes: Optional[str] = ""


class ResolveDiscrepancyRequest(BaseModel):
    resolution_notes: str
    resolved_by: str


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/import", response_model=ImportResponse)
async def import_tms_csv(
    file: UploadFile = File(...),
    snapshot_id: int = Form(...),
    system_name: str = Form(...),
    external_as_of: str = Form(...),
    imported_by: str = Form(default="api"),
    base_currency: str = Form(default="EUR"),
    db: Session = Depends(get_db)
):
    """
    Import cash position data from external TMS CSV file.
    
    Expected CSV columns (flexible naming):
    - account_id / account_no / account_number
    - account_name / name
    - bank_name / bank
    - currency / ccy
    - amount / balance / position
    - fx_rate (optional)
    - position_date / as_of_date (optional)
    """
    try:
        # Parse external_as_of datetime
        external_as_of_dt = datetime.fromisoformat(external_as_of.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid external_as_of datetime format")
    
    try:
        content = await file.read()
        
        service = ExternalCertificationService(db)
        import_record = service.import_tms_csv(
            snapshot_id=snapshot_id,
            file_content=content,
            file_name=file.filename or "unknown.csv",
            system_name=system_name,
            external_as_of=external_as_of_dt,
            imported_by=imported_by,
            base_currency=base_currency
        )
        
        return ImportResponse(
            id=import_record.id,
            snapshot_id=import_record.snapshot_id,
            system_name=import_record.system_name,
            file_name=import_record.file_name,
            external_as_of=import_record.external_as_of,
            gitto_as_of=import_record.gitto_as_of,
            row_count=import_record.row_count,
            external_total_base=import_record.external_total_base,
            message=f"Successfully imported {import_record.row_count} cash positions"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/imports", response_model=List[ImportResponse])
def list_imports(
    snapshot_id: Optional[int] = Query(None),
    system_name: Optional[str] = Query(None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """List external system imports."""
    query = db.query(ExternalSystemImport)
    
    if snapshot_id:
        query = query.filter(ExternalSystemImport.snapshot_id == snapshot_id)
    if system_name:
        query = query.filter(ExternalSystemImport.system_name.ilike(f"%{system_name}%"))
    
    imports = query.order_by(ExternalSystemImport.imported_at.desc()).limit(limit).all()
    
    return [
        ImportResponse(
            id=imp.id,
            snapshot_id=imp.snapshot_id,
            system_name=imp.system_name,
            file_name=imp.file_name,
            external_as_of=imp.external_as_of,
            gitto_as_of=imp.gitto_as_of,
            row_count=imp.row_count,
            external_total_base=imp.external_total_base,
            message=""
        )
        for imp in imports
    ]


@router.get("/imports/{import_id}")
def get_import(import_id: int, db: Session = Depends(get_db)):
    """Get details of a specific import."""
    import_record = db.query(ExternalSystemImport).filter(
        ExternalSystemImport.id == import_id
    ).first()
    
    if not import_record:
        raise HTTPException(status_code=404, detail="Import not found")
    
    from external_certification_models import ExternalCashPosition
    
    positions = db.query(ExternalCashPosition).filter(
        ExternalCashPosition.import_id == import_id
    ).all()
    
    return {
        "import": {
            "id": import_record.id,
            "snapshot_id": import_record.snapshot_id,
            "system_name": import_record.system_name,
            "file_name": import_record.file_name,
            "file_hash": import_record.file_hash,
            "imported_at": import_record.imported_at.isoformat(),
            "imported_by": import_record.imported_by,
            "external_as_of": import_record.external_as_of.isoformat(),
            "gitto_as_of": import_record.gitto_as_of.isoformat(),
            "row_count": import_record.row_count,
            "external_total_base": import_record.external_total_base,
        },
        "positions": [
            {
                "id": pos.id,
                "external_account_id": pos.external_account_id,
                "account_name": pos.account_name,
                "bank_name": pos.bank_name,
                "currency": pos.currency,
                "amount": pos.amount,
                "amount_base": pos.amount_base,
                "fx_rate_used": pos.fx_rate_used,
                "gitto_account_id": pos.gitto_account_id,
                "is_mapped": pos.is_mapped,
            }
            for pos in positions
        ]
    }


@router.post("/imports/{import_id}/generate-report", response_model=CertificationReportResponse)
def generate_certification_report(
    import_id: int,
    created_by: str = Query(default="api"),
    db: Session = Depends(get_db)
):
    """
    Generate a certification report comparing external TMS vs Gitto totals.
    
    The report will:
    - Compare external cash positions to Gitto bank-truth totals
    - Attribute differences to specific categories with evidence
    - Calculate a certification score
    """
    try:
        service = ExternalCertificationService(db)
        report = service.generate_certification_report(import_id, created_by)
        
        # Load related data
        discrepancies = db.query(CertificationDiscrepancy).filter(
            CertificationDiscrepancy.report_id == report.id
        ).all()
        
        comparisons = db.query(AccountComparison).filter(
            AccountComparison.report_id == report.id
        ).all()
        
        return CertificationReportResponse(
            id=report.id,
            snapshot_id=report.snapshot_id,
            import_id=report.import_id,
            created_at=report.created_at,
            status=report.status.value,
            external_total_base=report.external_total_base,
            gitto_total_base=report.gitto_total_base,
            gross_difference_base=report.gross_difference_base,
            net_difference_base=report.net_difference_base,
            explained_by_unmatched=report.explained_by_unmatched,
            explained_by_fx_policy=report.explained_by_fx_policy,
            explained_by_stale_data=report.explained_by_stale_data,
            explained_by_mapping_gap=report.explained_by_mapping_gap,
            explained_by_timing=report.explained_by_timing,
            explained_by_rounding=report.explained_by_rounding,
            unexplained_amount=report.unexplained_amount,
            certification_score=report.certification_score,
            is_certified=report.is_certified,
            certified_at=report.certified_at,
            certified_by=report.certified_by,
            discrepancies=[
                DiscrepancyResponse(
                    id=d.id,
                    category=d.category.value,
                    description=d.description,
                    amount_base=d.amount_base,
                    currency=d.currency,
                    evidence_refs=d.evidence_refs_json,
                    is_resolved=d.is_resolved
                )
                for d in discrepancies
            ],
            account_comparisons=[
                AccountComparisonResponse(
                    id=c.id,
                    external_account_id=c.external_account_id,
                    external_account_name=c.external_account_name,
                    external_amount_base=c.external_amount_base,
                    gitto_account_id=c.gitto_account_id,
                    gitto_account_name=c.gitto_account_name,
                    gitto_amount_base=c.gitto_amount_base,
                    difference_base=c.difference_base,
                    is_matched=c.is_matched,
                    primary_category=c.primary_discrepancy_category.value if c.primary_discrepancy_category else None
                )
                for c in comparisons
            ]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports", response_model=List[dict])
def list_reports(
    snapshot_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """List certification reports."""
    query = db.query(CertificationReport)
    
    if snapshot_id:
        query = query.filter(CertificationReport.snapshot_id == snapshot_id)
    if status:
        query = query.filter(CertificationReport.status == CertificationStatus(status))
    
    reports = query.order_by(CertificationReport.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "snapshot_id": r.snapshot_id,
            "import_id": r.import_id,
            "created_at": r.created_at.isoformat(),
            "status": r.status.value,
            "certification_score": r.certification_score,
            "is_certified": r.is_certified,
            "gross_difference_base": r.gross_difference_base,
            "unexplained_amount": r.unexplained_amount,
        }
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=CertificationReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a specific certification report with full details."""
    report = db.query(CertificationReport).filter(
        CertificationReport.id == report_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    discrepancies = db.query(CertificationDiscrepancy).filter(
        CertificationDiscrepancy.report_id == report_id
    ).all()
    
    comparisons = db.query(AccountComparison).filter(
        AccountComparison.report_id == report_id
    ).all()
    
    return CertificationReportResponse(
        id=report.id,
        snapshot_id=report.snapshot_id,
        import_id=report.import_id,
        created_at=report.created_at,
        status=report.status.value,
        external_total_base=report.external_total_base,
        gitto_total_base=report.gitto_total_base,
        gross_difference_base=report.gross_difference_base,
        net_difference_base=report.net_difference_base,
        explained_by_unmatched=report.explained_by_unmatched,
        explained_by_fx_policy=report.explained_by_fx_policy,
        explained_by_stale_data=report.explained_by_stale_data,
        explained_by_mapping_gap=report.explained_by_mapping_gap,
        explained_by_timing=report.explained_by_timing,
        explained_by_rounding=report.explained_by_rounding,
        unexplained_amount=report.unexplained_amount,
        certification_score=report.certification_score,
        is_certified=report.is_certified,
        certified_at=report.certified_at,
        certified_by=report.certified_by,
        discrepancies=[
            DiscrepancyResponse(
                id=d.id,
                category=d.category.value,
                description=d.description,
                amount_base=d.amount_base,
                currency=d.currency,
                evidence_refs=d.evidence_refs_json,
                is_resolved=d.is_resolved
            )
            for d in discrepancies
        ],
        account_comparisons=[
            AccountComparisonResponse(
                id=c.id,
                external_account_id=c.external_account_id,
                external_account_name=c.external_account_name,
                external_amount_base=c.external_amount_base,
                gitto_account_id=c.gitto_account_id,
                gitto_account_name=c.gitto_account_name,
                gitto_amount_base=c.gitto_amount_base,
                difference_base=c.difference_base,
                is_matched=c.is_matched,
                primary_category=c.primary_discrepancy_category.value if c.primary_discrepancy_category else None
            )
            for c in comparisons
        ]
    )


@router.post("/reports/{report_id}/certify")
def certify_report(
    report_id: int,
    request: CertifyRequest,
    db: Session = Depends(get_db)
):
    """Mark a report as certified."""
    try:
        service = ExternalCertificationService(db)
        report = service.certify_report(
            report_id=report_id,
            certified_by=request.certified_by,
            notes=request.notes or ""
        )
        
        return {
            "id": report.id,
            "is_certified": report.is_certified,
            "certified_at": report.certified_at.isoformat() if report.certified_at else None,
            "certified_by": report.certified_by,
            "status": report.status.value,
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reports/{report_id}/export")
def export_report(
    report_id: int,
    format: str = Query(default="json", regex="^(json|xlsx|pdf)$"),
    db: Session = Depends(get_db)
):
    """
    Export certification report.
    
    Formats:
    - json: Full JSON export
    - xlsx: Excel spreadsheet (future)
    - pdf: PDF document (future)
    """
    try:
        service = ExternalCertificationService(db)
        export_data = service.export_report(report_id, format)
        
        return export_data
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reports/{report_id}/discrepancies/{discrepancy_id}/resolve")
def resolve_discrepancy(
    report_id: int,
    discrepancy_id: int,
    request: ResolveDiscrepancyRequest,
    db: Session = Depends(get_db)
):
    """Mark a discrepancy as resolved."""
    discrepancy = db.query(CertificationDiscrepancy).filter(
        CertificationDiscrepancy.id == discrepancy_id,
        CertificationDiscrepancy.report_id == report_id
    ).first()
    
    if not discrepancy:
        raise HTTPException(status_code=404, detail="Discrepancy not found")
    
    discrepancy.is_resolved = True
    discrepancy.resolution_notes = request.resolution_notes
    discrepancy.resolved_by = request.resolved_by
    discrepancy.resolved_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "id": discrepancy.id,
        "is_resolved": discrepancy.is_resolved,
        "resolved_at": discrepancy.resolved_at.isoformat(),
        "resolved_by": discrepancy.resolved_by,
    }


@router.get("/reports/{report_id}/discrepancies/{discrepancy_id}/evidence")
def get_discrepancy_evidence(
    report_id: int,
    discrepancy_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed evidence for a specific discrepancy."""
    discrepancy = db.query(CertificationDiscrepancy).filter(
        CertificationDiscrepancy.id == discrepancy_id,
        CertificationDiscrepancy.report_id == report_id
    ).first()
    
    if not discrepancy:
        raise HTTPException(status_code=404, detail="Discrepancy not found")
    
    return {
        "id": discrepancy.id,
        "category": discrepancy.category.value,
        "description": discrepancy.description,
        "amount_base": discrepancy.amount_base,
        "evidence": discrepancy.evidence_refs_json or [],
    }


@router.get("/snapshots/{snapshot_id}/certification-status")
def get_snapshot_certification_status(
    snapshot_id: int,
    db: Session = Depends(get_db)
):
    """Get certification status for a snapshot."""
    # Get latest report for snapshot
    report = db.query(CertificationReport).filter(
        CertificationReport.snapshot_id == snapshot_id
    ).order_by(CertificationReport.created_at.desc()).first()
    
    # Get all imports for snapshot
    imports = db.query(ExternalSystemImport).filter(
        ExternalSystemImport.snapshot_id == snapshot_id
    ).all()
    
    return {
        "snapshot_id": snapshot_id,
        "has_certification": report is not None,
        "is_certified": report.is_certified if report else False,
        "certification_score": report.certification_score if report else None,
        "latest_report_id": report.id if report else None,
        "import_count": len(imports),
        "latest_import": {
            "id": imports[0].id,
            "system_name": imports[0].system_name,
            "imported_at": imports[0].imported_at.isoformat(),
        } if imports else None,
    }
