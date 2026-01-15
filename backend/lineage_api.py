"""
Data Lineage API Endpoints

Provides REST API for:
- Connection management (CRUD, test, sync)
- Dataset retrieval
- Sync run monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db
from lineage_service import LineageService
from lineage_models import (
    LineageConnection, SyncRun, LineageDataset, CanonicalRecord,
    ConnectionStatus, SyncStatus
)
from connector_interface import ConnectorRegistry


router = APIRouter(prefix="/lineage", tags=["Data Lineage"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateConnectionRequest(BaseModel):
    """Request to create a connection."""
    entity_id: Optional[int] = None
    type: str = Field(..., description="Connection type (bank_stub, erp_stub, etc.)")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict, description="Non-sensitive configuration")
    secret_ref: Optional[str] = Field(None, description="Reference to secrets")


class ConnectionResponse(BaseModel):
    """Connection response."""
    id: int
    entity_id: Optional[int]
    type: str
    name: str
    description: Optional[str]
    status: str
    status_message: Optional[str]
    config: Optional[Dict[str, Any]]
    created_at: datetime
    last_test_at: Optional[datetime]
    last_sync_at: Optional[datetime]


class TestConnectionResponse(BaseModel):
    """Connection test response."""
    success: bool
    message: str
    latency_ms: Optional[float]
    details: Dict[str, Any]


class StartSyncRequest(BaseModel):
    """Request to start a sync."""
    triggered_by: str = "manual"
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    background: bool = True


class StartSyncResponse(BaseModel):
    """Sync start response."""
    sync_run_id: int
    status: str
    message: str


class SyncRunResponse(BaseModel):
    """Sync run response."""
    id: int
    connection_id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    rows_extracted: int
    rows_normalized: int
    rows_loaded: int
    rows_skipped: int
    rows_error: int
    warning_count: int
    triggered_by: Optional[str]


class DatasetResponse(BaseModel):
    """Dataset response."""
    id: int
    dataset_id: str
    entity_id: Optional[int]
    sync_run_id: Optional[int]
    source_type: str
    source_summary: Optional[Dict[str, Any]]
    schema_fingerprint: Optional[str]
    row_count: int
    amount_total_base: float
    currency: Optional[str]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    created_at: datetime


class CanonicalRecordResponse(BaseModel):
    """Canonical record response."""
    id: int
    dataset_id: int
    record_type: str
    canonical_id: str
    amount: Optional[float]
    currency: Optional[str]
    record_date: Optional[datetime]
    due_date: Optional[datetime]
    counterparty: Optional[str]
    external_id: Optional[str]
    payload: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/connector-types")
def list_connector_types():
    """List available connector types."""
    return {
        "connector_types": ConnectorRegistry.list_types(),
        "description": "Use these types when creating connections"
    }


@router.post("/connections", response_model=ConnectionResponse)
def create_connection(
    request: CreateConnectionRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new data source connection.
    
    Connection types:
    - bank_stub: Stub bank connector (for testing)
    - erp_stub: Stub ERP connector (for testing)
    - ap_stub: Stub AP connector (for testing)
    
    Real connectors (bank_plaid, erp_sap, etc.) will be registered later.
    """
    # Validate connector type
    if request.type not in ConnectorRegistry.list_types():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown connector type: {request.type}. Available types: {ConnectorRegistry.list_types()}"
        )
    
    service = LineageService(db)
    connection = service.create_connection(
        entity_id=request.entity_id,
        connection_type=request.type,
        name=request.name,
        config=request.config,
        secret_ref=request.secret_ref,
        description=request.description
    )
    
    return ConnectionResponse(
        id=connection.id,
        entity_id=connection.entity_id,
        type=connection.type,
        name=connection.name,
        description=connection.description,
        status=connection.status,
        status_message=connection.status_message,
        config=connection.config_json,
        created_at=connection.created_at,
        last_test_at=connection.last_test_at,
        last_sync_at=connection.last_sync_at
    )


@router.get("/connections", response_model=List[ConnectionResponse])
def list_connections(
    entity_id: Optional[int] = Query(None, description="Filter by entity"),
    db: Session = Depends(get_db)
):
    """List all connections, optionally filtered by entity."""
    service = LineageService(db)
    connections = service.list_connections(entity_id=entity_id)
    
    return [
        ConnectionResponse(
            id=c.id,
            entity_id=c.entity_id,
            type=c.type,
            name=c.name,
            description=c.description,
            status=c.status,
            status_message=c.status_message,
            config=c.config_json,
            created_at=c.created_at,
            last_test_at=c.last_test_at,
            last_sync_at=c.last_sync_at
        )
        for c in connections
    ]


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """Get a connection by ID."""
    service = LineageService(db)
    connection = service.get_connection(connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail=f"Connection {connection_id} not found")
    
    return ConnectionResponse(
        id=connection.id,
        entity_id=connection.entity_id,
        type=connection.type,
        name=connection.name,
        description=connection.description,
        status=connection.status,
        status_message=connection.status_message,
        config=connection.config_json,
        created_at=connection.created_at,
        last_test_at=connection.last_test_at,
        last_sync_at=connection.last_sync_at
    )


@router.post("/connections/{connection_id}/test", response_model=TestConnectionResponse)
def test_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """
    Test a connection.
    
    Verifies credentials and connectivity to the data source.
    Updates connection status based on test result.
    """
    service = LineageService(db)
    result = service.test_connection(connection_id)
    
    return TestConnectionResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
        details=result.details
    )


@router.post("/connections/{connection_id}/sync", response_model=StartSyncResponse)
def start_sync(
    connection_id: int,
    request: StartSyncRequest = Body(default=StartSyncRequest()),
    db: Session = Depends(get_db)
):
    """
    Start a sync operation.
    
    By default runs in the background and returns immediately.
    Use GET /connections/{id}/runs to monitor progress.
    """
    service = LineageService(db)
    
    sync_run_id, error = service.start_sync(
        connection_id=connection_id,
        triggered_by=request.triggered_by,
        since=request.since,
        until=request.until,
        background=request.background
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return StartSyncResponse(
        sync_run_id=sync_run_id,
        status="pending" if request.background else "running",
        message=f"Sync started. Monitor progress at GET /lineage/sync-runs/{sync_run_id}"
    )


@router.get("/connections/{connection_id}/runs", response_model=List[SyncRunResponse])
def get_connection_runs(
    connection_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get sync runs for a connection."""
    service = LineageService(db)
    runs = service.get_sync_runs(connection_id, limit=limit)
    
    return [
        SyncRunResponse(
            id=r.id,
            connection_id=r.connection_id,
            started_at=r.started_at,
            finished_at=r.finished_at,
            status=r.status,
            rows_extracted=r.rows_extracted,
            rows_normalized=r.rows_normalized,
            rows_loaded=r.rows_loaded,
            rows_skipped=r.rows_skipped,
            rows_error=r.rows_error,
            warning_count=r.warning_count,
            triggered_by=r.triggered_by
        )
        for r in runs
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# SYNC RUN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/sync-runs/{sync_run_id}", response_model=SyncRunResponse)
def get_sync_run(
    sync_run_id: int,
    db: Session = Depends(get_db)
):
    """Get a sync run by ID."""
    service = LineageService(db)
    run = service.get_sync_run(sync_run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail=f"Sync run {sync_run_id} not found")
    
    return SyncRunResponse(
        id=run.id,
        connection_id=run.connection_id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        rows_extracted=run.rows_extracted,
        rows_normalized=run.rows_normalized,
        rows_loaded=run.rows_loaded,
        rows_skipped=run.rows_skipped,
        rows_error=run.rows_error,
        warning_count=run.warning_count,
        triggered_by=run.triggered_by
    )


@router.get("/sync-runs/{sync_run_id}/errors")
def get_sync_run_errors(
    sync_run_id: int,
    db: Session = Depends(get_db)
):
    """Get errors from a sync run."""
    service = LineageService(db)
    run = service.get_sync_run(sync_run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail=f"Sync run {sync_run_id} not found")
    
    return {
        "sync_run_id": sync_run_id,
        "error_count": run.rows_error,
        "errors": run.errors_json or [],
        "warning_count": run.warning_count,
        "warnings": run.warnings_json or []
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DATASET ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Get a dataset by ID."""
    service = LineageService(db)
    dataset = service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    return DatasetResponse(
        id=dataset.id,
        dataset_id=dataset.dataset_id,
        entity_id=dataset.entity_id,
        sync_run_id=dataset.sync_run_id,
        source_type=dataset.source_type,
        source_summary=dataset.source_summary_json,
        schema_fingerprint=dataset.schema_fingerprint,
        row_count=dataset.row_count,
        amount_total_base=dataset.amount_total_base or 0.0,
        currency=dataset.currency,
        date_range_start=dataset.date_range_start,
        date_range_end=dataset.date_range_end,
        created_at=dataset.created_at
    )


@router.get("/datasets/by-uuid/{dataset_uuid}", response_model=DatasetResponse)
def get_dataset_by_uuid(
    dataset_uuid: str,
    db: Session = Depends(get_db)
):
    """Get a dataset by UUID."""
    service = LineageService(db)
    dataset = service.get_dataset_by_uuid(dataset_uuid)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_uuid} not found")
    
    return DatasetResponse(
        id=dataset.id,
        dataset_id=dataset.dataset_id,
        entity_id=dataset.entity_id,
        sync_run_id=dataset.sync_run_id,
        source_type=dataset.source_type,
        source_summary=dataset.source_summary_json,
        schema_fingerprint=dataset.schema_fingerprint,
        row_count=dataset.row_count,
        amount_total_base=dataset.amount_total_base or 0.0,
        currency=dataset.currency,
        date_range_start=dataset.date_range_start,
        date_range_end=dataset.date_range_end,
        created_at=dataset.created_at
    )


@router.get("/datasets/{dataset_id}/records", response_model=List[CanonicalRecordResponse])
def get_dataset_records(
    dataset_id: int,
    record_type: Optional[str] = Query(None, description="Filter by record type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get canonical records from a dataset."""
    service = LineageService(db)
    
    # Verify dataset exists
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    records = service.get_canonical_records(
        dataset_id=dataset_id,
        record_type=record_type,
        limit=limit,
        offset=offset
    )
    
    return [
        CanonicalRecordResponse(
            id=r.id,
            dataset_id=r.dataset_id,
            record_type=r.record_type,
            canonical_id=r.canonical_id,
            amount=r.amount,
            currency=r.currency,
            record_date=r.record_date,
            due_date=r.due_date,
            counterparty=r.counterparty,
            external_id=r.external_id,
            payload=r.payload_json or {}
        )
        for r in records
    ]


@router.get("/datasets/{dataset_id}/schema")
def get_dataset_schema(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """Get schema information for a dataset."""
    service = LineageService(db)
    dataset = service.get_dataset(dataset_id)
    
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    return {
        "dataset_id": dataset_id,
        "schema_fingerprint": dataset.schema_fingerprint,
        "columns": dataset.schema_columns_json or [],
        "source_type": dataset.source_type
    }


@router.get("/datasets/{dataset_id}/raw-records")
def get_dataset_raw_records(
    dataset_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get raw records from a dataset (for debugging)."""
    service = LineageService(db)
    
    # Verify dataset exists
    dataset = service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    
    records = service.get_raw_records(
        dataset_id=dataset_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "dataset_id": dataset_id,
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "source_table": r.source_table,
                "source_row_id": r.source_row_id,
                "raw_hash": r.raw_hash,
                "is_processed": bool(r.is_processed),
                "processing_error": r.processing_error,
                "extracted_at": r.extracted_at.isoformat() if r.extracted_at else None,
                "raw_payload": r.raw_payload_json
            }
            for r in records
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA DRIFT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/connections/{connection_id}/schema-drift")
def get_schema_drift_events(
    connection_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get schema drift events for a connection."""
    from lineage_models import SchemaDriftEvent
    
    events = db.query(SchemaDriftEvent).filter(
        SchemaDriftEvent.connection_id == connection_id
    ).order_by(SchemaDriftEvent.detected_at.desc()).limit(limit).all()
    
    return {
        "connection_id": connection_id,
        "drift_events": [
            {
                "id": e.id,
                "old_dataset_id": e.old_dataset_id,
                "new_dataset_id": e.new_dataset_id,
                "old_fingerprint": e.old_fingerprint,
                "new_fingerprint": e.new_fingerprint,
                "added_columns": e.added_columns_json,
                "removed_columns": e.removed_columns_json,
                "type_changes": e.type_changes_json,
                "severity": e.severity,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
                "acknowledged_at": e.acknowledged_at.isoformat() if e.acknowledged_at else None,
                "acknowledged_by": e.acknowledged_by
            }
            for e in events
        ]
    }
