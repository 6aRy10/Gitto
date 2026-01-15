"""
SAP S/4HANA Connector

SAP S/4HANA is the enterprise ERP for large organizations.
Supports both OData REST API and BAPI/RFC connections.

API: https://api.sap.com/
"""

from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
import requests
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)


class SAPConnector(APIConnector):
    """
    Connector for SAP S/4HANA via OData API.
    
    Config:
        base_url: SAP system URL (e.g., "https://mysap.example.com:443")
        client: SAP client number (e.g., "100")
        username: SAP username
        password: SAP password
        
    For cloud (SAP S/4HANA Cloud):
        base_url: "https://{tenant}.s4hana.ondemand.com"
        auth_type: "oauth" or "basic"
        client_id: OAuth client ID (if oauth)
        client_secret: OAuth client secret (if oauth)
    """
    
    connector_type = ConnectorType.ERP_SAP
    display_name = "SAP S/4HANA"
    description = "SAP S/4HANA ERP via OData API"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.session = None
        self.access_token = None
    
    def _validate_config(self) -> None:
        required = ['base_url']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def authenticate(self) -> bool:
        """Authenticate with SAP system."""
        try:
            self.session = requests.Session()
            
            auth_type = self.config.get('auth_type', 'basic')
            
            if auth_type == 'oauth':
                # OAuth 2.0 for SAP S/4HANA Cloud
                return self._oauth_auth()
            else:
                # Basic Auth for on-premise
                return self._basic_auth()
                
        except Exception as e:
            print(f"SAP auth error: {e}")
            return False
    
    def _basic_auth(self) -> bool:
        """Basic authentication for on-premise SAP."""
        username = self.config.get('username')
        password = self.config.get('password')
        
        if not username or not password:
            return False
        
        self.session.auth = (username, password)
        self.session.headers.update({
            'Accept': 'application/json',
            'sap-client': self.config.get('client', '100')
        })
        return True
    
    def _oauth_auth(self) -> bool:
        """OAuth 2.0 for SAP S/4HANA Cloud."""
        token_url = f"{self.config.get('base_url')}/sap/bc/sec/oauth2/token"
        
        response = requests.post(
            token_url,
            data={
                'grant_type': 'client_credentials',
                'client_id': self.config.get('client_id'),
                'client_secret': self.config.get('client_secret')
            }
        )
        
        if response.status_code == 200:
            self.access_token = response.json().get('access_token')
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            })
            return True
        return False
    
    def test_connection(self) -> ConnectorResult:
        """Test SAP connection."""
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            # Try to fetch company codes
            url = f"{self.config.get('base_url')}/sap/opu/odata/sap/API_COMPANYCODE_SRV/A_CompanyCode"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('d', {}).get('results', []))
                return ConnectorResult(
                    success=True,
                    message=f"Connected to SAP. Found {count} company codes."
                )
            else:
                return ConnectorResult(
                    success=False,
                    message=f"Connection failed: HTTP {response.status_code}"
                )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch financial documents from SAP."""
        if not self.session:
            return
        
        # AR - Customer Invoices
        yield from self._fetch_customer_invoices(context)
        
        # AP - Supplier Invoices
        yield from self._fetch_supplier_invoices(context)
        
        # Bank Statements
        yield from self._fetch_bank_statements(context)
    
    def _fetch_customer_invoices(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AR invoices via Billing Document API."""
        try:
            url = f"{self.config.get('base_url')}/sap/opu/odata/sap/API_BILLING_DOCUMENT_SRV/A_BillingDocument"
            params = {'$top': 1000, '$format': 'json'}
            
            response = self.session.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                results = response.json().get('d', {}).get('results', [])
                
                for doc in results:
                    yield {
                        '_record_type': 'invoice',
                        'BillingDocument': doc.get('BillingDocument'),
                        'BillingDocumentType': doc.get('BillingDocumentType'),
                        'SoldToParty': doc.get('SoldToParty'),
                        'PayerParty': doc.get('PayerParty'),
                        'TotalNetAmount': float(doc.get('TotalNetAmount', 0)),
                        'TransactionCurrency': doc.get('TransactionCurrency'),
                        'BillingDocumentDate': doc.get('BillingDocumentDate'),
                        'PaymentTerms': doc.get('CustomerPaymentTerms'),
                        'CompanyCode': doc.get('CompanyCode'),
                        'LastChangeDate': doc.get('LastChangeDate')
                    }
        except Exception as e:
            print(f"Error fetching customer invoices: {e}")
    
    def _fetch_supplier_invoices(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch AP invoices via Supplier Invoice API."""
        try:
            url = f"{self.config.get('base_url')}/sap/opu/odata/sap/API_SUPPLIERINVOICE_PROCESS_SRV/A_SupplierInvoice"
            params = {'$top': 1000, '$format': 'json'}
            
            response = self.session.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                results = response.json().get('d', {}).get('results', [])
                
                for doc in results:
                    yield {
                        '_record_type': 'vendor_bill',
                        'SupplierInvoice': doc.get('SupplierInvoice'),
                        'FiscalYear': doc.get('FiscalYear'),
                        'InvoicingParty': doc.get('InvoicingParty'),
                        'InvoiceGrossAmount': float(doc.get('InvoiceGrossAmount', 0)),
                        'DocumentCurrency': doc.get('DocumentCurrency'),
                        'DocumentDate': doc.get('DocumentDate'),
                        'PostingDate': doc.get('PostingDate'),
                        'DueCalculationBaseDate': doc.get('DueCalculationBaseDate'),
                        'CompanyCode': doc.get('CompanyCode'),
                        'PaymentTerms': doc.get('PaymentTerms')
                    }
        except Exception as e:
            print(f"Error fetching supplier invoices: {e}")
    
    def _fetch_bank_statements(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch bank statements via Bank Statement API."""
        try:
            url = f"{self.config.get('base_url')}/sap/opu/odata/sap/API_BANKSTATEMENT_SRV/A_BankStatement"
            params = {'$top': 1000, '$format': 'json'}
            
            response = self.session.get(url, params=params, timeout=60)
            
            if response.status_code == 200:
                results = response.json().get('d', {}).get('results', [])
                
                for stmt in results:
                    yield {
                        '_record_type': 'bank_statement',
                        'BankStatement': stmt.get('BankStatement'),
                        'HouseBank': stmt.get('HouseBank'),
                        'HouseBankAccount': stmt.get('HouseBankAccount'),
                        'BankStatementDate': stmt.get('BankStatementDate'),
                        'OpeningBalanceAmount': float(stmt.get('OpeningBalanceAmtInCoCodeCrcy', 0)),
                        'ClosingBalanceAmount': float(stmt.get('ClosingBalanceAmtInCoCodeCrcy', 0)),
                        'Currency': stmt.get('CompanyCodeCurrency'),
                        'CompanyCode': stmt.get('CompanyCode')
                    }
        except Exception as e:
            print(f"Error fetching bank statements: {e}")
    
    def _get_record_type(self) -> str:
        return 'erp_record'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize SAP record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'invoice')
        quality_issues = []
        
        if record_type == 'invoice':
            normalized = self._normalize_invoice(data)
        elif record_type == 'vendor_bill':
            normalized = self._normalize_vendor_bill(data)
        elif record_type == 'bank_statement':
            normalized = self._normalize_bank_statement(data)
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
            source_system=f"SAP:{self.config.get('client', 'unknown')}",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_invoice(self, data: Dict) -> Dict:
        """Normalize SAP Billing Document."""
        return {
            'invoice_number': data.get('BillingDocument', ''),
            'invoice_type': data.get('BillingDocumentType', ''),
            'customer_id': data.get('SoldToParty', ''),
            'payer_id': data.get('PayerParty', ''),
            'amount': data.get('TotalNetAmount', 0),
            'currency': data.get('TransactionCurrency', 'USD'),
            'issue_date': data.get('BillingDocumentDate'),
            'payment_terms': data.get('PaymentTerms'),
            'company_code': data.get('CompanyCode'),
            'sap_id': data.get('BillingDocument'),
            'last_updated': data.get('LastChangeDate'),
        }
    
    def _normalize_vendor_bill(self, data: Dict) -> Dict:
        """Normalize SAP Supplier Invoice."""
        return {
            'bill_number': data.get('SupplierInvoice', ''),
            'fiscal_year': data.get('FiscalYear', ''),
            'vendor_id': data.get('InvoicingParty', ''),
            'amount': data.get('InvoiceGrossAmount', 0),
            'currency': data.get('DocumentCurrency', 'USD'),
            'issue_date': data.get('DocumentDate'),
            'posting_date': data.get('PostingDate'),
            'due_date': data.get('DueCalculationBaseDate'),
            'payment_terms': data.get('PaymentTerms'),
            'company_code': data.get('CompanyCode'),
            'sap_id': f"{data.get('SupplierInvoice')}_{data.get('FiscalYear')}",
        }
    
    def _normalize_bank_statement(self, data: Dict) -> Dict:
        """Normalize SAP Bank Statement."""
        return {
            'statement_id': data.get('BankStatement', ''),
            'house_bank': data.get('HouseBank', ''),
            'account': data.get('HouseBankAccount', ''),
            'statement_date': data.get('BankStatementDate'),
            'opening_balance': data.get('OpeningBalanceAmount', 0),
            'closing_balance': data.get('ClosingBalanceAmount', 0),
            'currency': data.get('Currency', 'USD'),
            'company_code': data.get('CompanyCode'),
            'sap_id': data.get('BankStatement'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        sap_id = data.get('sap_id', '')
        company = data.get('company_code', '')
        components = [f'sap_{record_type}', str(company), str(sap_id)]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"




