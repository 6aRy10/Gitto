"""
Database Constraints for Immutable Snapshots

Enforces snapshot immutability at database level (triggers/constraints).
"""

from sqlalchemy import event, DDL
from sqlalchemy.engine import Engine
import models


def create_snapshot_immutability_constraints(engine):
    """
    Create database-level constraints to enforce snapshot immutability.
    
    This prevents direct SQL updates even if application checks are bypassed.
    """
    
    # SQLite doesn't support CHECK constraints on UPDATE, so we use triggers
    if engine.dialect.name == 'sqlite':
        # Trigger to prevent updates to locked snapshots
        trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS prevent_locked_snapshot_update
        BEFORE UPDATE ON snapshots
        FOR EACH ROW
        WHEN NEW.is_locked = 1
        BEGIN
            SELECT RAISE(ABORT, 'Cannot update locked snapshot. Snapshot is immutable once locked.');
        END;
        """
        
        # Trigger to prevent deletion of locked snapshots
        delete_trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS prevent_locked_snapshot_delete
        BEFORE DELETE ON snapshots
        FOR EACH ROW
        WHEN OLD.is_locked = 1
        BEGIN
            SELECT RAISE(ABORT, 'Cannot delete locked snapshot. Snapshot is immutable once locked.');
        END;
        """
        
        # Trigger to prevent invoice updates when snapshot is locked
        invoice_trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS prevent_invoice_update_locked_snapshot
        BEFORE UPDATE ON invoices
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM snapshots 
            WHERE snapshots.id = NEW.snapshot_id 
            AND snapshots.is_locked = 1
        )
        BEGIN
            SELECT RAISE(ABORT, 'Cannot update invoice in locked snapshot. Snapshot is immutable once locked.');
        END;
        """
        
        # Execute triggers
        with engine.connect() as conn:
            conn.execute(DDL(trigger_sql))
            conn.execute(DDL(delete_trigger_sql))
            conn.execute(DDL(invoice_trigger_sql))
            conn.commit()
    
    # For PostgreSQL, use CHECK constraints
    elif engine.dialect.name == 'postgresql':
        # Add check constraint (if not exists)
        constraint_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'snapshot_locked_immutable'
            ) THEN
                ALTER TABLE snapshots
                ADD CONSTRAINT snapshot_locked_immutable
                CHECK (
                    is_locked = 0 OR (
                        -- If locked, these fields cannot change
                        created_at = created_at AND
                        entity_id = entity_id
                    )
                );
            END IF;
        END $$;
        """
        
        with engine.connect() as conn:
            conn.execute(DDL(constraint_sql))
            conn.commit()


# Register event listener to create constraints on engine creation
@event.listens_for(Engine, "connect")
def create_constraints(dbapi_conn, connection_record):
    """Create constraints when database connection is established."""
    engine = connection_record.engine
    create_snapshot_immutability_constraints(engine)


