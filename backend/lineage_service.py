"""
Data Lineage Service

Orchestrates sync operations and manages data lineage:
- Creates SyncRuns and Datasets
- Extracts, normalizes, and loads data
- Detects schema drift
- Ensures idempotency
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import threading
import uuid

from lineage_models import (
    LineageConnection, SyncRun, LineageDataset, RawRecord, CanonicalRecord,
    LineageEvidenceRef, SchemaDriftEvent,
    ConnectionStatus, SyncStatus, RecordType, generate_dataset_id
)
from connector_interface import (
    BaseConnector, ConnectorRegistry, ExtractedRow, SchemaInfo,
    SyncResult, SyncProgress, ConnectionTestResult
)


# ═══════════════════════════════════════════════════════════════════════════════
# LINEAGE SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class LineageService:
    """
    Manages data lineage and sync operations.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._running_syncs: Dict[int, threading.Thread] = {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_connection(
        self,
        entity_id: Optional[int],
        connection_type: str,
        name: str,
        config: Dict[str, Any],
        secret_ref: Optional[str] = None,
        description: Optional[str] = None
    ) -> LineageConnection:
        """
        Create a new connection.
        
        Args:
            entity_id: Entity this connection belongs to
            connection_type: Type of connector (bank_plaid, erp_sap, etc.)
            name: Human-readable name
            config: Non-sensitive configuration
            secret_ref: Reference to secrets
            description: Optional description
        
        Returns:
            Created LineageConnection
        """
        connection = LineageConnection(
            entity_id=entity_id,
            type=connection_type,
            name=name,
            description=description,
            config_json=config,
            secret_ref=secret_ref,
            status=ConnectionStatus.PENDING_SETUP.value
        )
        
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        
        return connection
    
    def get_connection(self, connection_id: int) -> Optional[LineageConnection]:
        """Get connection by ID."""
        return self.db.query(LineageConnection).filter(
            LineageConnection.id == connection_id
        ).first()
    
    def list_connections(self, entity_id: Optional[int] = None) -> List[LineageConnection]:
        """List connections, optionally filtered by entity."""
        query = self.db.query(LineageConnection)
        if entity_id is not None:
            query = query.filter(LineageConnection.entity_id == entity_id)
        return query.all()
    
    def test_connection(self, connection_id: int) -> ConnectionTestResult:
        """
        Test a connection.
        
        Args:
            connection_id: Connection to test
        
        Returns:
            ConnectionTestResult with success status
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return ConnectionTestResult(
                success=False,
                message=f"Connection {connection_id} not found"
            )
        
        # Get connector
        connector = ConnectorRegistry.create(
            connection.type,
            connection.config_json or {},
            connection.secret_ref
        )
        
        if not connector:
            connection.status = ConnectionStatus.ERROR.value
            connection.status_message = f"Unknown connector type: {connection.type}"
            self.db.commit()
            return ConnectionTestResult(
                success=False,
                message=f"Unknown connector type: {connection.type}"
            )
        
        # Run test
        result = connector.test_connection()
        
        # Update connection status
        connection.last_test_at = datetime.now(timezone.utc)
        if result.success:
            connection.status = ConnectionStatus.ACTIVE.value
            connection.status_message = result.message
        else:
            connection.status = ConnectionStatus.ERROR.value
            connection.status_message = result.message
        
        self.db.commit()
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYNC OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_sync(
        self,
        connection_id: int,
        triggered_by: str = "manual",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        background: bool = True
    ) -> Tuple[int, Optional[str]]:
        """
        Start a sync operation.
        
        Args:
            connection_id: Connection to sync
            triggered_by: Who/what triggered the sync
            since: Sync records modified after this time
            until: Sync records modified before this time
            background: Run in background thread
        
        Returns:
            Tuple of (sync_run_id, error_message if any)
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return (0, f"Connection {connection_id} not found")
        
        # Check if already running
        if connection_id in self._running_syncs and self._running_syncs[connection_id].is_alive():
            return (0, "Sync already in progress for this connection")
        
        # Create sync run
        sync_run = SyncRun(
            connection_id=connection_id,
            status=SyncStatus.PENDING.value,
            triggered_by=triggered_by
        )
        self.db.add(sync_run)
        self.db.commit()
        self.db.refresh(sync_run)
        
        if background:
            # Run in background
            thread = threading.Thread(
                target=self._execute_sync,
                args=(sync_run.id, connection_id, since, until)
            )
            self._running_syncs[connection_id] = thread
            thread.start()
        else:
            # Run synchronously
            self._execute_sync(sync_run.id, connection_id, since, until)
        
        return (sync_run.id, None)
    
    def _execute_sync(
        self,
        sync_run_id: int,
        connection_id: int,
        since: Optional[datetime],
        until: Optional[datetime]
    ):
        """Execute sync operation (called in background thread or synchronously)."""
        # Note: Need new session for background thread
        from database import SessionLocal
        db = SessionLocal()
        
        try:
            sync_run = db.query(SyncRun).filter(SyncRun.id == sync_run_id).first()
            connection = db.query(LineageConnection).filter(LineageConnection.id == connection_id).first()
            
            if not sync_run or not connection:
                return
            
            # Update status to running
            sync_run.status = SyncStatus.RUNNING.value
            sync_run.started_at = datetime.now(timezone.utc)
            db.commit()
            
            # Get connector
            connector = ConnectorRegistry.create(
                connection.type,
                connection.config_json or {},
                connection.secret_ref
            )
            
            if not connector:
                sync_run.status = SyncStatus.FAILED.value
                sync_run.finished_at = datetime.now(timezone.utc)
                sync_run.errors_json = [{"error": f"Unknown connector type: {connection.type}"}]
                db.commit()
                return
            
            # Get schema for drift detection
            schema_info = connector.get_schema()
            
            # Create dataset
            dataset = LineageDataset(
                entity_id=connection.entity_id,
                sync_run_id=sync_run.id,
                source_type=connector.source_type,
                source_summary_json={
                    "connection_id": connection_id,
                    "connection_type": connection.type,
                    "since": since.isoformat() if since else None,
                    "until": until.isoformat() if until else None
                },
                schema_fingerprint=schema_info.fingerprint,
                schema_columns_json=schema_info.columns
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            
            # Check for schema drift
            self._check_schema_drift(db, connection_id, dataset, schema_info)
            
            # Extract and load data
            result = self._extract_and_load(
                db, connector, dataset, sync_run, since, until
            )
            
            # Update sync run
            sync_run.finished_at = datetime.now(timezone.utc)
            sync_run.status = SyncStatus.SUCCESS.value if result.success else (
                SyncStatus.PARTIAL.value if result.rows_loaded > 0 else SyncStatus.FAILED.value
            )
            sync_run.rows_extracted = result.rows_extracted
            sync_run.rows_normalized = result.rows_normalized
            sync_run.rows_loaded = result.rows_loaded
            sync_run.rows_skipped = result.rows_skipped
            sync_run.rows_error = result.rows_error
            sync_run.errors_json = result.errors if result.errors else None
            sync_run.warning_count = len(result.warnings)
            sync_run.warnings_json = result.warnings if result.warnings else None
            
            # Update dataset metrics
            dataset.row_count = result.rows_loaded
            if result.date_range_start:
                dataset.date_range_start = result.date_range_start
            if result.date_range_end:
                dataset.date_range_end = result.date_range_end
            
            # Calculate total amount
            total_amount = db.query(CanonicalRecord).filter(
                CanonicalRecord.dataset_id == dataset.id
            ).with_entities(
                db.query(CanonicalRecord.amount).filter(
                    CanonicalRecord.dataset_id == dataset.id
                ).scalar_subquery()
            ).scalar() or 0.0
            dataset.amount_total_base = total_amount
            
            # Update connection last_sync_at
            connection.last_sync_at = datetime.now(timezone.utc)
            
            db.commit()
            
        except Exception as e:
            # Handle unexpected errors
            try:
                sync_run = db.query(SyncRun).filter(SyncRun.id == sync_run_id).first()
                if sync_run:
                    sync_run.status = SyncStatus.FAILED.value
                    sync_run.finished_at = datetime.now(timezone.utc)
                    sync_run.errors_json = [{"error": str(e), "type": type(e).__name__}]
                    db.commit()
            except:
                pass
        finally:
            db.close()
            # Clean up running sync tracker
            if connection_id in self._running_syncs:
                del self._running_syncs[connection_id]
    
    def _extract_and_load(
        self,
        db: Session,
        connector: BaseConnector,
        dataset: LineageDataset,
        sync_run: SyncRun,
        since: Optional[datetime],
        until: Optional[datetime]
    ) -> SyncResult:
        """Extract data from connector and load into database."""
        rows_extracted = 0
        rows_normalized = 0
        rows_loaded = 0
        rows_skipped = 0
        rows_error = 0
        errors = []
        warnings = []
        min_date = None
        max_date = None
        
        try:
            for raw_row in connector.extract(since=since, until=until):
                rows_extracted += 1
                
                try:
                    # Store raw record
                    raw_record = RawRecord(
                        dataset_id=dataset.id,
                        source_table=raw_row.source_table,
                        source_row_id=raw_row.source_row_id,
                        raw_payload_json=raw_row.raw_payload,
                        raw_hash=raw_row.raw_hash
                    )
                    db.add(raw_record)
                    db.flush()  # Get ID
                    
                    # Normalize
                    normalized = connector.normalize(raw_row)
                    rows_normalized += 1
                    
                    # Track date range
                    record_date_str = normalized.get("record_date")
                    if record_date_str:
                        try:
                            if isinstance(record_date_str, str):
                                record_date = datetime.fromisoformat(record_date_str.replace("Z", "+00:00"))
                            else:
                                record_date = record_date_str
                            if min_date is None or record_date < min_date:
                                min_date = record_date
                            if max_date is None or record_date > max_date:
                                max_date = record_date
                        except:
                            pass
                    
                    # Create canonical record
                    canonical_record = CanonicalRecord(
                        dataset_id=dataset.id,
                        raw_record_id=raw_record.id,
                        record_type=normalized["record_type"],
                        canonical_id=normalized["canonical_id"],
                        payload_json=normalized.get("payload", {}),
                        amount=normalized.get("amount"),
                        currency=normalized.get("currency"),
                        record_date=datetime.fromisoformat(normalized["record_date"]) if normalized.get("record_date") and isinstance(normalized["record_date"], str) else normalized.get("record_date"),
                        due_date=datetime.fromisoformat(normalized["due_date"]) if normalized.get("due_date") and isinstance(normalized["due_date"], str) else normalized.get("due_date"),
                        counterparty=normalized.get("counterparty"),
                        external_id=normalized.get("external_id")
                    )
                    
                    try:
                        db.add(canonical_record)
                        db.flush()
                        rows_loaded += 1
                        raw_record.is_processed = 1
                    except IntegrityError:
                        # Duplicate canonical_id - idempotency working!
                        db.rollback()
                        rows_skipped += 1
                        warnings.append({
                            "row_idx": rows_extracted,
                            "warning_type": "duplicate",
                            "message": f"Duplicate canonical_id: {normalized['canonical_id'][:20]}...",
                            "canonical_id": normalized["canonical_id"]
                        })
                        # Re-add raw record without canonical
                        raw_record = RawRecord(
                            dataset_id=dataset.id,
                            source_table=raw_row.source_table,
                            source_row_id=raw_row.source_row_id,
                            raw_payload_json=raw_row.raw_payload,
                            raw_hash=raw_row.raw_hash,
                            is_processed=1,
                            processing_error="Duplicate canonical_id (idempotency)"
                        )
                        db.add(raw_record)
                    
                except Exception as e:
                    rows_error += 1
                    errors.append({
                        "row_idx": rows_extracted,
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "source_row_id": raw_row.source_row_id
                    })
                
                # Commit in batches
                if rows_extracted % 100 == 0:
                    db.commit()
            
            # Final commit
            db.commit()
            
        except Exception as e:
            errors.append({
                "row_idx": rows_extracted,
                "error_type": "extraction_error",
                "message": str(e)
            })
        
        return SyncResult(
            success=rows_error == 0,
            rows_extracted=rows_extracted,
            rows_normalized=rows_normalized,
            rows_loaded=rows_loaded,
            rows_skipped=rows_skipped,
            rows_error=rows_error,
            errors=errors,
            warnings=warnings,
            date_range_start=min_date,
            date_range_end=max_date
        )
    
    def _check_schema_drift(
        self,
        db: Session,
        connection_id: int,
        new_dataset: LineageDataset,
        new_schema: SchemaInfo
    ):
        """Check for schema drift and record if detected."""
        # Get previous dataset for this connection
        previous_dataset = db.query(LineageDataset).join(
            SyncRun, LineageDataset.sync_run_id == SyncRun.id
        ).filter(
            SyncRun.connection_id == connection_id,
            LineageDataset.id != new_dataset.id
        ).order_by(LineageDataset.created_at.desc()).first()
        
        if not previous_dataset or not previous_dataset.schema_fingerprint:
            return  # No previous schema to compare
        
        if previous_dataset.schema_fingerprint == new_schema.fingerprint:
            return  # No drift
        
        # Detect specific changes
        old_columns = {c["name"]: c for c in (previous_dataset.schema_columns_json or [])}
        new_columns = {c["name"]: c for c in new_schema.columns}
        
        added = [c for name, c in new_columns.items() if name not in old_columns]
        removed = [c for name, c in old_columns.items() if name not in new_columns]
        type_changes = [
            {"name": name, "old_type": old_columns[name]["type"], "new_type": new_columns[name]["type"]}
            for name in old_columns
            if name in new_columns and old_columns[name]["type"] != new_columns[name]["type"]
        ]
        
        # Determine severity
        severity = "info"
        if removed or type_changes:
            severity = "warning"
        if any(c["name"] in ["amount", "currency", "date", "due_date"] for c in removed):
            severity = "error"
        
        # Record drift event
        drift_event = SchemaDriftEvent(
            connection_id=connection_id,
            old_dataset_id=previous_dataset.id,
            new_dataset_id=new_dataset.id,
            old_fingerprint=previous_dataset.schema_fingerprint,
            new_fingerprint=new_schema.fingerprint,
            added_columns_json=added if added else None,
            removed_columns_json=removed if removed else None,
            type_changes_json=type_changes if type_changes else None,
            severity=severity
        )
        db.add(drift_event)
        db.commit()
    
    def get_sync_run(self, sync_run_id: int) -> Optional[SyncRun]:
        """Get sync run by ID."""
        return self.db.query(SyncRun).filter(SyncRun.id == sync_run_id).first()
    
    def get_sync_runs(self, connection_id: int, limit: int = 20) -> List[SyncRun]:
        """Get sync runs for a connection."""
        return self.db.query(SyncRun).filter(
            SyncRun.connection_id == connection_id
        ).order_by(SyncRun.started_at.desc()).limit(limit).all()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATASET MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_dataset(self, dataset_id: int) -> Optional[LineageDataset]:
        """Get dataset by ID."""
        return self.db.query(LineageDataset).filter(
            LineageDataset.id == dataset_id
        ).first()
    
    def get_dataset_by_uuid(self, dataset_uuid: str) -> Optional[LineageDataset]:
        """Get dataset by UUID."""
        return self.db.query(LineageDataset).filter(
            LineageDataset.dataset_id == dataset_uuid
        ).first()
    
    def get_canonical_records(
        self,
        dataset_id: int,
        record_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CanonicalRecord]:
        """Get canonical records from a dataset."""
        query = self.db.query(CanonicalRecord).filter(
            CanonicalRecord.dataset_id == dataset_id
        )
        if record_type:
            query = query.filter(CanonicalRecord.record_type == record_type)
        return query.offset(offset).limit(limit).all()
    
    def get_raw_records(
        self,
        dataset_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[RawRecord]:
        """Get raw records from a dataset."""
        return self.db.query(RawRecord).filter(
            RawRecord.dataset_id == dataset_id
        ).offset(offset).limit(limit).all()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVIDENCE LINKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def create_evidence_ref(
        self,
        kind: str,
        ref_id: int,
        context_type: Optional[str] = None,
        context_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LineageEvidenceRef:
        """Create an evidence reference."""
        evidence_ref = LineageEvidenceRef(
            kind=kind,
            ref_id=ref_id,
            context_type=context_type,
            context_id=context_id,
            metadata_json=metadata
        )
        self.db.add(evidence_ref)
        self.db.commit()
        self.db.refresh(evidence_ref)
        return evidence_ref
    
    def get_evidence_for_context(
        self,
        context_type: str,
        context_id: int
    ) -> List[LineageEvidenceRef]:
        """Get all evidence for a given context."""
        return self.db.query(LineageEvidenceRef).filter(
            LineageEvidenceRef.context_type == context_type,
            LineageEvidenceRef.context_id == context_id
        ).all()
