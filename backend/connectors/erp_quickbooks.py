"""
QuickBooks Online Connector (Using Official SDK)

Uses intuit-oauth for authentication and quickbooks-python for API calls.

QuickBooks API: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities
"""

from datetime import datetime
from typing import Any, Dict, Iterator, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK imports
try:
    from intuitlib.client import AuthClient
    from intuitlib.enums import Scopes
    from quickbooks import QuickBooks
    from quickbooks.objects.invoice import Invoice as QBInvoice
    from quickbooks.objects.bill import Bill as QBBill
    from quickbooks.objects.payment import Payment as QBPayment
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class QuickBooksConnector(APIConnector):
    """
    Connector for QuickBooks Online using Official SDK.
    
    Config:
        client_id: OAuth client ID
        client_secret: OAuth client secret (or reference)
        refresh_token: OAuth refresh token (or reference)
        realm_id: QuickBooks company ID
        environment: 'sandbox' or 'production'
    """
    
    connector_type = ConnectorType.ERP_QUICKBOOKS
    display_name = "QuickBooks Online"
    description = "QuickBooks Online accounting software via Official SDK"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.auth_client = None
        self.qb_client = None
        self.realm_id = config.get('realm_id')
        self.environment = config.get('environment', 'sandbox')
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("QuickBooks SDK not installed. Run: pip install intuit-oauth quickbooks-python")
        required = ['client_id', 'realm_id']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def _get_secret(self, key: str) -> str:
        """Retrieve secret - in production, use secrets manager."""
        return self.config.get(key, '')
    
    def authenticate(self) -> bool:
        """Authenticate with QuickBooks using OAuth 2.0."""
        if not HAS_SDK:
            return False
            
        try:
            client_id = self.config.get('client_id')
            client_secret = self._get_secret('client_secret')
            refresh_token = self._get_secret('refresh_token')
            
            if not all([client_id, client_secret, refresh_token]):
                print("Missing QuickBooks credentials")
                return False
            
            # Initialize auth client
            self.auth_client = AuthClient(
                client_id=client_id,
                client_secret=client_secret,
                environment=self.environment,
                redirect_uri='https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl'
            )
            
            # Refresh access token
            self.auth_client.refresh(refresh_token=refresh_token)
            
            # Initialize QuickBooks client
            self.qb_client = QuickBooks(
                auth_client=self.auth_client,
                refresh_token=refresh_token,
                company_id=self.realm_id
            )
            
            return True
            
        except Exception as e:
            print(f"QuickBooks auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test QuickBooks connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="QuickBooks SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            from quickbooks.objects.companyinfo import CompanyInfo
            company_info = CompanyInfo.get(self.realm_id, qb=self.qb_client)
            return ConnectorResult(
                success=True,
                message=f"Connected to: {company_info.CompanyName}"
            )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch invoices, bills, and payments from QuickBooks."""
        if not self.qb_client:
            return
            
        # Fetch AR Invoices
        yield from self._fetch_invoices(context)
        
        # Fetch AP Bills
        yield from self._fetch_bills(context)
        
        # Fetch Payments
        yield from self._fetch_payments(context)
    
    def _fetch_invoices(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AR invoices using SDK."""
        try:
            invoices = QBInvoice.all(qb=self.qb_client, max_results=1000)
            
            for inv in invoices:
                yield {
                    '_record_type': 'invoice',
                    'Id': inv.Id,
                    'DocNumber': inv.DocNumber,
                    'CustomerRef': {
                        'value': inv.CustomerRef.value if inv.CustomerRef else None,
                        'name': inv.CustomerRef.name if inv.CustomerRef else None
                    },
                    'TotalAmt': float(inv.TotalAmt) if inv.TotalAmt else 0,
                    'Balance': float(inv.Balance) if inv.Balance else 0,
                    'CurrencyRef': {'value': inv.CurrencyRef.value if inv.CurrencyRef else 'USD'},
                    'TxnDate': str(inv.TxnDate) if inv.TxnDate else None,
                    'DueDate': str(inv.DueDate) if inv.DueDate else None,
                    'EmailStatus': inv.EmailStatus,
                    'SyncToken': inv.SyncToken,
                    'MetaData': {
                        'LastUpdatedTime': str(inv.MetaData.LastUpdatedTime) if inv.MetaData else None
                    }
                }
        except Exception as e:
            print(f"Error fetching invoices: {e}")
    
    def _fetch_bills(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AP bills using SDK."""
        try:
            bills = QBBill.all(qb=self.qb_client, max_results=1000)
            
            for bill in bills:
                yield {
                    '_record_type': 'bill',
                    'Id': bill.Id,
                    'DocNumber': bill.DocNumber,
                    'VendorRef': {
                        'value': bill.VendorRef.value if bill.VendorRef else None,
                        'name': bill.VendorRef.name if bill.VendorRef else None
                    },
                    'TotalAmt': float(bill.TotalAmt) if bill.TotalAmt else 0,
                    'Balance': float(bill.Balance) if bill.Balance else 0,
                    'CurrencyRef': {'value': bill.CurrencyRef.value if bill.CurrencyRef else 'USD'},
                    'TxnDate': str(bill.TxnDate) if bill.TxnDate else None,
                    'DueDate': str(bill.DueDate) if bill.DueDate else None,
                    'SyncToken': bill.SyncToken,
                    'MetaData': {
                        'LastUpdatedTime': str(bill.MetaData.LastUpdatedTime) if bill.MetaData else None
                    }
                }
        except Exception as e:
            print(f"Error fetching bills: {e}")
    
    def _fetch_payments(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch payments using SDK."""
        try:
            payments = QBPayment.all(qb=self.qb_client, max_results=1000)
            
            for pmt in payments:
                yield {
                    '_record_type': 'payment',
                    'Id': pmt.Id,
                    'PaymentRefNum': pmt.PaymentRefNum,
                    'CustomerRef': {
                        'value': pmt.CustomerRef.value if pmt.CustomerRef else None,
                        'name': pmt.CustomerRef.name if pmt.CustomerRef else None
                    },
                    'TotalAmt': float(pmt.TotalAmt) if pmt.TotalAmt else 0,
                    'CurrencyRef': {'value': pmt.CurrencyRef.value if pmt.CurrencyRef else 'USD'},
                    'TxnDate': str(pmt.TxnDate) if pmt.TxnDate else None,
                    'DepositToAccountRef': {
                        'value': pmt.DepositToAccountRef.value if pmt.DepositToAccountRef else None
                    },
                    'Line': [{'TxnId': line.LinkedTxn[0].TxnId if line.LinkedTxn else None} 
                             for line in (pmt.Line or [])],
                    'MetaData': {
                        'LastUpdatedTime': str(pmt.MetaData.LastUpdatedTime) if pmt.MetaData else None
                    }
                }
        except Exception as e:
            print(f"Error fetching payments: {e}")
    
    def _get_record_type(self) -> str:
        return 'erp_record'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize QuickBooks record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'invoice')
        quality_issues = []
        
        if record_type == 'invoice':
            normalized = self._normalize_invoice(data)
        elif record_type == 'bill':
            normalized = self._normalize_bill(data)
        elif record_type == 'payment':
            normalized = self._normalize_payment(data)
        else:
            normalized = data
        
        if not normalized.get('amount'):
            quality_issues.append('missing_amount')
        if not normalized.get('due_date'):
            quality_issues.append('missing_due_date')
        
        canonical_id = self._generate_canonical_id(normalized, record_type)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type=record_type,
            data=normalized,
            source_id=record.source_id,
            source_system=f"QuickBooks:{self.realm_id}",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_invoice(self, data: Dict) -> Dict:
        """Normalize QuickBooks Invoice."""
        customer_ref = data.get('CustomerRef', {})
        return {
            'invoice_number': data.get('DocNumber', ''),
            'customer_id': customer_ref.get('value', ''),
            'customer_name': customer_ref.get('name', ''),
            'amount': float(data.get('TotalAmt', 0)),
            'balance': float(data.get('Balance', 0)),
            'currency': data.get('CurrencyRef', {}).get('value', 'USD'),
            'issue_date': data.get('TxnDate'),
            'due_date': data.get('DueDate'),
            'email_status': data.get('EmailStatus'),
            'is_paid': float(data.get('Balance', 0)) == 0,
            'qb_id': data.get('Id'),
            'sync_token': data.get('SyncToken'),
            'last_updated': data.get('MetaData', {}).get('LastUpdatedTime'),
        }
    
    def _normalize_bill(self, data: Dict) -> Dict:
        """Normalize QuickBooks Bill."""
        vendor_ref = data.get('VendorRef', {})
        return {
            'bill_number': data.get('DocNumber', ''),
            'vendor_id': vendor_ref.get('value', ''),
            'vendor_name': vendor_ref.get('name', ''),
            'amount': float(data.get('TotalAmt', 0)),
            'balance': float(data.get('Balance', 0)),
            'currency': data.get('CurrencyRef', {}).get('value', 'USD'),
            'issue_date': data.get('TxnDate'),
            'due_date': data.get('DueDate'),
            'is_paid': float(data.get('Balance', 0)) == 0,
            'qb_id': data.get('Id'),
            'sync_token': data.get('SyncToken'),
            'last_updated': data.get('MetaData', {}).get('LastUpdatedTime'),
        }
    
    def _normalize_payment(self, data: Dict) -> Dict:
        """Normalize QuickBooks Payment."""
        customer_ref = data.get('CustomerRef', {})
        return {
            'payment_ref': data.get('PaymentRefNum', ''),
            'customer_id': customer_ref.get('value', ''),
            'customer_name': customer_ref.get('name', ''),
            'amount': float(data.get('TotalAmt', 0)),
            'currency': data.get('CurrencyRef', {}).get('value', 'USD'),
            'payment_date': data.get('TxnDate'),
            'deposit_to_account': data.get('DepositToAccountRef', {}).get('value'),
            'qb_id': data.get('Id'),
            'linked_invoices': [line.get('TxnId') for line in data.get('Line', []) if line.get('TxnId')],
            'last_updated': data.get('MetaData', {}).get('LastUpdatedTime'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        if record_type == 'invoice':
            components = ['qb_invoice', str(self.realm_id), str(data.get('qb_id', ''))]
        elif record_type == 'bill':
            components = ['qb_bill', str(self.realm_id), str(data.get('qb_id', ''))]
        else:
            components = [f'qb_{record_type}', str(self.realm_id), str(data.get('qb_id', ''))]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
