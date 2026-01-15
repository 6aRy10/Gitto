"""
Snapshot Immutability Protection
P2 Fix: Prevents modification of locked snapshots at application level.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models

class SnapshotLockedError(Exception):
    """Raised when attempting to modify a locked snapshot"""
    pass

def check_snapshot_not_locked(db: Session, snapshot_id: int, action: str = "modify") -> models.Snapshot:
    """
    P2 Fix: Check if snapshot is locked and raise error if attempting to modify.
    
    Args:
        db: Database session
        snapshot_id: ID of snapshot to check
        action: Description of action being attempted (for error message)
    
    Returns:
        Snapshot object if not locked
    
    Raises:
        HTTPException: If snapshot not found
        SnapshotLockedError: If snapshot is locked
    """
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == snapshot_id).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
    
    if snapshot.is_locked:
        lock_type = snapshot.lock_type or "Unknown"
        raise SnapshotLockedError(
            f"Cannot {action} locked snapshot {snapshot_id}. "
            f"Snapshot is locked with type: {lock_type}. "
            f"Unlock the snapshot first or create a new snapshot."
        )
    
    return snapshot

def require_snapshot_unlocked(snapshot_id: int):
    """
    Decorator to protect endpoints from modifying locked snapshots.
    Usage:
        @require_snapshot_unlocked(snapshot_id)
        def update_snapshot(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract db and snapshot_id from kwargs or args
            db = kwargs.get('db') or (args[0] if args else None)
            sid = kwargs.get('snapshot_id') or snapshot_id
            
            if db and sid:
                check_snapshot_not_locked(db, sid, f"execute {func.__name__}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


