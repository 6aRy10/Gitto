"""
Google BigQuery Connector (Official SDK)

BigQuery is Google Cloud's serverless data warehouse.
Supports bi-directional sync with high-performance queries.

API: https://cloud.google.com/bigquery/docs/reference/libraries
"""

from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK
try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class BigQueryConnector(APIConnector):
    """
    Connector for Google BigQuery.
    
    Config:
        project_id: GCP project ID
        credentials_json: Path to service account JSON file
        dataset: Default dataset name
        location: BigQuery location (e.g., "US", "EU")
        
    Or use application default credentials:
        use_default_credentials: true
    """
    
    connector_type = ConnectorType.WAREHOUSE_BIGQUERY
    display_name = "BigQuery"
    description = "Google BigQuery for analytics and bi-directional sync"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("BigQuery SDK not installed. Run: pip install google-cloud-bigquery")
        if 'project_id' not in self.config:
            raise ValueError("project_id is required")
    
    def authenticate(self) -> bool:
        """Connect to BigQuery."""
        if not HAS_SDK:
            return False
            
        try:
            project_id = self.config.get('project_id')
            
            if self.config.get('credentials_json'):
                # Service account authentication
                credentials = service_account.Credentials.from_service_account_file(
                    self.config.get('credentials_json'),
                    scopes=['https://www.googleapis.com/auth/bigquery']
                )
                self.client = bigquery.Client(
                    project=project_id,
                    credentials=credentials,
                    location=self.config.get('location', 'US')
                )
            else:
                # Application default credentials
                self.client = bigquery.Client(
                    project=project_id,
                    location=self.config.get('location', 'US')
                )
            
            return True
            
        except Exception as e:
            print(f"BigQuery auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test BigQuery connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="BigQuery SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            # List datasets to verify access
            datasets = list(self.client.list_datasets(max_results=10))
            dataset_names = [d.dataset_id for d in datasets]
            
            return ConnectorResult(
                success=True,
                message=f"Connected to {self.config.get('project_id')}. Datasets: {', '.join(dataset_names[:3])}..."
            )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch records from configured queries."""
        if not self.client:
            return
        
        # Execute configured queries
        queries = self.config.get('queries', [])
        
        for query_config in queries:
            yield from self._execute_query(query_config, context)
    
    def _execute_query(self, query_config: Dict, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Execute a configured query and yield records."""
        try:
            query = query_config.get('sql')
            record_type = query_config.get('record_type', 'generic')
            
            # Add incremental filter if supported
            if context.since_timestamp and query_config.get('timestamp_column'):
                ts_col = query_config.get('timestamp_column')
                timestamp_str = context.since_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                if 'WHERE' in query.upper():
                    query = f"{query} AND {ts_col} > TIMESTAMP('{timestamp_str}')"
                else:
                    query = f"{query} WHERE {ts_col} > TIMESTAMP('{timestamp_str}')"
            
            query_job = self.client.query(query)
            results = query_job.result()
            
            for row in results:
                record = dict(row.items())
                record['_record_type'] = record_type
                yield record
                
        except Exception as e:
            print(f"Error executing query: {e}")
    
    def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute arbitrary SQL and return results."""
        if not self.client:
            if not self.authenticate():
                raise ConnectionError("Failed to connect to BigQuery")
        
        query_job = self.client.query(sql)
        results = query_job.result()
        
        return [dict(row.items()) for row in results]
    
    def write_records(self, table_id: str, records: List[Dict[str, Any]], 
                      write_disposition: str = "WRITE_APPEND") -> int:
        """
        Write records to a BigQuery table.
        
        Args:
            table_id: Full table ID (project.dataset.table)
            records: List of dictionaries to insert
            write_disposition: WRITE_APPEND, WRITE_TRUNCATE, or WRITE_EMPTY
        """
        if not self.client:
            if not self.authenticate():
                raise ConnectionError("Failed to connect to BigQuery")
        
        if not records:
            return 0
        
        # Use streaming insert for small batches
        if len(records) < 1000:
            errors = self.client.insert_rows_json(table_id, records)
            if errors:
                print(f"BigQuery insert errors: {errors}")
                return 0
            return len(records)
        
        # Use load job for larger batches
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        )
        
        import json
        import io
        
        json_data = '\n'.join(json.dumps(r) for r in records)
        load_job = self.client.load_table_from_file(
            io.StringIO(json_data),
            table_id,
            job_config=job_config
        )
        load_job.result()  # Wait for completion
        
        return load_job.output_rows
    
    def create_table(self, table_id: str, schema: List[Dict[str, str]]) -> bool:
        """
        Create a BigQuery table.
        
        Args:
            table_id: Full table ID (project.dataset.table)
            schema: List of {"name": "col", "type": "STRING"} dicts
        """
        if not self.client:
            if not self.authenticate():
                return False
        
        try:
            bq_schema = [
                bigquery.SchemaField(
                    name=field['name'],
                    field_type=field['type'],
                    mode=field.get('mode', 'NULLABLE')
                )
                for field in schema
            ]
            
            table = bigquery.Table(table_id, schema=bq_schema)
            self.client.create_table(table)
            return True
            
        except Exception as e:
            print(f"Error creating table: {e}")
            return False
    
    def _get_record_type(self) -> str:
        return 'warehouse_record'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize BigQuery record - pass through with metadata."""
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
                # Convert BigQuery types
                if hasattr(value, 'isoformat'):
                    normalized[key] = value.isoformat()
                else:
                    normalized[key] = value
        
        canonical_id = self._generate_canonical_id(normalized, record_type)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type=record_type,
            data=normalized,
            source_id=record.source_id,
            source_system=f"BigQuery:{self.config.get('project_id')}",
            source_checksum=record.compute_checksum(),
            quality_issues=[],
            is_complete=True
        )
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate canonical ID from primary key or hash."""
        import hashlib
        import json
        
        # Try to use configured primary key
        pk_columns = self.config.get('primary_key_columns', [])
        if pk_columns:
            pk_values = [str(data.get(col, '')) for col in pk_columns]
            components = [f'bigquery_{record_type}'] + pk_values
            content = '|'.join(components)
        else:
            # Hash all data
            content = json.dumps(data, sort_keys=True, default=str)
        
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"




