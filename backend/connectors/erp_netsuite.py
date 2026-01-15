"""
NetSuite Connector (Official SDK)

NetSuite is Oracle's ERP for mid-market and enterprise.
Uses SuiteTalk SOAP/REST API for data extraction.

API: https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/chapter_1520808489.html
"""

from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK
try:
    from netsuitesdk import NetSuiteConnection
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class NetSuiteConnector(APIConnector):
    """
    Connector for NetSuite ERP via SuiteTalk API.
    
    Config:
        account: NetSuite account ID (e.g., "1234567")
        consumer_key: OAuth consumer key
        consumer_secret: OAuth consumer secret
        token_key: Token ID
        token_secret: Token secret
    """
    
    connector_type = ConnectorType.ERP_NETSUITE
    display_name = "NetSuite"
    description = "Oracle NetSuite ERP via SuiteTalk API"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = None
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("NetSuite SDK not installed. Run: pip install netsuitesdk")
        required = ['account', 'consumer_key', 'consumer_secret', 'token_key', 'token_secret']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def authenticate(self) -> bool:
        """Authenticate with NetSuite using Token-Based Auth."""
        if not HAS_SDK:
            return False
            
        try:
            self.connection = NetSuiteConnection(
                account=self.config.get('account'),
                consumer_key=self.config.get('consumer_key'),
                consumer_secret=self.config.get('consumer_secret'),
                token_key=self.config.get('token_key'),
                token_secret=self.config.get('token_secret')
            )
            return True
        except Exception as e:
            print(f"NetSuite auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test NetSuite connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="NetSuite SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            # Try to get subsidiaries to verify connection
            subs = self.connection.subsidiaries.get_all()
            return ConnectorResult(
                success=True,
                message=f"Connected to NetSuite. Found {len(subs)} subsidiaries."
            )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch invoices, vendor bills, and payments from NetSuite."""
        if not self.connection:
            return
        
        # AR Invoices
        yield from self._fetch_invoices(context)
        
        # AP Vendor Bills
        yield from self._fetch_vendor_bills(context)
        
        # Customer Payments
        yield from self._fetch_payments(context)
    
    def _fetch_invoices(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AR invoices."""
        try:
            invoices = self.connection.invoices.get_all()
            
            for inv in invoices:
                yield {
                    '_record_type': 'invoice',
                    'internalId': inv.get('internalId'),
                    'tranId': inv.get('tranId'),
                    'entity': inv.get('entity', {}).get('name'),
                    'entityId': inv.get('entity', {}).get('internalId'),
                    'subsidiary': inv.get('subsidiary', {}).get('name'),
                    'total': float(inv.get('total', 0)),
                    'amountRemaining': float(inv.get('amountRemaining', 0)),
                    'currency': inv.get('currency', {}).get('name', 'USD'),
                    'tranDate': inv.get('tranDate'),
                    'dueDate': inv.get('dueDate'),
                    'status': inv.get('status'),
                    'lastModifiedDate': inv.get('lastModifiedDate')
                }
        except Exception as e:
            print(f"Error fetching invoices: {e}")
    
    def _fetch_vendor_bills(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AP vendor bills."""
        try:
            bills = self.connection.vendor_bills.get_all()
            
            for bill in bills:
                yield {
                    '_record_type': 'vendor_bill',
                    'internalId': bill.get('internalId'),
                    'tranId': bill.get('tranId'),
                    'entity': bill.get('entity', {}).get('name'),
                    'entityId': bill.get('entity', {}).get('internalId'),
                    'subsidiary': bill.get('subsidiary', {}).get('name'),
                    'total': float(bill.get('total', 0)),
                    'amountRemaining': float(bill.get('amountRemaining', 0)),
                    'currency': bill.get('currency', {}).get('name', 'USD'),
                    'tranDate': bill.get('tranDate'),
                    'dueDate': bill.get('dueDate'),
                    'status': bill.get('status'),
                    'lastModifiedDate': bill.get('lastModifiedDate')
                }
        except Exception as e:
            print(f"Error fetching vendor bills: {e}")
    
    def _fetch_payments(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch customer payments."""
        try:
            payments = self.connection.customer_payments.get_all()
            
            for pmt in payments:
                yield {
                    '_record_type': 'payment',
                    'internalId': pmt.get('internalId'),
                    'tranId': pmt.get('tranId'),
                    'customer': pmt.get('customer', {}).get('name'),
                    'customerId': pmt.get('customer', {}).get('internalId'),
                    'total': float(pmt.get('total', 0)),
                    'currency': pmt.get('currency', {}).get('name', 'USD'),
                    'tranDate': pmt.get('tranDate'),
                    'account': pmt.get('account', {}).get('name'),
                    'lastModifiedDate': pmt.get('lastModifiedDate')
                }
        except Exception as e:
            print(f"Error fetching payments: {e}")
    
    def _get_record_type(self) -> str:
        return 'erp_record'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize NetSuite record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'invoice')
        quality_issues = []
        
        if record_type == 'invoice':
            normalized = self._normalize_invoice(data)
        elif record_type == 'vendor_bill':
            normalized = self._normalize_vendor_bill(data)
        elif record_type == 'payment':
            normalized = self._normalize_payment(data)
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
            source_system=f"NetSuite:{self.config.get('account')}",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_invoice(self, data: Dict) -> Dict:
        """Normalize NetSuite Invoice."""
        return {
            'invoice_number': data.get('tranId', ''),
            'customer_id': data.get('entityId', ''),
            'customer_name': data.get('entity', ''),
            'amount': data.get('total', 0),
            'amount_due': data.get('amountRemaining', 0),
            'currency': data.get('currency', 'USD'),
            'issue_date': data.get('tranDate'),
            'due_date': data.get('dueDate'),
            'status': data.get('status'),
            'subsidiary': data.get('subsidiary'),
            'is_paid': data.get('amountRemaining', 0) == 0,
            'netsuite_id': data.get('internalId'),
            'last_updated': data.get('lastModifiedDate'),
        }
    
    def _normalize_vendor_bill(self, data: Dict) -> Dict:
        """Normalize NetSuite Vendor Bill."""
        return {
            'bill_number': data.get('tranId', ''),
            'vendor_id': data.get('entityId', ''),
            'vendor_name': data.get('entity', ''),
            'amount': data.get('total', 0),
            'amount_due': data.get('amountRemaining', 0),
            'currency': data.get('currency', 'USD'),
            'issue_date': data.get('tranDate'),
            'due_date': data.get('dueDate'),
            'status': data.get('status'),
            'subsidiary': data.get('subsidiary'),
            'is_paid': data.get('amountRemaining', 0) == 0,
            'netsuite_id': data.get('internalId'),
            'last_updated': data.get('lastModifiedDate'),
        }
    
    def _normalize_payment(self, data: Dict) -> Dict:
        """Normalize NetSuite Payment."""
        return {
            'payment_ref': data.get('tranId', ''),
            'customer_id': data.get('customerId', ''),
            'customer_name': data.get('customer', ''),
            'amount': data.get('total', 0),
            'currency': data.get('currency', 'USD'),
            'payment_date': data.get('tranDate'),
            'deposit_account': data.get('account'),
            'netsuite_id': data.get('internalId'),
            'last_updated': data.get('lastModifiedDate'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        ns_id = data.get('netsuite_id', '')
        components = [f'netsuite_{record_type}', str(self.config.get('account')), str(ns_id)]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"




