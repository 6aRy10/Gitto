"""
MT940 Bank Statement Connector

SWIFT MT940 is the international standard for bank statement files.
This connector parses MT940 format and normalizes to Gitto's bank transaction schema.

MT940 Structure:
- :20: Transaction Reference
- :25: Account ID
- :28C: Statement Number
- :60F/60M: Opening Balance (First/Middle)
- :61: Transaction Line
- :86: Transaction Details
- :62F/62M: Closing Balance (Final/Middle)
"""

import re
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional
from decimal import Decimal
from .base import (
    FileConnector, ConnectorType, ConnectorResult, 
    SyncContext, ExtractedRecord, NormalizedRecord
)


class MT940Connector(FileConnector):
    """
    Connector for SWIFT MT940 bank statement files.
    
    Config:
        file_content: Raw MT940 file bytes
        bank_name: Name of the bank (for lineage)
        entity_id: Entity this account belongs to
    """
    
    connector_type = ConnectorType.BANK_MT940
    display_name = "MT940 Bank Statement"
    description = "SWIFT MT940 format bank statement files"
    
    def _validate_config(self) -> None:
        """Validate required config."""
        if 'file_content' not in self.config:
            raise ValueError("file_content is required")
    
    def test_connection(self) -> ConnectorResult:
        """Test that file can be parsed."""
        try:
            content = self.config.get('file_content', b'')
            if not content:
                return ConnectorResult(success=False, message="No file content provided")
            
            # Try to parse first statement
            statements = list(self._parse_statements(content))
            if not statements:
                return ConnectorResult(success=False, message="No valid MT940 statements found")
            
            return ConnectorResult(
                success=True, 
                message=f"Found {len(statements)} statement(s)"
            )
        except Exception as e:
            return ConnectorResult(success=False, message=f"Parse error: {str(e)}")
    
    def parse_file(self, content: bytes) -> Iterator[ExtractedRecord]:
        """Parse MT940 file and yield transactions."""
        # Decode content
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        
        for statement in self._parse_statements(content):
            account_id = statement.get('account_id', '')
            statement_date = statement.get('statement_date')
            
            for txn in statement.get('transactions', []):
                txn['account_id'] = account_id
                txn['statement_date'] = statement_date
                txn['opening_balance'] = statement.get('opening_balance')
                txn['closing_balance'] = statement.get('closing_balance')
                
                yield ExtractedRecord(
                    source_id=txn.get('reference', f"{account_id}_{txn.get('value_date')}_{txn.get('amount')}"),
                    record_type='bank_txn',
                    data=txn
                )
    
    def _parse_statements(self, content: bytes) -> Iterator[Dict[str, Any]]:
        """Parse MT940 content into statement dictionaries."""
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        
        # Split into individual statements (each starts with :20:)
        statement_blocks = re.split(r'(?=:20:)', text)
        
        for block in statement_blocks:
            if not block.strip() or ':20:' not in block:
                continue
            
            statement = self._parse_statement_block(block)
            if statement:
                yield statement
    
    def _parse_statement_block(self, block: str) -> Optional[Dict[str, Any]]:
        """Parse a single MT940 statement block."""
        statement = {
            'transactions': [],
            'raw_block': block
        }
        
        # Extract fields using regex
        patterns = {
            'reference': r':20:(.+?)(?:\r?\n|$)',
            'account_id': r':25:(.+?)(?:\r?\n|$)',
            'statement_number': r':28C:(.+?)(?:\r?\n|$)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, block)
            if match:
                statement[field] = match.group(1).strip()
        
        # Parse opening balance (:60F: or :60M:)
        opening_match = re.search(r':60[FM]:([CD])(\d{6})([A-Z]{3})([\d,\.]+)', block)
        if opening_match:
            dc, date_str, currency, amount_str = opening_match.groups()
            statement['opening_balance'] = {
                'debit_credit': dc,
                'date': self._parse_date(date_str),
                'currency': currency,
                'amount': self._parse_amount(amount_str, dc)
            }
        
        # Parse closing balance (:62F: or :62M:)
        closing_match = re.search(r':62[FM]:([CD])(\d{6})([A-Z]{3})([\d,\.]+)', block)
        if closing_match:
            dc, date_str, currency, amount_str = closing_match.groups()
            statement['closing_balance'] = {
                'debit_credit': dc,
                'date': self._parse_date(date_str),
                'currency': currency,
                'amount': self._parse_amount(amount_str, dc)
            }
            statement['statement_date'] = self._parse_date(date_str)
        
        # Parse transactions (:61: lines followed by :86: details)
        txn_pattern = r':61:(\d{6})(\d{4})?([CD]R?)([A-Z]?)([\d,\.]+)([A-Z]{4})(.{0,16})?(?:\r?\n:86:(.+?))?(?=(?:\r?\n:6[12])|$)'
        
        for match in re.finditer(txn_pattern, block, re.DOTALL):
            groups = match.groups()
            value_date_str = groups[0]
            booking_date_str = groups[1]
            dc = groups[2]
            funds_code = groups[3]
            amount_str = groups[4]
            txn_type = groups[5]
            reference = groups[6] if groups[6] else ''
            details = groups[7] if groups[7] else ''
            
            txn = {
                'value_date': self._parse_date(value_date_str),
                'booking_date': self._parse_date(booking_date_str) if booking_date_str else self._parse_date(value_date_str),
                'debit_credit': 'D' if 'D' in dc else 'C',
                'is_reversal': 'R' in dc,
                'funds_code': funds_code,
                'amount': self._parse_amount(amount_str, dc),
                'transaction_type': txn_type,
                'reference': reference.strip(),
                'details': self._clean_details(details),
                'currency': statement.get('opening_balance', {}).get('currency', 'EUR')
            }
            
            # Extract additional info from details
            txn.update(self._parse_details(txn['details']))
            
            statement['transactions'].append(txn)
        
        return statement if statement.get('account_id') else None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse YYMMDD date format."""
        if not date_str or len(date_str) < 6:
            return None
        try:
            year = int(date_str[0:2])
            year = 2000 + year if year < 50 else 1900 + year
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            return f"{year}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            return None
    
    def _parse_amount(self, amount_str: str, dc: str) -> float:
        """Parse amount string and apply debit/credit sign."""
        try:
            # Replace comma with decimal point
            amount = float(amount_str.replace(',', '.'))
            # Debits are negative (outflows)
            if 'D' in dc:
                amount = -amount
            return amount
        except ValueError:
            return 0.0
    
    def _clean_details(self, details: str) -> str:
        """Clean transaction details text."""
        if not details:
            return ''
        # Remove newlines and excess whitespace
        return ' '.join(details.split())
    
    def _parse_details(self, details: str) -> Dict[str, str]:
        """Extract structured info from :86: details field."""
        result = {}
        
        # Common structured formats in :86:
        # /ORDP/ - Ordering Party
        # /BENM/ - Beneficiary
        # /REMI/ - Remittance Information
        # /SVCLVL/ - Service Level
        # /EREF/ - End-to-end Reference
        
        patterns = {
            'ordering_party': r'/ORDP/([^/]+)',
            'beneficiary': r'/BENM/([^/]+)',
            'remittance_info': r'/REMI/([^/]+)',
            'end_to_end_ref': r'/EREF/([^/]+)',
            'mandate_ref': r'/MARF/([^/]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, details)
            if match:
                result[field] = match.group(1).strip()
        
        # Also store raw for fallback parsing
        result['raw_details'] = details
        
        return result
    
    def normalize(self, record: ExtractedRecord, context: SyncContext) -> NormalizedRecord:
        """Normalize MT940 transaction to Gitto's canonical schema."""
        data = record.data
        quality_issues = []
        
        # Map to canonical bank transaction fields
        normalized_data = {
            # Core fields
            'txn_ref': data.get('reference', '') or data.get('end_to_end_ref', ''),
            'account_id': data.get('account_id', ''),
            'value_date': data.get('value_date'),
            'booking_date': data.get('booking_date'),
            'amount': data.get('amount', 0.0),
            'currency': data.get('currency', 'EUR'),
            
            # Counterparty
            'counterparty_name': data.get('beneficiary') or data.get('ordering_party', ''),
            
            # Remittance info (for matching)
            'remittance_info': data.get('remittance_info') or data.get('raw_details', ''),
            
            # MT940-specific
            'transaction_type_code': data.get('transaction_type', ''),
            'is_reversal': data.get('is_reversal', False),
            
            # Balance context
            'statement_opening_balance': data.get('opening_balance', {}).get('amount'),
            'statement_closing_balance': data.get('closing_balance', {}).get('amount'),
        }
        
        # Apply field mappings from context
        if context.field_mappings:
            for source_field, canonical_field in context.field_mappings.items():
                if source_field in data:
                    normalized_data[canonical_field] = data[source_field]
        
        # Data quality checks
        if not normalized_data.get('value_date'):
            quality_issues.append("missing_value_date")
        if not normalized_data.get('amount'):
            quality_issues.append("zero_or_missing_amount")
        if not normalized_data.get('txn_ref'):
            quality_issues.append("missing_transaction_reference")
        
        # Generate canonical ID
        canonical_id = self._generate_canonical_id(normalized_data)
        
        return NormalizedRecord(
            canonical_id=canonical_id,
            record_type='bank_txn',
            data=normalized_data,
            source_id=record.source_id,
            source_system=f"MT940:{self.config.get('bank_name', 'unknown')}",
            source_checksum=record.compute_checksum(),
            quality_issues=quality_issues,
            is_complete=len(quality_issues) == 0
        )
    
    def _generate_canonical_id(self, data: Dict[str, Any]) -> str:
        """Generate stable canonical ID for bank transaction."""
        import hashlib
        
        # Components that make a transaction unique
        components = [
            str(data.get('account_id', '')),
            str(data.get('value_date', '')),
            str(data.get('amount', '')),
            str(data.get('txn_ref', '')),
            str(data.get('remittance_info', ''))[:50]  # First 50 chars
        ]
        
        content = '|'.join(components)
        return f"bank_txn:{hashlib.sha256(content.encode()).hexdigest()[:16]}"




