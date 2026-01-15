from sqlalchemy.orm import Session
import models
import json
from datetime import datetime
from typing import List
from secrets_manager import resolve_snowflake_password

# Mock implementation of Snowflake SDK interaction
# In a real environment, this would use snowflake.connector

class SnowflakeSyncEngine:
    def __init__(self, config: models.SnowflakeConfig):
        self.config = config
        # P1 Fix: Resolve password from environment variable
        self.password = resolve_snowflake_password(
            config.id, 
            config.password_env_var
        )
        if not self.password:
            raise ValueError(
                f"Snowflake password not found. Please set environment variable "
                f"GITTO_SNOWFLAKE_PASSWORD_{config.id} or configure password_env_var."
            )

    def pull_invoices(self, db: Session):
        """Fetches raw invoice data from Snowflake tables."""
        print(f"PULLING FROM SNOWFLAKE: {self.config.database}.{self.config.schema_name}")
        # Logic to execute SQL query based on self.config.invoice_mapping
        return []

    def push_match_decisions(self, db: Session, match_ids: List[int]):
        """
        Writes Gitto's reconciliation decisions back to a Snowflake sidecar table.
        This is critical for Enterprise 'Warehouse Mode'.
        """
        matches = db.query(models.ReconciliationTable).filter(models.ReconciliationTable.id.in_(match_ids)).all()
        
        writeback_payload = []
        for m in matches:
            writeback_payload.append({
                "canonical_id": m.invoice.canonical_id,
                "bank_txn_id": m.bank_transaction_id,
                "amount_reconciled": m.amount_allocated,
                "match_type": m.bank_transaction.reconciliation_type,
                "gitto_sync_at": datetime.utcnow().isoformat()
            })
            
        # SQL Implementation:
        # INSERT INTO GITTO_WRITEBACK_MATCHES (canonical_id, ...) VALUES (...)
        print(f"PUSHING {len(writeback_payload)} MATCH DECISIONS TO SNOWFLAKE.")
        return True

    def push_forecast_snapshot(self, db: Session, snapshot_id: int):
        """
        Pushes a flattened version of the 13-week forecast back to Snowflake.
        Allows BI teams to build dashboards on top of Gitto's intelligence.
        """
        from cash_calendar_service import get_13_week_workspace
        workspace = get_13_week_workspace(db, snapshot_id)
        
        if not workspace: return False
        
        writeback_payload = []
        for week in workspace['grid']:
            writeback_payload.append({
                "snapshot_id": snapshot_id,
                "week_label": week['week_label'],
                "start_date": week['start_date'],
                "projected_cash": week['closing_cash'],
                "p50_inflow": week['inflow_p50'],
                "committed_outflow": week['outflow_committed'],
                "gitto_sync_at": datetime.utcnow().isoformat()
            })
            
        print(f"PUSHING {len(writeback_payload)} FORECAST ROWS TO SNOWFLAKE.")
        return True

def sync_snowflake_bi_directional(db: Session, config_id: int):
    config = db.query(models.SnowflakeConfig).filter(models.SnowflakeConfig.id == config_id).first()
    if not config: return False
    
    engine = SnowflakeSyncEngine(config)
    
    # 1. Pull New Data
    new_data = engine.pull_invoices(db)
    
    # 2. Push Recent Decisions (Warehouse Mode)
    engine.push_match_decisions(db, []) # Pass recent match IDs
    
    # 3. Update Last Sync
    config.last_sync_at = datetime.utcnow()
    db.commit()
    
    return True

import json
from datetime import datetime
from typing import List
from secrets_manager import resolve_snowflake_password

# Mock implementation of Snowflake SDK interaction
# In a real environment, this would use snowflake.connector

class SnowflakeSyncEngine:
    def __init__(self, config: models.SnowflakeConfig):
        self.config = config
        # P1 Fix: Resolve password from environment variable
        self.password = resolve_snowflake_password(
            config.id, 
            config.password_env_var
        )
        if not self.password:
            raise ValueError(
                f"Snowflake password not found. Please set environment variable "
                f"GITTO_SNOWFLAKE_PASSWORD_{config.id} or configure password_env_var."
            )

    def pull_invoices(self, db: Session):
        """Fetches raw invoice data from Snowflake tables."""
        print(f"PULLING FROM SNOWFLAKE: {self.config.database}.{self.config.schema_name}")
        # Logic to execute SQL query based on self.config.invoice_mapping
        return []

    def push_match_decisions(self, db: Session, match_ids: List[int]):
        """
        Writes Gitto's reconciliation decisions back to a Snowflake sidecar table.
        This is critical for Enterprise 'Warehouse Mode'.
        """
        matches = db.query(models.ReconciliationTable).filter(models.ReconciliationTable.id.in_(match_ids)).all()
        
        writeback_payload = []
        for m in matches:
            writeback_payload.append({
                "canonical_id": m.invoice.canonical_id,
                "bank_txn_id": m.bank_transaction_id,
                "amount_reconciled": m.amount_allocated,
                "match_type": m.bank_transaction.reconciliation_type,
                "gitto_sync_at": datetime.utcnow().isoformat()
            })
            
        # SQL Implementation:
        # INSERT INTO GITTO_WRITEBACK_MATCHES (canonical_id, ...) VALUES (...)
        print(f"PUSHING {len(writeback_payload)} MATCH DECISIONS TO SNOWFLAKE.")
        return True

    def push_forecast_snapshot(self, db: Session, snapshot_id: int):
        """
        Pushes a flattened version of the 13-week forecast back to Snowflake.
        Allows BI teams to build dashboards on top of Gitto's intelligence.
        """
        from cash_calendar_service import get_13_week_workspace
        workspace = get_13_week_workspace(db, snapshot_id)
        
        if not workspace: return False
        
        writeback_payload = []
        for week in workspace['grid']:
            writeback_payload.append({
                "snapshot_id": snapshot_id,
                "week_label": week['week_label'],
                "start_date": week['start_date'],
                "projected_cash": week['closing_cash'],
                "p50_inflow": week['inflow_p50'],
                "committed_outflow": week['outflow_committed'],
                "gitto_sync_at": datetime.utcnow().isoformat()
            })
            
        print(f"PUSHING {len(writeback_payload)} FORECAST ROWS TO SNOWFLAKE.")
        return True

def sync_snowflake_bi_directional(db: Session, config_id: int):
    config = db.query(models.SnowflakeConfig).filter(models.SnowflakeConfig.id == config_id).first()
    if not config: return False
    
    engine = SnowflakeSyncEngine(config)
    
    # 1. Pull New Data
    new_data = engine.pull_invoices(db)
    
    # 2. Push Recent Decisions (Warehouse Mode)
    engine.push_match_decisions(db, []) # Pass recent match IDs
    
    # 3. Update Last Sync
    config.last_sync_at = datetime.utcnow()
    db.commit()
    
    return True
