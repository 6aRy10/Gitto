"""
Snowflake Data Warehouse Connector

Snowflake is a cloud data platform for analytics and data sharing.
Supports bi-directional sync: read data and writeback results.

API: https://docs.snowflake.com/en/developer-guide/python-connector/python-connector
"""

from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK
try:
    import snowflake.connector
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class SnowflakeConnector(APIConnector):
    """
    Connector for Snowflake Data Warehouse.
    
    Config:
        account: Snowflake account identifier (e.g., "xy12345.us-east-1")
        user: Username
        password: Password (or use key pair auth)
        warehouse: Warehouse name
        database: Database name
        schema: Schema name
        role: Role to use (optional)
        
    For key pair auth:
        private_key_path: Path to private key file
        private_key_passphrase: Passphrase for private key
    """
    
    connector_type = ConnectorType.WAREHOUSE_SNOWFLAKE
    display_name = "Snowflake"
    description = "Snowflake Data Warehouse for bi-directional sync"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = None
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("Snowflake SDK not installed. Run: pip install snowflake-connector-python")
        required = ['account', 'user', 'warehouse', 'database']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def authenticate(self) -> bool:
        """Connect to Snowflake."""
        if not HAS_SDK:
            return False
            
        try:
            connect_params = {
                'account': self.config.get('account'),
                'user': self.config.get('user'),
                'warehouse': self.config.get('warehouse'),
                'database': self.config.get('database'),
                'schema': self.config.get('schema', 'PUBLIC'),
            }
            
            # Password auth
            if self.config.get('password'):
                connect_params['password'] = self.config.get('password')
            
            # Key pair auth
            if self.config.get('private_key_path'):
                from cryptography.hazmat.backends import default_backend
                from cryptography.hazmat.primitives import serialization
                
                with open(self.config.get('private_key_path'), 'rb') as key_file:
                    p_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=self.config.get('private_key_passphrase', '').encode() or None,
                        backend=default_backend()
                    )
                connect_params['private_key'] = p_key
            
            # Role
            if self.config.get('role'):
                connect_params['role'] = self.config.get('role')
            
            self.connection = snowflake.connector.connect(**connect_params)
            return True
            
        except Exception as e:
            print(f"Snowflake auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test Snowflake connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="Snowflake SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
            row = cursor.fetchone()
            cursor.close()
            
            return ConnectorResult(
                success=True,
                message=f"Connected to {row[1]}.{row[2]} on warehouse {row[0]}"
            )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch records from configured queries."""
        if not self.connection:
            return
        
        # Execute configured queries
        queries = self.config.get('queries', [])
        
        for query_config in queries:
            yield from self._execute_query(query_config, context)
    
    def _execute_query(self, query_config: Dict, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Execute a configured query and yield records."""
        try:
            cursor = self.connection.cursor()
            
            query = query_config.get('sql')
            record_type = query_config.get('record_type', 'generic')
            
            # Add incremental filter if supported
            if context.since_timestamp and query_config.get('timestamp_column'):
                ts_col = query_config.get('timestamp_column')
                timestamp_str = context.since_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                query = f"{query} WHERE {ts_col} > '{timestamp_str}'"
            
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor:
                record = dict(zip(columns, row))
                record['_record_type'] = record_type
                yield record
            
            cursor.close()
            
        except Exception as e:
            print(f"Error executing query: {e}")
    
    def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute arbitrary SQL and return results."""
        if not self.connection:
            if not self.authenticate():
                raise ConnectionError("Failed to connect to Snowflake")
        
        cursor = self.connection.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor]
        cursor.close()
        return results
    
    def write_records(self, table: str, records: List[Dict[str, Any]]) -> int:
        """Write records to a Snowflake table."""
        if not self.connection:
            if not self.authenticate():
                raise ConnectionError("Failed to connect to Snowflake")
        
        if not records:
            return 0
        
        cursor = self.connection.cursor()
        
        # Get columns from first record
        columns = list(records[0].keys())
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        sql = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
        
        # Prepare values
        values = [tuple(r.get(c) for c in columns) for r in records]
        
        cursor.executemany(sql, values)
        self.connection.commit()
        
        rows_affected = cursor.rowcount
        cursor.close()
        
        return rows_affected
    
    def _get_record_type(self) -> str:
        return 'warehouse_record'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize Snowflake record - pass through with metadata."""
        data = record.data
        record_type = data.get('_record_type', 'generic')
        
        # Apply field mappings from context
        normalized = {}
        for source_field, target_field in context.field_mappings.items():
            if source_field in data:
                normalized[target_field] = data[source_field]
        
        # Include unmapped fields
        for key, value in data.items():
            if key not in context.field_mappings and key != '_record_type':
                normalized[key] = value
        
        canonical_id = self._generate_canonical_id(normalized, record_type)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type=record_type,
            data=normalized,
            source_id=record.source_id,
            source_system=f"Snowflake:{self.config.get('database')}",
            source_checksum=record.compute_checksum(),
            quality_issues=[],
            is_complete=True
        )
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate canonical ID from primary key or hash."""
        import hashlib
        
        # Try to use configured primary key
        pk_columns = self.config.get('primary_key_columns', [])
        if pk_columns:
            pk_values = [str(data.get(col, '')) for col in pk_columns]
            components = [f'snowflake_{record_type}'] + pk_values
        else:
            # Hash all data
            import json
            content = json.dumps(data, sort_keys=True, default=str)
            return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    def close(self):
        """Close the connection."""
        if self.connection:
            self.connection.close()
            self.connection = None




