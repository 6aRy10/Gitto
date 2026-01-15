"""
Data Freshness Service

Monitors data staleness across all connected sources.
Alerts when data sources become stale beyond configured thresholds.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import models


# Default freshness thresholds (hours)
DEFAULT_THRESHOLDS = {
    'bank_mt940': 24,      # Bank statements: stale after 24h
    'bank_bai2': 24,
    'bank_api': 4,          # Real-time bank APIs: 4h
    'erp_netsuite': 12,     # ERP data: 12h
    'erp_quickbooks': 12,
    'erp_xero': 12,
    'warehouse_snowflake': 6,
    'warehouse_bigquery': 6,
    'manual_upload': 168,   # Manual uploads: 7 days
}


def get_data_freshness_dashboard(db: Session) -> Dict[str, Any]:
    """
    Get comprehensive data freshness status for all sources.
    
    Returns:
        Dashboard data with source status, alerts, and metrics.
    """
    dashboard = {
        'as_of': datetime.utcnow().isoformat(),
        'sources': [],
        'alerts': [],
        'summary': {
            'total_sources': 0,
            'fresh': 0,
            'stale': 0,
            'critical': 0,
            'unknown': 0
        }
    }
    
    # Get all connections with their last sync info
    connections = db.query(models.Connection).all()
    
    for conn in connections:
        connector = conn.connector
        source_status = get_source_freshness(db, conn)
        dashboard['sources'].append(source_status)
        
        # Update summary
        dashboard['summary']['total_sources'] += 1
        status = source_status.get('status', 'unknown')
        if status == 'fresh':
            dashboard['summary']['fresh'] += 1
        elif status == 'stale':
            dashboard['summary']['stale'] += 1
        elif status == 'critical':
            dashboard['summary']['critical'] += 1
        else:
            dashboard['summary']['unknown'] += 1
        
        # Add alerts for stale/critical sources
        if status in ('stale', 'critical'):
            dashboard['alerts'].append({
                'connection_id': conn.id,
                'source_name': connector.name if connector else f"Connection #{conn.id}",
                'severity': 'warning' if status == 'stale' else 'critical',
                'message': f"Data is {source_status.get('hours_since_sync', 0):.1f} hours old",
                'threshold_hours': source_status.get('threshold_hours', 24)
            })
    
    # Calculate overall health score
    total = dashboard['summary']['total_sources']
    if total > 0:
        fresh_pct = (dashboard['summary']['fresh'] / total) * 100
        dashboard['summary']['health_score'] = round(fresh_pct, 1)
    else:
        dashboard['summary']['health_score'] = 100.0
    
    return dashboard


def get_source_freshness(db: Session, connection: models.Connection) -> Dict[str, Any]:
    """
    Get freshness status for a single data source.
    """
    connector = connection.connector
    connector_type = connector.type if connector else 'unknown'
    
    # Get threshold for this connector type
    threshold_hours = DEFAULT_THRESHOLDS.get(connector_type, 24)
    
    # Calculate hours since last sync
    last_sync = connection.last_success_at or connection.last_sync_at
    if last_sync:
        hours_since = (datetime.utcnow() - last_sync).total_seconds() / 3600
    else:
        hours_since = float('inf')
    
    # Determine status
    if hours_since == float('inf'):
        status = 'unknown'
    elif hours_since <= threshold_hours:
        status = 'fresh'
    elif hours_since <= threshold_hours * 2:
        status = 'stale'
    else:
        status = 'critical'
    
    # Get recent sync run stats
    recent_syncs = db.query(models.SyncRun)\
        .filter(models.SyncRun.connection_id == connection.id)\
        .order_by(models.SyncRun.started_at.desc())\
        .limit(5)\
        .all()
    
    sync_history = []
    for run in recent_syncs:
        sync_history.append({
            'id': run.id,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'completed_at': run.completed_at.isoformat() if run.completed_at else None,
            'status': run.status,
            'rows_extracted': run.rows_extracted,
            'error_message': run.error_message
        })
    
    return {
        'connection_id': connection.id,
        'connection_name': connection.name,
        'connector_type': connector_type,
        'connector_name': connector.name if connector else 'Unknown',
        'status': status,
        'last_sync_at': last_sync.isoformat() if last_sync else None,
        'hours_since_sync': round(hours_since, 1) if hours_since != float('inf') else None,
        'threshold_hours': threshold_hours,
        'sync_status': connection.sync_status,
        'consecutive_failures': connection.consecutive_failures,
        'recent_syncs': sync_history
    }


def check_snapshot_data_freshness(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """
    Check data freshness for all sources contributing to a snapshot.
    
    This is critical for Lock Snapshot - warn/block if data is stale.
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    if not snapshot:
        return {'error': 'Snapshot not found'}
    
    result = {
        'snapshot_id': snapshot_id,
        'snapshot_name': snapshot.name,
        'as_of': datetime.utcnow().isoformat(),
        'sources': [],
        'can_lock': True,
        'lock_warnings': [],
        'lock_blockers': []
    }
    
    # Get datasets referenced by this snapshot
    dataset_ids = []
    if snapshot.dataset_id:
        # Parse dataset_id (could be single or comma-separated)
        dataset_ids = [d.strip() for d in str(snapshot.dataset_id).split(',') if d.strip()]
    
    # Get invoices to understand data sources
    invoice_count = db.query(func.count(models.Invoice.id))\
        .filter(models.Invoice.snapshot_id == snapshot_id)\
        .scalar()
    
    # Get bank transactions count
    bank_txn_count = db.query(func.count(models.BankTransaction.id))\
        .filter(models.BankTransaction.snapshot_id == snapshot_id)\
        .scalar()
    
    # Check entity's connected sources
    if snapshot.entity_id:
        connectors = db.query(models.Connector)\
            .filter(models.Connector.entity_id == snapshot.entity_id)\
            .filter(models.Connector.is_active == 1)\
            .all()
        
        for connector in connectors:
            for connection in connector.connections:
                freshness = get_source_freshness(db, connection)
                result['sources'].append(freshness)
                
                status = freshness.get('status')
                if status == 'critical':
                    result['can_lock'] = False
                    result['lock_blockers'].append({
                        'source': freshness['connector_name'],
                        'reason': f"Data is {freshness.get('hours_since_sync', 'unknown')} hours old (critical)"
                    })
                elif status == 'stale':
                    result['lock_warnings'].append({
                        'source': freshness['connector_name'],
                        'reason': f"Data is {freshness.get('hours_since_sync', 0):.1f} hours old"
                    })
    
    # Check bank vs ERP age mismatch
    bank_as_of = _get_latest_data_timestamp(db, snapshot_id, 'bank')
    erp_as_of = _get_latest_data_timestamp(db, snapshot_id, 'erp')
    
    if bank_as_of and erp_as_of:
        mismatch_hours = abs((bank_as_of - erp_as_of).total_seconds() / 3600)
        if mismatch_hours > 24:
            result['lock_warnings'].append({
                'source': 'Bank vs ERP',
                'reason': f"Bank and ERP data have {mismatch_hours:.1f} hour age gap"
            })
    
    return result


def _get_latest_data_timestamp(db: Session, snapshot_id: int, source_type: str) -> Optional[datetime]:
    """Get the latest data timestamp for a source type in a snapshot."""
    if source_type == 'bank':
        latest = db.query(func.max(models.BankTransaction.value_date))\
            .filter(models.BankTransaction.snapshot_id == snapshot_id)\
            .scalar()
        if latest:
            if isinstance(latest, str):
                return datetime.fromisoformat(latest)
            return latest
    elif source_type == 'erp':
        # Use invoice dates as proxy for ERP data
        latest = db.query(func.max(models.Invoice.created_at))\
            .filter(models.Invoice.snapshot_id == snapshot_id)\
            .scalar()
        if latest:
            if isinstance(latest, str):
                return datetime.fromisoformat(latest)
            return latest
    return None


def create_freshness_alert(
    db: Session, 
    connection_id: int, 
    alert_type: str, 
    severity: str, 
    message: str
) -> models.DataFreshnessAlert:
    """Create a data freshness alert."""
    alert = models.DataFreshnessAlert(
        connection_id=connection_id,
        alert_type=alert_type,
        severity=severity,
        message=message
    )
    db.add(alert)
    db.commit()
    return alert


def get_unacknowledged_alerts(db: Session) -> List[models.DataFreshnessAlert]:
    """Get all unacknowledged freshness alerts."""
    return db.query(models.DataFreshnessAlert)\
        .filter(models.DataFreshnessAlert.acknowledged_at.is_(None))\
        .order_by(models.DataFreshnessAlert.created_at.desc())\
        .all()


def acknowledge_alert(db: Session, alert_id: int, user: str) -> bool:
    """Acknowledge a freshness alert."""
    alert = db.query(models.DataFreshnessAlert)\
        .filter(models.DataFreshnessAlert.id == alert_id)\
        .first()
    if alert:
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user
        db.commit()
        return True
    return False




