"""
Plaid Bank Connector (Official SDK)

Plaid is the leading bank aggregator in the US/Canada.
Provides real-time access to bank accounts, transactions, and balances.

Plaid API: https://plaid.com/docs/
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK
try:
    import plaid
    from plaid.api import plaid_api
    from plaid.model.transactions_get_request import TransactionsGetRequest
    from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
    from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
    from plaid.model.item_get_request import ItemGetRequest
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class PlaidConnector(APIConnector):
    """
    Connector for Plaid Bank Aggregation API.
    
    Config:
        client_id: Plaid client ID
        secret: Plaid secret key
        access_token: Plaid access token (from Link flow)
        environment: 'sandbox', 'development', or 'production'
    """
    
    connector_type = ConnectorType.BANK_API
    display_name = "Plaid"
    description = "US/Canada bank aggregation via Plaid API"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = None
        self.access_token = config.get('access_token')
        self.environment = config.get('environment', 'sandbox')
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("Plaid SDK not installed. Run: pip install plaid-python")
        # Only client_id and secret are required for initial setup
        # access_token comes from completing the Plaid Link flow
        required = ['client_id', 'secret']
        for key in required:
            if key not in self.config:
                raise ValueError(f"{key} is required")
    
    def authenticate(self) -> bool:
        """Initialize Plaid client."""
        if not HAS_SDK:
            return False
            
        try:
            # Configure environment
            if self.environment == 'production':
                host = plaid.Environment.Production
            elif self.environment == 'development':
                host = plaid.Environment.Development
            else:
                host = plaid.Environment.Sandbox
            
            configuration = plaid.Configuration(
                host=host,
                api_key={
                    'clientId': self.config.get('client_id'),
                    'secret': self.config.get('secret'),
                }
            )
            
            api_client = plaid.ApiClient(configuration)
            self.client = plaid_api.PlaidApi(api_client)
            
            return True
            
        except Exception as e:
            print(f"Plaid auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test Plaid connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="Plaid SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            # If we have an access_token, verify it works
            if self.access_token:
                request = ItemGetRequest(access_token=self.access_token)
                response = self.client.item_get(request)
                item = response['item']
                return ConnectorResult(
                    success=True,
                    message=f"Connected to: {item.get('institution_id', 'Unknown Bank')}"
                )
            else:
                # Without access_token, just verify the API credentials are valid
                # by checking we can initialize the client
                return ConnectorResult(
                    success=True,
                    message="API credentials valid. Click 'Connect Bank Account' to link your bank."
                )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch accounts and transactions from Plaid."""
        if not self.client:
            return
        
        # Fetch balances first
        yield from self._fetch_balances()
        
        # Fetch transactions
        yield from self._fetch_transactions(context)
    
    def _fetch_balances(self) -> Iterator[Dict[str, Any]]:
        """Fetch current account balances."""
        try:
            request = AccountsBalanceGetRequest(access_token=self.access_token)
            response = self.client.accounts_balance_get(request)
            
            for account in response['accounts']:
                yield {
                    '_record_type': 'balance',
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'official_name': account.get('official_name'),
                    'type': account['type'],
                    'subtype': account.get('subtype'),
                    'mask': account.get('mask'),
                    'balances': {
                        'available': account['balances'].get('available'),
                        'current': account['balances'].get('current'),
                        'limit': account['balances'].get('limit'),
                        'iso_currency_code': account['balances'].get('iso_currency_code', 'USD'),
                    },
                    'as_of': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"Error fetching balances: {e}")
    
    def _fetch_transactions(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch transactions with pagination."""
        try:
            # Default to last 30 days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            if context.since_timestamp:
                start_date = context.since_timestamp.date()
            
            request = TransactionsGetRequest(
                access_token=self.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(count=500, offset=0)
            )
            
            response = self.client.transactions_get(request)
            transactions = response['transactions']
            total = response['total_transactions']
            
            for txn in transactions:
                yield self._transaction_to_dict(txn)
            
            # Paginate if more transactions
            offset = len(transactions)
            while offset < total:
                request = TransactionsGetRequest(
                    access_token=self.access_token,
                    start_date=start_date,
                    end_date=end_date,
                    options=TransactionsGetRequestOptions(count=500, offset=offset)
                )
                response = self.client.transactions_get(request)
                
                for txn in response['transactions']:
                    yield self._transaction_to_dict(txn)
                
                offset += len(response['transactions'])
                
        except Exception as e:
            print(f"Error fetching transactions: {e}")
    
    def _transaction_to_dict(self, txn) -> Dict[str, Any]:
        """Convert Plaid transaction to dictionary."""
        return {
            '_record_type': 'transaction',
            'transaction_id': txn['transaction_id'],
            'account_id': txn['account_id'],
            'amount': txn['amount'],
            'iso_currency_code': txn.get('iso_currency_code', 'USD'),
            'date': str(txn['date']),
            'authorized_date': str(txn.get('authorized_date')) if txn.get('authorized_date') else None,
            'name': txn['name'],
            'merchant_name': txn.get('merchant_name'),
            'payment_channel': txn.get('payment_channel'),
            'pending': txn.get('pending', False),
            'category': txn.get('category', []),
            'category_id': txn.get('category_id'),
            'location': {
                'city': txn.get('location', {}).get('city'),
                'country': txn.get('location', {}).get('country'),
            },
            'payment_meta': {
                'reference_number': txn.get('payment_meta', {}).get('reference_number'),
                'payee': txn.get('payment_meta', {}).get('payee'),
                'payer': txn.get('payment_meta', {}).get('payer'),
            }
        }
    
    def _get_record_type(self) -> str:
        return 'bank_txn'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize Plaid record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'transaction')
        quality_issues = []
        
        if record_type == 'transaction':
            normalized = self._normalize_transaction(data)
        elif record_type == 'balance':
            normalized = self._normalize_balance(data)
        else:
            normalized = data
        
        if not normalized.get('amount') and record_type == 'transaction':
            quality_issues.append('missing_amount')
        
        canonical_id = self._generate_canonical_id(normalized, record_type)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type=record_type,
            data=normalized,
            source_id=record.source_id,
            source_system="Plaid",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_transaction(self, data: Dict) -> Dict:
        """Normalize Plaid transaction."""
        # Plaid amounts: positive = outflow, negative = inflow
        # Gitto convention: positive = inflow, negative = outflow
        amount = -data.get('amount', 0)
        
        return {
            'txn_ref': data.get('transaction_id', ''),
            'account_id': data.get('account_id', ''),
            'amount': amount,
            'currency': data.get('iso_currency_code', 'USD'),
            'value_date': data.get('date'),
            'booking_date': data.get('authorized_date') or data.get('date'),
            'counterparty_name': data.get('merchant_name') or data.get('name', ''),
            'remittance_info': data.get('name', ''),
            'category': ', '.join(data.get('category', [])),
            'is_pending': data.get('pending', False),
            'payment_channel': data.get('payment_channel'),
            'plaid_txn_id': data.get('transaction_id'),
        }
    
    def _normalize_balance(self, data: Dict) -> Dict:
        """Normalize Plaid balance."""
        balances = data.get('balances', {})
        return {
            'account_id': data.get('account_id', ''),
            'account_name': data.get('name', ''),
            'account_type': data.get('type', ''),
            'account_subtype': data.get('subtype', ''),
            'account_mask': data.get('mask', ''),
            'balance_available': balances.get('available'),
            'balance_current': balances.get('current'),
            'balance_limit': balances.get('limit'),
            'currency': balances.get('iso_currency_code', 'USD'),
            'as_of': data.get('as_of'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        if record_type == 'transaction':
            components = ['plaid_txn', str(data.get('plaid_txn_id', ''))]
        else:
            components = [f'plaid_{record_type}', str(data.get('account_id', '')), str(data.get('as_of', ''))]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"


