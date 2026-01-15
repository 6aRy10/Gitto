"""
Nordigen (GoCardless) Open Banking Connector

Nordigen provides free access to Open Banking APIs in EU/UK.
Now part of GoCardless Bank Account Data API.

API: https://nordigen.com/en/docs/
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK
try:
    from nordigen import NordigenClient
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class NordigenConnector(APIConnector):
    """
    Connector for Nordigen/GoCardless Open Banking API.
    
    Config:
        secret_id: Nordigen Secret ID
        secret_key: Nordigen Secret Key
        requisition_id: ID from completed bank connection flow
    """
    
    connector_type = ConnectorType.BANK_API
    display_name = "Nordigen Open Banking"
    description = "EU/UK Open Banking via Nordigen (GoCardless)"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.requisition_id = config.get('requisition_id')
        self.accounts = []
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("Nordigen SDK not installed. Run: pip install nordigen")
        required = ['secret_id', 'secret_key']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def authenticate(self) -> bool:
        """Initialize Nordigen client and get access token."""
        if not HAS_SDK:
            return False
            
        try:
            self.client = NordigenClient(
                secret_id=self.config.get('secret_id'),
                secret_key=self.config.get('secret_key')
            )
            
            # Generate new access token
            self.client.generate_token()
            
            return True
            
        except Exception as e:
            print(f"Nordigen auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test Nordigen connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="Nordigen SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            # List available institutions to verify API access
            institutions = self.client.institution.get_institutions(country="GB")
            return ConnectorResult(
                success=True,
                message=f"Connected. {len(institutions)} banks available."
            )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def get_available_banks(self, country: str = "GB") -> List[Dict]:
        """Get list of available banks for a country."""
        if not self.client:
            self.authenticate()
        
        try:
            institutions = self.client.institution.get_institutions(country=country)
            return [
                {
                    'id': inst['id'],
                    'name': inst['name'],
                    'logo': inst.get('logo'),
                    'countries': inst.get('countries', [])
                }
                for inst in institutions
            ]
        except Exception as e:
            print(f"Error fetching institutions: {e}")
            return []
    
    def create_requisition(self, institution_id: str, redirect_url: str) -> Dict:
        """
        Create a requisition (bank connection request).
        
        Returns link for user to authorize bank access.
        """
        if not self.client:
            self.authenticate()
        
        try:
            # Create end user agreement
            agreement = self.client.agreement.create_agreement(
                institution_id=institution_id,
                max_historical_days=90,
                access_valid_for_days=90,
                access_scope=["balances", "details", "transactions"]
            )
            
            # Create requisition
            requisition = self.client.requisition.create_requisition(
                redirect=redirect_url,
                institution_id=institution_id,
                agreement=agreement["id"]
            )
            
            return {
                'requisition_id': requisition['id'],
                'link': requisition['link'],
                'status': requisition['status']
            }
        except Exception as e:
            print(f"Error creating requisition: {e}")
            return {}
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch accounts and transactions via Open Banking."""
        if not self.client or not self.requisition_id:
            return
        
        try:
            # Get requisition details
            requisition = self.client.requisition.get_requisition_by_id(
                requisition_id=self.requisition_id
            )
            
            account_ids = requisition.get('accounts', [])
            
            for account_id in account_ids:
                account = self.client.account_api(id=account_id)
                
                # Fetch account details
                yield from self._fetch_account_details(account, account_id)
                
                # Fetch balances
                yield from self._fetch_balances(account, account_id)
                
                # Fetch transactions
                yield from self._fetch_transactions(account, account_id, context)
                
        except Exception as e:
            print(f"Error fetching records: {e}")
    
    def _fetch_account_details(self, account, account_id: str) -> Iterator[Dict[str, Any]]:
        """Fetch account metadata."""
        try:
            details = account.get_details()
            account_data = details.get('account', {})
            
            yield {
                '_record_type': 'account',
                'account_id': account_id,
                'iban': account_data.get('iban'),
                'name': account_data.get('name'),
                'owner_name': account_data.get('ownerName'),
                'currency': account_data.get('currency'),
                'product': account_data.get('product'),
                'cash_account_type': account_data.get('cashAccountType'),
            }
        except Exception as e:
            print(f"Error fetching account details: {e}")
    
    def _fetch_balances(self, account, account_id: str) -> Iterator[Dict[str, Any]]:
        """Fetch account balances."""
        try:
            balances_response = account.get_balances()
            
            for balance in balances_response.get('balances', []):
                yield {
                    '_record_type': 'balance',
                    'account_id': account_id,
                    'balance_type': balance.get('balanceType'),
                    'amount': float(balance.get('balanceAmount', {}).get('amount', 0)),
                    'currency': balance.get('balanceAmount', {}).get('currency', 'EUR'),
                    'reference_date': balance.get('referenceDate'),
                    'as_of': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"Error fetching balances: {e}")
    
    def _fetch_transactions(self, account, account_id: str, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch transactions."""
        try:
            # Default to last 90 days
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            if context.since_timestamp:
                start_date = context.since_timestamp.strftime('%Y-%m-%d')
            
            transactions_response = account.get_transactions(
                date_from=start_date,
                date_to=end_date
            )
            
            # Booked transactions
            for txn in transactions_response.get('transactions', {}).get('booked', []):
                txn['_record_type'] = 'transaction'
                txn['account_id'] = account_id
                txn['status'] = 'booked'
                yield txn
            
            # Pending transactions
            for txn in transactions_response.get('transactions', {}).get('pending', []):
                txn['_record_type'] = 'transaction'
                txn['account_id'] = account_id
                txn['status'] = 'pending'
                yield txn
                
        except Exception as e:
            print(f"Error fetching transactions: {e}")
    
    def _get_record_type(self) -> str:
        return 'bank_txn'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize Nordigen record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'transaction')
        quality_issues = []
        
        if record_type == 'transaction':
            normalized = self._normalize_transaction(data)
        elif record_type == 'balance':
            normalized = self._normalize_balance(data)
        elif record_type == 'account':
            normalized = data
        else:
            normalized = data
        
        if record_type == 'transaction' and not normalized.get('amount'):
            quality_issues.append('missing_amount')
        
        canonical_id = self._generate_canonical_id(normalized, record_type)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type=record_type,
            data=normalized,
            source_id=record.source_id,
            source_system="Nordigen",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_transaction(self, data: Dict) -> Dict:
        """Normalize Open Banking transaction to Gitto schema."""
        # Extract amount (can be nested in transactionAmount)
        txn_amount = data.get('transactionAmount', {})
        amount = float(txn_amount.get('amount', 0)) if txn_amount else 0
        currency = txn_amount.get('currency', 'EUR')
        
        # Get counterparty info
        creditor = data.get('creditorName', '')
        debtor = data.get('debtorName', '')
        counterparty = creditor or debtor
        
        return {
            'txn_ref': data.get('transactionId') or data.get('internalTransactionId', ''),
            'account_id': data.get('account_id', ''),
            'amount': amount,
            'currency': currency,
            'value_date': data.get('valueDate') or data.get('bookingDate'),
            'booking_date': data.get('bookingDate'),
            'counterparty_name': counterparty,
            'counterparty_iban': data.get('creditorAccount', {}).get('iban') or data.get('debtorAccount', {}).get('iban'),
            'remittance_info': data.get('remittanceInformationUnstructured', '') or 
                              ' '.join(data.get('remittanceInformationUnstructuredArray', [])),
            'end_to_end_id': data.get('endToEndId'),
            'is_pending': data.get('status') == 'pending',
            'bank_txn_code': data.get('bankTransactionCode'),
            'nordigen_txn_id': data.get('transactionId'),
        }
    
    def _normalize_balance(self, data: Dict) -> Dict:
        """Normalize Open Banking balance."""
        return {
            'account_id': data.get('account_id', ''),
            'balance_type': data.get('balance_type', ''),
            'balance_amount': data.get('amount'),
            'currency': data.get('currency', 'EUR'),
            'reference_date': data.get('reference_date'),
            'as_of': data.get('as_of'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        if record_type == 'transaction':
            components = [
                'nordigen_txn',
                str(data.get('account_id', '')),
                str(data.get('nordigen_txn_id') or data.get('txn_ref', '')),
                str(data.get('value_date', '')),
                str(data.get('amount', ''))
            ]
        else:
            components = [
                f'nordigen_{record_type}',
                str(data.get('account_id', '')),
                str(data.get('as_of', ''))
            ]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"




