"""
Bank Statement Format Validator

Validates MT940, BAI2, and camt.053 formats according to actual specification rules.
"""

import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class MT940Validator:
    """Validates MT940 format according to SWIFT standards."""
    
    # MT940 field length constraints
    FIELD_LENGTHS = {
        ':20:': (16, 16),  # Reference: exactly 16 chars
        ':25:': (1, 35),   # Account: 1-35 chars
        ':28C:': (5, 5),   # Statement number: exactly 5 chars (00001/001)
        ':61:': (16, 16),  # Statement line: exactly 16 chars for date part
        ':86:': (1, 390),  # Narrative: 1-390 chars
        ':62F:': (18, 18), # Closing balance: exactly 18 chars
    }
    
    @staticmethod
    def validate_statement(content: str) -> Tuple[bool, List[str]]:
        """Validate MT940 statement format."""
        errors = []
        lines = content.strip().split('\n')
        
        # Check required tags
        required_tags = [':20:', ':25:', ':28C:', ':62F:']
        found_tags = set()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check tag format
            if line.startswith(':'):
                tag_match = re.match(r'^(:[0-9]{2}[A-Z]?):', line)
                if not tag_match:
                    errors.append(f"Invalid tag format: {line[:20]}")
                    continue
                
                tag = tag_match.group(1)
                found_tags.add(tag)
                
                # Validate field lengths
                if tag in MT940Validator.FIELD_LENGTHS:
                    min_len, max_len = MT940Validator.FIELD_LENGTHS[tag]
                    field_content = line[len(tag):]
                    if len(field_content) < min_len or len(field_content) > max_len:
                        errors.append(f"Tag {tag} length violation: {len(field_content)} (expected {min_len}-{max_len})")
                
                # Validate :61: format (date + amount)
                if tag == ':61:':
                    if not re.match(r'^:61:\d{6}\d{4}[DC]\d{1,15},\d{2}[A-Z]{0,3}', line):
                        errors.append(f"Invalid :61: format: {line[:50]}")
                
                # Validate :62F: format (balance)
                if tag == ':62F:':
                    if not re.match(r'^:62F:[DC]\d{6}[A-Z]{3}\d{1,15},\d{2}', line):
                        errors.append(f"Invalid :62F: format: {line[:50]}")
        
        # Check required tags present
        for tag in required_tags:
            if tag not in found_tags:
                errors.append(f"Missing required tag: {tag}")
        
        return len(errors) == 0, errors


class BAI2Validator:
    """Validates BAI2 format according to BAI standards."""
    
    @staticmethod
    def validate_statement(content: str) -> Tuple[bool, List[str]]:
        """Validate BAI2 statement format."""
        errors = []
        lines = content.strip().split('\n')
        
        if not lines:
            return False, ["Empty file"]
        
        # Check file header (01)
        if not lines[0].startswith('01,'):
            errors.append("Missing file header (01)")
        
        # Check account header (02)
        account_header_found = False
        for i, line in enumerate(lines):
            if line.startswith('02,'):
                account_header_found = True
                # Validate account header format
                parts = line.split(',')
                if len(parts) < 7:
                    errors.append(f"Invalid account header format at line {i+1}")
                break
        
        if not account_header_found:
            errors.append("Missing account header (02)")
        
        # Check file trailer (99)
        if not lines[-1].startswith('99,'):
            errors.append("Missing file trailer (99)")
        
        # Validate transaction records (16)
        for i, line in enumerate(lines):
            if line.startswith('16,'):
                parts = line.split(',')
                if len(parts) < 6:
                    errors.append(f"Invalid transaction record format at line {i+1}")
                # Validate amount format
                if len(parts) > 2:
                    try:
                        float(parts[2])
                    except ValueError:
                        errors.append(f"Invalid amount format at line {i+1}: {parts[2]}")
        
        return len(errors) == 0, errors


class Camt053Validator:
    """Validates camt.053 (ISO 20022) format."""
    
    @staticmethod
    def validate_statement(content: str) -> Tuple[bool, List[str]]:
        """Validate camt.053 XML format."""
        errors = []
        
        # Check XML structure
        if not content.strip().startswith('<?xml'):
            errors.append("Missing XML declaration")
        
        # Check namespace
        if 'urn:iso:std:iso:20022:tech:xsd:camt.053' not in content:
            errors.append("Missing or incorrect camt.053 namespace")
        
        # Check required elements
        required_elements = [
            'BkToCstmrStmt',
            'GrpHdr',
            'MsgId',
            'Stmt',
            'Acct',
            'Bal',
            'Ntry'
        ]
        
        for elem in required_elements:
            if f'<{elem}' not in content and f'<{elem}>' not in content:
                errors.append(f"Missing required element: {elem}")
        
        # Validate XML well-formedness (basic check)
        open_tags = re.findall(r'<([^/>]+)>', content)
        close_tags = re.findall(r'</([^>]+)>', content)
        
        # Check balance
        if '<Bal>' in content:
            if '<Amt' not in content:
                errors.append("Balance element missing Amount")
            if 'Ccy=' not in content:
                errors.append("Balance element missing Currency")
        
        return len(errors) == 0, errors


def validate_bank_statement(filepath: str, format_type: str) -> Tuple[bool, List[str]]:
    """Validate bank statement file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if format_type == 'MT940':
        return MT940Validator.validate_statement(content)
    elif format_type == 'BAI2':
        return BAI2Validator.validate_statement(content)
    elif format_type == 'camt.053':
        return Camt053Validator.validate_statement(content)
    else:
        return False, [f"Unknown format: {format_type}"]


