"""
Stripe Payments Connector (Official SDK)

Stripe is a leading payment processor. This connector fetches:
- Payment intents and charges
- Payouts and transfers  
- Balance and balance transactions
- Invoices and subscriptions

API: https://stripe.com/docs/api
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional
from .base import (
    APIConnector, ConnectorType, ConnectorResult,
    SyncContext, ExtractedRecord, NormalizedRecord
)

# Official SDK
try:
    import stripe
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class StripeConnector(APIConnector):
    """
    Connector for Stripe Payments API.
    
    Config:
        api_key: Stripe secret API key (sk_live_xxx or sk_test_xxx)
        account_id: Connected account ID (optional, for platforms)
    """
    
    connector_type = ConnectorType.PAYMENTS
    display_name = "Stripe"
    description = "Payment processing data via Stripe API"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_id = config.get('account_id')
    
    def _validate_config(self) -> None:
        if not HAS_SDK:
            raise ImportError("Stripe SDK not installed. Run: pip install stripe")
        if 'api_key' not in self.config:
            raise ValueError("api_key is required")
    
    def authenticate(self) -> bool:
        """Set up Stripe API key."""
        if not HAS_SDK:
            return False
            
        try:
            stripe.api_key = self.config.get('api_key')
            return True
        except Exception as e:
            print(f"Stripe auth error: {e}")
            return False
    
    def test_connection(self) -> ConnectorResult:
        """Test Stripe connection."""
        if not HAS_SDK:
            return ConnectorResult(success=False, message="Stripe SDK not installed")
            
        if not self.authenticate():
            return ConnectorResult(success=False, message="Authentication failed")
        
        try:
            account = stripe.Account.retrieve()
            return ConnectorResult(
                success=True,
                message=f"Connected to: {account.get('business_profile', {}).get('name', account['id'])}"
            )
        except stripe.error.AuthenticationError:
            return ConnectorResult(success=False, message="Invalid API key")
        except Exception as e:
            return ConnectorResult(success=False, message=f"Connection test failed: {str(e)}")
    
    def fetch_records(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch payment data from Stripe."""
        if not stripe.api_key:
            return
        
        # Current balance
        yield from self._fetch_balance()
        
        # Balance transactions (money movements)
        yield from self._fetch_balance_transactions(context)
        
        # Payouts (to bank account)
        yield from self._fetch_payouts(context)
        
        # Charges (incoming payments)
        yield from self._fetch_charges(context)
    
    def _fetch_balance(self) -> Iterator[Dict[str, Any]]:
        """Fetch current Stripe balance."""
        try:
            balance = stripe.Balance.retrieve()
            
            for available in balance.get('available', []):
                yield {
                    '_record_type': 'balance',
                    'balance_type': 'available',
                    'amount': available['amount'] / 100,  # Convert from cents
                    'currency': available['currency'].upper(),
                    'source_types': available.get('source_types', {}),
                    'as_of': datetime.utcnow().isoformat()
                }
            
            for pending in balance.get('pending', []):
                yield {
                    '_record_type': 'balance',
                    'balance_type': 'pending',
                    'amount': pending['amount'] / 100,
                    'currency': pending['currency'].upper(),
                    'source_types': pending.get('source_types', {}),
                    'as_of': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"Error fetching balance: {e}")
    
    def _fetch_balance_transactions(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch balance transactions with pagination."""
        try:
            params = {'limit': 100}
            
            if context.since_timestamp:
                params['created'] = {'gte': int(context.since_timestamp.timestamp())}
            
            transactions = stripe.BalanceTransaction.list(**params)
            
            for txn in transactions.auto_paging_iter():
                yield {
                    '_record_type': 'balance_txn',
                    'id': txn['id'],
                    'amount': txn['amount'] / 100,
                    'net': txn['net'] / 100,
                    'fee': txn['fee'] / 100,
                    'currency': txn['currency'].upper(),
                    'type': txn['type'],
                    'description': txn.get('description'),
                    'source': txn.get('source'),
                    'created': datetime.fromtimestamp(txn['created']).isoformat(),
                    'available_on': datetime.fromtimestamp(txn['available_on']).isoformat(),
                    'status': txn['status'],
                    'reporting_category': txn.get('reporting_category'),
                }
        except Exception as e:
            print(f"Error fetching balance transactions: {e}")
    
    def _fetch_payouts(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch payouts to bank account."""
        try:
            params = {'limit': 100}
            
            if context.since_timestamp:
                params['created'] = {'gte': int(context.since_timestamp.timestamp())}
            
            payouts = stripe.Payout.list(**params)
            
            for payout in payouts.auto_paging_iter():
                yield {
                    '_record_type': 'payout',
                    'id': payout['id'],
                    'amount': payout['amount'] / 100,
                    'currency': payout['currency'].upper(),
                    'status': payout['status'],
                    'type': payout['type'],
                    'method': payout['method'],
                    'description': payout.get('description'),
                    'destination': payout.get('destination'),
                    'arrival_date': datetime.fromtimestamp(payout['arrival_date']).isoformat() if payout.get('arrival_date') else None,
                    'created': datetime.fromtimestamp(payout['created']).isoformat(),
                    'failure_code': payout.get('failure_code'),
                    'failure_message': payout.get('failure_message'),
                }
        except Exception as e:
            print(f"Error fetching payouts: {e}")
    
    def _fetch_charges(self, context: SyncContext) -> Iterator[Dict[str, Any]]:
        """Fetch charges (incoming payments)."""
        try:
            params = {'limit': 100}
            
            if context.since_timestamp:
                params['created'] = {'gte': int(context.since_timestamp.timestamp())}
            
            charges = stripe.Charge.list(**params)
            
            for charge in charges.auto_paging_iter():
                yield {
                    '_record_type': 'charge',
                    'id': charge['id'],
                    'amount': charge['amount'] / 100,
                    'amount_refunded': charge['amount_refunded'] / 100,
                    'currency': charge['currency'].upper(),
                    'status': charge['status'],
                    'paid': charge['paid'],
                    'refunded': charge['refunded'],
                    'captured': charge['captured'],
                    'description': charge.get('description'),
                    'customer': charge.get('customer'),
                    'invoice': charge.get('invoice'),
                    'payment_intent': charge.get('payment_intent'),
                    'payment_method': charge.get('payment_method'),
                    'receipt_email': charge.get('receipt_email'),
                    'created': datetime.fromtimestamp(charge['created']).isoformat(),
                    'billing_details': charge.get('billing_details', {}),
                    'outcome': {
                        'network_status': charge.get('outcome', {}).get('network_status'),
                        'risk_level': charge.get('outcome', {}).get('risk_level'),
                    },
                }
        except Exception as e:
            print(f"Error fetching charges: {e}")
    
    def _get_record_type(self) -> str:
        return 'payment'
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize Stripe record to Gitto's canonical schema."""
        data = record.data
        record_type = data.get('_record_type', 'charge')
        quality_issues = []
        
        if record_type == 'charge':
            normalized = self._normalize_charge(data)
        elif record_type == 'payout':
            normalized = self._normalize_payout(data)
        elif record_type == 'balance_txn':
            normalized = self._normalize_balance_txn(data)
        elif record_type == 'balance':
            normalized = data
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
            source_system="Stripe",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _normalize_charge(self, data: Dict) -> Dict:
        """Normalize Stripe charge to inflow."""
        billing = data.get('billing_details', {})
        return {
            'txn_ref': data.get('id', ''),
            'amount': data.get('amount', 0),
            'currency': data.get('currency', 'USD'),
            'txn_date': data.get('created'),
            'counterparty_name': billing.get('name', ''),
            'counterparty_email': billing.get('email') or data.get('receipt_email', ''),
            'description': data.get('description', ''),
            'status': data.get('status'),
            'is_paid': data.get('paid', False),
            'is_refunded': data.get('refunded', False),
            'refund_amount': data.get('amount_refunded', 0),
            'payment_method': data.get('payment_method'),
            'invoice_ref': data.get('invoice'),
            'stripe_id': data.get('id'),
        }
    
    def _normalize_payout(self, data: Dict) -> Dict:
        """Normalize Stripe payout to outflow."""
        return {
            'txn_ref': data.get('id', ''),
            'amount': -abs(data.get('amount', 0)),  # Negative for outflow
            'currency': data.get('currency', 'USD'),
            'txn_date': data.get('created'),
            'arrival_date': data.get('arrival_date'),
            'description': data.get('description', 'Stripe Payout'),
            'status': data.get('status'),
            'payout_method': data.get('method'),
            'payout_type': data.get('type'),
            'destination_account': data.get('destination'),
            'failure_reason': data.get('failure_message'),
            'stripe_id': data.get('id'),
        }
    
    def _normalize_balance_txn(self, data: Dict) -> Dict:
        """Normalize balance transaction."""
        return {
            'txn_ref': data.get('id', ''),
            'amount': data.get('amount', 0),
            'net_amount': data.get('net', 0),
            'fee_amount': data.get('fee', 0),
            'currency': data.get('currency', 'USD'),
            'txn_date': data.get('created'),
            'available_date': data.get('available_on'),
            'txn_type': data.get('type'),
            'description': data.get('description', ''),
            'status': data.get('status'),
            'reporting_category': data.get('reporting_category'),
            'source_ref': data.get('source'),
            'stripe_id': data.get('id'),
        }
    
    def _generate_canonical_id(self, data: Dict, record_type: str) -> str:
        """Generate stable canonical ID."""
        import hashlib
        
        stripe_id = data.get('stripe_id') or data.get('id', '')
        components = [f'stripe_{record_type}', str(stripe_id)]
        
        content = '|'.join(components)
        return f"{record_type}:{hashlib.sha256(content.encode()).hexdigest()[:16]}"




