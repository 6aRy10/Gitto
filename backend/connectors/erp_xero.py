"""
Xero Connector (Using Official SDK)

Uses xero-python SDK for authentication and API calls.

Xero API: https://developer.xero.com/documentation/api/accounting/overview
"""

from datetime import datetime
from typing import Any, Dict, Iterator, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK imports
try:
    from xero_python.api_client import ApiClient
    from xero_python.api_client.configuration import Configuration
    from xero_python.api_client.oauth2 import OAuth2Token
    from xero_python.accounting import AccountingApi
    from xero_python.identity import IdentityApi
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class XeroConnector(APIConnector):
    """
    Connector for Xero Accounting using Official SDK.
    
    Config:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        refresh_token: OAuth refresh token
        tenant_id: Xero organization ID
    """
    
    connector_type = ConnectorType.ERP_XERO
    display_name = "Xero"
    description = "Xero Accounting software via Official SDK"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_client = None
        self.accounting_api = None
        self.tenant_id = config.get('tenant_id')
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("Xero SDK not installed. Run: pip install xero-python")
        required = ['client_id', 'tenant_id']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def _get_secret(self, key: str) -> str:
        """Retrieve secret - in production, use secrets manager."""
        return self.config.get(key, '')
    
    def authenticate(self) -> bool:
        """Authenticate with Xero using OAuth 2.0."""
        if not HAS_SDK:
            return False
            
        try:
            client_id = self.config.get('client_id')
            client_secret = self._get_secret('client_secret')
            
            # Check for existing access token or refresh
            access_token = self._get_secret('access_token')
            refresh_token = self._get_secret('refresh_token')
            
            if not access_token and not refresh_token:
                print("Missing Xero credentials")
                return False
            
            # Configure API client
            api_client = ApiClient(
                Configuration(
                    oauth2_token=OAuth2Token(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                )
            )
            
            # Set access token
            if access_token:
                api_client.configuration.access_token = access_token
            
            self.api_client = api_client
            self.accounting_api = AccountingApi(api_client)
            
            return True
            
        except Exception as e:
            print(f"Xero auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test Xero connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="Xero SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            # Get organization info
            api_response = self.accounting_api.get_organisations(self.tenant_id)
            if api_response.organisations:
                org = api_response.organisations[0]
                return ConnectorResult(
                    success=True,
                    message=f"Connected to: {org.name}"
                )
            return ConnectorResult(success=False, message="No organizations found")
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch invoices, bills, and bank transactions from Xero."""
        if not self.accounting_api:
            return
            
        yield from self._fetch_invoices(context)
        yield from self._fetch_bills(context)
        yield from self._fetch_bank_transactions(context)
    
    def _fetch_invoices(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AR invoices (Type=ACCREC)."""
        try:
            where_clause = 'Type=="ACCREC"'
            if context.since_timestamp:
                where_clause += f' AND UpdatedDateUTC>DateTime({context.since_timestamp.year},{context.since_timestamp.month},{context.since_timestamp.day})'
            
            api_response = self.accounting_api.get_invoices(
                self.tenant_id,
                where=where_clause
            )
            
            for inv in (api_response.invoices or []):
                yield {
                    '_record_type': 'invoice',
                    'InvoiceID': inv.invoice_id,
                    'InvoiceNumber': inv.invoice_number,
                    'Contact': {
                        'ContactID': inv.contact.contact_id if inv.contact else None,
                        'Name': inv.contact.name if inv.contact else None
                    },
                    'Total': float(inv.total) if inv.total else 0,
                    'AmountDue': float(inv.amount_due) if inv.amount_due else 0,
                    'AmountPaid': float(inv.amount_paid) if inv.amount_paid else 0,
                    'CurrencyCode': inv.currency_code or 'USD',
                    'DateString': str(inv.date) if inv.date else None,
                    'DueDateString': str(inv.due_date) if inv.due_date else None,
                    'Status': inv.status,
                    'UpdatedDateUTC': str(inv.updated_date_utc) if inv.updated_date_utc else None
                }
        except Exception as e:
            print(f"Error fetching invoices: {e}")
    
    def _fetch_bills(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AP bills (Type=ACCPAY)."""
        try:
            where_clause = 'Type=="ACCPAY"'
            if context.since_timestamp:
                where_clause += f' AND UpdatedDateUTC>DateTime({context.since_timestamp.year},{context.since_timestamp.month},{context.since_timestamp.day})'
            
            api_response = self.accounting_api.get_invoices(
                self.tenant_id,
                where=where_clause
            )
            
            for bill in (api_response.invoices or []):
                yield {
                    '_record_type': 'bill',
                    'InvoiceID': bill.invoice_id,
                    'InvoiceNumber': bill.invoice_number,
                    'Contact': {
                        'ContactID': bill.contact.contact_id if bill.contact else None,
                        'Name': bill.contact.name if bill.contact else None
                    },
                    'Total': float(bill.total) if bill.total else 0,
                    'AmountDue': float(bill.amount_due) if bill.amount_due else 0,
                    'AmountPaid': float(bill.amount_paid) if bill.amount_paid else 0,
                    'CurrencyCode': bill.currency_code or 'USD',
                    'DateString': str(bill.date) if bill.date else None,
                    'DueDateString': str(bill.due_date) if bill.due_date else None,
                    'Status': bill.status,
                    'UpdatedDateUTC': str(bill.updated_date_utc) if bill.updated_date_utc else None
                }
        except Exception as e:
            print(f"Error fetching bills: {e}")
    
    def _fetch_bank_transactions(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch bank transactions."""
        try:
            api_response = self.accounting_api.get_bank_transactions(self.tenant_id)
            
            for txn in (api_response.bank_transactions or []):
                yield {
                    '_record_type': 'bank_txn',
                    'BankTransactionID': txn.bank_transaction_id,
                    'Contact': {
                        'ContactID': txn.contact.contact_id if txn.contact else None,
                        'Name': txn.contact.name if txn.contact else None
                    },
                    'BankAccount': {
                        'AccountID': txn.bank_account.account_id if txn.bank_account else None,
                        'Name': txn.bank_account.name if txn.bank_account else None
                    },
                    'Total': float(txn.total) if txn.total else 0,
                    'CurrencyCode': txn.currency_code or 'USD',
                    'DateString': str(txn.date) if txn.date else None,
                    'Type': txn.type,
                    'Status': txn.status,
                    'IsReconciled': txn.is_reconciled,
                    'UpdatedDateUTC': str(txn.updated_date_utc) if txn.updated_date_utc else None
                }
        except Exception as e:
            print(f"Error fetching bank transactions: {e}")
    
    def _get_record_type(self) -> str:
        return 'erp_record'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize Xero record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'invoice')
        quality_issues = []
        
        if record_type == 'invoice':
            normalized = self._normalize_invoice(data)
        elif record_type == 'bill':
            normalized = self._normalize_bill(data)
        elif record_type == 'bank_txn':
            normalized = self._normalize_bank_txn(data)
        else:
            normalized = data
        
        if not normalized.get('amount'):
            quality_issues.append('missing_amount')
        
        canonical_id = self._generate_canonical_id(normalized, record_type)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type=record_type,
            data=normalized,
            source_id=record.source_id,
            source_system=f"Xero:{self.tenant_id}",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_invoice(self, data: Dict) -> Dict:
        """Normalize Xero Invoice."""
        contact = data.get('Contact', {})
        return {
            'invoice_number': data.get('InvoiceNumber', ''),
            'customer_id': contact.get('ContactID', ''),
            'customer_name': contact.get('Name', ''),
            'amount': float(data.get('Total', 0)),
            'amount_due': float(data.get('AmountDue', 0)),
            'amount_paid': float(data.get('AmountPaid', 0)),
            'currency': data.get('CurrencyCode', 'USD'),
            'issue_date': data.get('DateString'),
            'due_date': data.get('DueDateString'),
            'status': data.get('Status'),
            'is_paid': data.get('Status') == 'PAID',
            'xero_id': data.get('InvoiceID'),
            'last_updated': data.get('UpdatedDateUTC'),
        }
    
    def _normalize_bill(self, data: Dict) -> Dict:
        """Normalize Xero Bill."""
        contact = data.get('Contact', {})
        return {
            'bill_number': data.get('InvoiceNumber', ''),
            'vendor_id': contact.get('ContactID', ''),
            'vendor_name': contact.get('Name', ''),
            'amount': float(data.get('Total', 0)),
            'amount_due': float(data.get('AmountDue', 0)),
            'amount_paid': float(data.get('AmountPaid', 0)),
            'currency': data.get('CurrencyCode', 'USD'),
            'issue_date': data.get('DateString'),
            'due_date': data.get('DueDateString'),
            'status': data.get('Status'),
            'is_paid': data.get('Status') == 'PAID',
            'xero_id': data.get('InvoiceID'),
            'last_updated': data.get('UpdatedDateUTC'),
        }
    
    def _normalize_bank_txn(self, data: Dict) -> Dict:
        """Normalize Xero Bank Transaction."""
        contact = data.get('Contact', {})
        bank_account = data.get('BankAccount', {})
        return {
            'txn_ref': data.get('BankTransactionID', ''),
            'account_id': bank_account.get('AccountID', ''),
            'account_name': bank_account.get('Name', ''),
            'counterparty_id': contact.get('ContactID', ''),
            'counterparty_name': contact.get('Name', ''),
            'amount': float(data.get('Total', 0)),
            'currency': data.get('CurrencyCode', 'USD'),
            'txn_date': data.get('DateString'),
            'txn_type': data.get('Type'),
            'status': data.get('Status'),
            'is_reconciled': data.get('IsReconciled', False),
            'xero_id': data.get('BankTransactionID'),
            'last_updated': data.get('UpdatedDateUTC'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        if record_type == 'invoice':
            components = ['xero_invoice', str(self.tenant_id), str(data.get('xero_id', ''))]
        elif record_type == 'bill':
            components = ['xero_bill', str(self.tenant_id), str(data.get('xero_id', ''))]
        else:
            components = [f'xero_{record_type}', str(self.tenant_id), str(data.get('xero_id', ''))]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
