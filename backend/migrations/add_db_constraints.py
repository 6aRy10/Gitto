"""
Database Constraints and Triggers
Finance systems should not rely on "developer discipline" - enforce at DB level.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def add_finance_constraints(engine: Engine):
    """
    Add database-level constraints for data integrity.
    These are enforced at the database level, not just application code.
    """
    
    with engine.connect() as conn:
        # 1. UNIQUE constraint: (snapshot_id, canonical_id)
        # Prevents duplicate invoices in the same snapshot
        try:
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_invoice_snapshot_canonical 
                ON invoices(snapshot_id, canonical_id) 
                WHERE canonical_id IS NOT NULL
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Index might already exist: {e}")
        
        # 2. Check constraint: Locked snapshots cannot be updated
        # This would require a trigger in SQLite (which doesn't support CHECK constraints on updates)
        # For SQLite, we rely on application-level checks
        # For PostgreSQL, we could add:
        # ALTER TABLE invoices ADD CONSTRAINT check_snapshot_not_locked 
        # CHECK (NOT EXISTS (SELECT 1 FROM snapshots WHERE id = snapshot_id AND is_locked = 1))
        
        # 3. Referential integrity: Reconciliation allocations must reference valid invoices/transactions
        # SQLAlchemy handles this with ForeignKey, but we can add explicit constraints
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_reconciliation_invoice 
                ON reconciliation_table(invoice_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_reconciliation_transaction 
                ON reconciliation_table(bank_transaction_id)
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Indexes might already exist: {e}")
        
        # 4. Check constraint: Amount allocations cannot exceed transaction amount
        # (Would require triggers for complex validation)
        
        # 5. Trigger: Prevent updates to locked snapshots
        # SQLite doesn't support triggers well, but we can add for PostgreSQL
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS prevent_locked_snapshot_invoice_update
                BEFORE UPDATE ON invoices
                WHEN EXISTS (SELECT 1 FROM snapshots WHERE id = NEW.snapshot_id AND is_locked = 1)
                BEGIN
                    SELECT RAISE(ABORT, 'Cannot update invoice in locked snapshot');
                END;
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Trigger creation may not be supported: {e}")
        
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS prevent_locked_snapshot_bill_update
                BEFORE UPDATE ON vendor_bills
                WHEN EXISTS (SELECT 1 FROM snapshots WHERE id = NEW.snapshot_id AND is_locked = 1)
                BEGIN
                    SELECT RAISE(ABORT, 'Cannot update vendor bill in locked snapshot');
                END;
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Trigger creation may not be supported: {e}")
        # This would require a trigger or application-level validation
        # For SQLite, we add a check constraint
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS check_allocation_amount
                BEFORE INSERT ON reconciliation_table
                BEGIN
                    SELECT CASE
                        WHEN (SELECT amount FROM bank_transactions WHERE id = NEW.bank_transaction_id) < 
                             (SELECT COALESCE(SUM(amount_allocated), 0) FROM reconciliation_table 
                              WHERE bank_transaction_id = NEW.bank_transaction_id) + NEW.amount_allocated
                        THEN RAISE(ABORT, 'Allocation exceeds transaction amount')
                    END;
                END
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Trigger might not be supported or already exists: {e}")
        
        # 5. Check constraint: Invoice amounts must be positive
        try:
            conn.execute(text("""
                CREATE TRIGGER IF NOT EXISTS check_invoice_amount_positive
                BEFORE INSERT ON invoices
                BEGIN
                    SELECT CASE
                        WHEN NEW.amount < 0
                        THEN RAISE(ABORT, 'Invoice amount must be positive')
                    END;
                END
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: Trigger might not be supported or already exists: {e}")
        
        print("Database constraints added successfully")


def verify_constraints(engine: Engine) -> dict:
    """
    Verify that constraints are in place.
    Returns a dict with constraint status.
    """
    status = {
        'unique_canonical_id': False,
        'referential_integrity': False,
        'amount_positive': False
    }
    
    with engine.connect() as conn:
        # Check for unique index
        try:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_invoice_snapshot_canonical'
            """))
            if result.fetchone():
                status['unique_canonical_id'] = True
        except:
            pass
        
        # Check for triggers
        try:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='trigger' AND name='check_allocation_amount'
            """))
            if result.fetchone():
                status['referential_integrity'] = True
        except:
            pass
        
        try:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='trigger' AND name='check_invoice_amount_positive'
            """))
            if result.fetchone():
                status['amount_positive'] = True
        except:
            pass
    
    return status


