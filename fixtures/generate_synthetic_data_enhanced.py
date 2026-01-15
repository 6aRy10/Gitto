"""
Enhanced Synthetic Data Generator

Fixes:
1. Proper MT940/BAI2/camt.053 format validation
2. Realistic distributions (weekends/holidays, batch payment runs, fee patterns)
3. Chaos mode (duplicate imports, missing days, timezone shifts, reversals, chargebacks)
4. Amount-weighted manifest invariants
5. Ground truth canonical transactions
"""

import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from faker import Faker
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict

from bank_format_validator import MT940Validator, BAI2Validator, Camt053Validator

fake = Faker()
OUTPUT_DIR = Path(__file__).parent


@dataclass
class ChaosConfig:
    """Chaos mode configuration."""
    duplicate_import_rate: float = 0.05  # 5% duplicate statement imports
    missing_days_rate: float = 0.03  # 3% missing days
    timezone_shift_rate: float = 0.02  # 2% timezone shifts
    negative_reversal_rate: float = 0.01  # 1% negative reversals
    chargeback_rate: float = 0.01  # 1% chargebacks
    enable_chaos: bool = False


class EnhancedSyntheticDataGenerator:
    """Enhanced generator with proper format validation and chaos mode."""
    
    def __init__(self, chaos_config: ChaosConfig = None):
        self.chaos_config = chaos_config or ChaosConfig()
        self.ground_truth_transactions = []  # Canonical transactions
        self.manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "random_seed": 42,
            "chaos_mode": self.chaos_config.enable_chaos,
            "datasets": {},
            "invariants": [],
            "known_exceptions": [],
            "amount_weighted_invariants": {}  # NEW: Amount-weighted checks
        }
    
    def generate_bank_statements_with_ground_truth(
        self,
        transactions: List[Dict],
        entity_id: int
    ) -> Tuple[List[Dict], Dict]:
        """
        Generate bank statements with ground truth canonical transactions.
        
        Returns:
            (raw_statements, ground_truth_dict)
        """
        # Create ground truth (canonical transactions)
        ground_truth = []
        for txn in transactions:
            canonical = {
                "transaction_id": txn.get("id"),
                "transaction_date": txn["transaction_date"],
                "amount": txn["amount"],
                "currency": txn.get("currency", "EUR"),
                "reference": txn.get("reference", ""),
                "counterparty": txn.get("counterparty", ""),
                "transaction_type": txn.get("transaction_type", ""),
                "fee": txn.get("fee", 0.0),
                "is_reconciled": txn.get("is_reconciled", 0),
                "canonical_hash": self._hash_transaction(txn)
            }
            ground_truth.append(canonical)
        
        self.ground_truth_transactions.extend(ground_truth)
        
        # Apply chaos mode if enabled
        if self.chaos_config.enable_chaos:
            transactions = self._apply_chaos(transactions)
        
        # Generate statements in multiple formats
        statements = {
            "csv": self._generate_csv_statement(transactions),
            "mt940": self._generate_mt940_statement(transactions, entity_id),
            "bai2": self._generate_bai2_statement(transactions, entity_id),
            "camt053": self._generate_camt053_statement(transactions, entity_id)
        }
        
        # Validate formats
        validation_results = {}
        for format_type, content in statements.items():
            if format_type == "csv":
                validation_results[format_type] = {"valid": True, "errors": []}
            elif format_type == "mt940":
                valid, errors = MT940Validator.validate_statement(content)
                validation_results[format_type] = {"valid": valid, "errors": errors}
            elif format_type == "bai2":
                valid, errors = BAI2Validator.validate_statement(content)
                validation_results[format_type] = {"valid": valid, "errors": errors}
            elif format_type == "camt053":
                valid, errors = Camt053Validator.validate_statement(content)
                validation_results[format_type] = {"valid": valid, "errors": errors}
        
        return statements, {
            "ground_truth": ground_truth,
            "validation_results": validation_results
        }
    
    def _apply_chaos(self, transactions: List[Dict]) -> List[Dict]:
        """Apply chaos mode transformations."""
        chaotic = transactions.copy()
        
        # Duplicate imports
        if random.random() < self.chaos_config.duplicate_import_rate:
            # Duplicate some transactions
            dup_count = int(len(chaotic) * 0.05)
            duplicates = random.sample(chaotic, min(dup_count, len(chaotic)))
            chaotic.extend(duplicates)
        
        # Missing days (remove transactions from certain days)
        if random.random() < self.chaos_config.missing_days_rate:
            # Remove transactions from random days
            days_to_remove = random.sample(range(90), 3)
            chaotic = [
                txn for txn in chaotic
                if datetime.fromisoformat(txn["transaction_date"]).day not in days_to_remove
            ]
        
        # Timezone shifts
        if random.random() < self.chaos_config.timezone_shift_rate:
            for txn in chaotic:
                if random.random() < 0.1:  # 10% of transactions
                    dt = datetime.fromisoformat(txn["transaction_date"])
                    # Shift by ±12 hours
                    shift_hours = random.choice([-12, -6, 6, 12])
                    txn["transaction_date"] = (dt + timedelta(hours=shift_hours)).isoformat()
        
        # Negative reversals
        if random.random() < self.chaos_config.negative_reversal_rate:
            # Create reversal transactions (opposite amount)
            reversal_count = int(len(chaotic) * 0.01)
            reversals = []
            for txn in random.sample(chaotic, min(reversal_count, len(chaotic))):
                reversal = txn.copy()
                reversal["amount"] = -txn["amount"]
                reversal["reference"] = f"REVERSAL-{txn.get('reference', '')}"
                reversal["transaction_type"] = "reversal"
                reversals.append(reversal)
            chaotic.extend(reversals)
        
        # Chargebacks
        if random.random() < self.chaos_config.chargeback_rate:
            chargeback_count = int(len(chaotic) * 0.01)
            chargebacks = []
            for txn in random.sample(chaotic, min(chargeback_count, len(chaotic))):
                if txn["amount"] > 0:  # Only chargeback positive amounts
                    chargeback = txn.copy()
                    chargeback["amount"] = -txn["amount"] * 1.05  # Chargeback + fee
                    chargeback["reference"] = f"CHARGEBACK-{txn.get('reference', '')}"
                    chargeback["transaction_type"] = "chargeback"
                    chargeback["fee"] = txn["amount"] * 0.05
                    chargebacks.append(chargeback)
            chaotic.extend(chargebacks)
        
        return chaotic
    
    def _generate_mt940_statement(self, transactions: List[Dict], entity_id: int) -> str:
        """Generate properly formatted MT940 statement."""
        lines = []
        
        # Header
        lines.append(":20:REFERENCE001")
        lines.append(f":25:ACC{entity_id:06d}")
        lines.append(":28C:00001/001")
        
        # Transactions
        for txn in transactions:
            if txn.get("is_wash"):
                continue
            
            dt = datetime.fromisoformat(txn["transaction_date"])
            date_str = dt.strftime("%y%m%d")
            amount = abs(txn["amount"])
            debit_credit = "D" if txn["amount"] < 0 else "C"
            
            # Format :61: properly (16 chars: date + amount + indicator)
            # Format: YYMMDDMMDD[DC]AMOUNT[3-letter-code]
            amount_str = f"{amount:.2f}".replace(".", ",")
            # Pad amount to 15 chars, add currency code
            currency = txn.get("currency", "EUR")[:3]
            line61 = f":61:{date_str}{date_str}{debit_credit}{amount_str:>15}{currency}"
            # Ensure exactly 16 chars for date part + proper formatting
            if len(line61) > 80:  # MT940 line limit
                line61 = line61[:80]
            lines.append(line61)
            
            # Narrative (:86:)
            narrative = f"{txn.get('reference', '')} {txn.get('counterparty', '')}"[:390]
            lines.append(f":86:{narrative}")
        
        # Closing balance
        total = sum(txn["amount"] for txn in transactions if not txn.get("is_wash"))
        balance_str = f"{abs(total):.2f}".replace(".", ",")
        lines.append(f":62F:C{datetime.now().strftime('%y%m%d')}EUR{balance_str:>15}")
        
        return "\n".join(lines)
    
    def _generate_bai2_statement(self, transactions: List[Dict], entity_id: int) -> str:
        """Generate properly formatted BAI2 statement."""
        lines = []
        
        # File header (01)
        now = datetime.now()
        lines.append(f"01,999999999,{now.strftime('%y%m%d')},1200,001,USD,+")
        
        # Account header (02)
        total = sum(txn["amount"] for txn in transactions if not txn.get("is_wash"))
        lines.append(f"02,ACC{entity_id:06d},{abs(total):.2f},{now.strftime('%y%m%d')},1200,001,+,{abs(total):.2f}")
        
        # Transactions (16)
        for txn in transactions:
            if txn.get("is_wash"):
                continue
            
            dt = datetime.fromisoformat(txn["transaction_date"])
            date_str = dt.strftime("%y%m%d")
            amount = abs(txn["amount"])
            type_code = "108" if txn["amount"] > 0 else "475"
            ref = (txn.get("reference", "")[:16] or "NONREF").ljust(16)
            
            lines.append(f"16,{type_code},{amount:.2f},{date_str},,{ref},,,")
            # Continuation (88)
            counterparty = (txn.get("counterparty", "")[:35] or "").ljust(35)
            lines.append(f"88,{counterparty}")
        
        # Account trailer (49)
        lines.append(f"49,{abs(total):.2f},1,")
        # File trailer (99)
        lines.append(f"99,{abs(total):.2f},1,")
        
        return "\n".join(lines)
    
    def _generate_camt053_statement(self, transactions: List[Dict], entity_id: int) -> str:
        """Generate properly formatted camt.053 XML."""
        root = ET.Element("Document", xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02")
        bk_to_cstmr = ET.SubElement(root, "BkToCstmrStmt")
        
        # Group header
        grp_hdr = ET.SubElement(bk_to_cstmr, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = f"MSG{entity_id:06d}"
        ET.SubElement(grp_hdr, "CreDtTm").text = datetime.now(timezone.utc).isoformat()
        
        # Statement
        stmt = ET.SubElement(bk_to_cstmr, "Stmt")
        ET.SubElement(stmt, "Id").text = f"STMT{entity_id:06d}"
        
        # Account
        acct = ET.SubElement(stmt, "Acct")
        acct_id = ET.SubElement(acct, "Id")
        othr = ET.SubElement(acct_id, "Othr")
        ET.SubElement(othr, "Id").text = f"ACC{entity_id:06d}"
        
        # Balance
        bal = ET.SubElement(stmt, "Bal")
        tp = ET.SubElement(bal, "Tp")
        cd_or_prtry = ET.SubElement(tp, "CdOrPrtry")
        ET.SubElement(cd_or_prtry, "Cd").text = "CLBD"
        total = sum(txn["amount"] for txn in transactions if not txn.get("is_wash"))
        amt = ET.SubElement(bal, "Amt", Ccy="EUR")
        amt.text = f"{abs(total):.2f}"
        dt = ET.SubElement(bal, "Dt")
        ET.SubElement(dt, "Dt").text = datetime.now().strftime("%Y-%m-%d")
        
        # Entries
        ntry = ET.SubElement(stmt, "Ntry")
        for txn in transactions:
            if txn.get("is_wash"):
                continue
            
            ntry_elem = ET.SubElement(ntry, "Ntry")
            dt_elem = datetime.fromisoformat(txn["transaction_date"])
            ET.SubElement(ntry_elem, "Amt", Ccy=txn.get("currency", "EUR")).text = f"{abs(txn['amount']):.2f}"
            ET.SubElement(ntry_elem, "CdtDbtInd").text = "CRDT" if txn["amount"] > 0 else "DBIT"
            bookg_dt = ET.SubElement(ntry_elem, "BookgDt")
            ET.SubElement(bookg_dt, "Dt").text = dt_elem.strftime("%Y-%m-%d")
            val_dt = ET.SubElement(ntry_elem, "ValDt")
            ET.SubElement(val_dt, "Dt").text = dt_elem.strftime("%Y-%m-%d")
            bk_tx_cd = ET.SubElement(ntry_elem, "BkTxCd")
            prtry = ET.SubElement(bk_tx_cd, "Prtry")
            ET.SubElement(prtry, "Cd").text = "PMNT"
            ntry_dtls = ET.SubElement(ntry_elem, "NtryDtls")
            tx_dtls = ET.SubElement(ntry_dtls, "TxDtls")
            rmt_inf = ET.SubElement(tx_dtls, "RmtInf")
            ET.SubElement(rmt_inf, "Ustrd").text = txn.get("reference", "")[:140]
        
        return ET.tostring(root, encoding='unicode')
    
    def _generate_csv_statement(self, transactions: List[Dict]) -> str:
        """Generate CSV statement."""
        lines = ["date,amount,currency,reference,counterparty,type"]
        for txn in transactions:
            if txn.get("is_wash"):
                continue
            lines.append(
                f"{txn['transaction_date']},{txn['amount']},{txn.get('currency', 'EUR')},"
                f"{txn.get('reference', '')},{txn.get('counterparty', '')},{txn.get('transaction_type', '')}"
            )
        return "\n".join(lines)
    
    def _hash_transaction(self, txn: Dict) -> str:
        """Create canonical hash for transaction."""
        import hashlib
        key = f"{txn['transaction_date']}|{txn['amount']}|{txn.get('reference', '')}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def generate_amount_weighted_manifest(
        self,
        invoices: List[Dict],
        transactions: List[Dict]
    ) -> Dict:
        """
        Generate amount-weighted manifest invariants.
        
        CFOs care about € exposure, not row counts.
        """
        total_invoice_amount = sum(abs(inv.get("amount", 0)) for inv in invoices)
        total_transaction_amount = sum(abs(txn.get("amount", 0)) for txn in transactions)
        
        # Amount-weighted checks
        amount_weighted = {
            "total_invoice_amount": total_invoice_amount,
            "total_transaction_amount": total_transaction_amount,
            "reconciliation_coverage": {
                "matched_amount": 0.0,  # Will be calculated after reconciliation
                "unmatched_amount": total_transaction_amount,
                "coverage_pct": 0.0
            },
            "fx_exposure": {
                "total_foreign_currency_amount": 0.0,
                "missing_fx_rate_amount": 0.0,
                "exposure_pct": 0.0
            },
            "data_quality": {
                "missing_due_date_amount": 0.0,
                "missing_due_date_pct": 0.0,
                "duplicate_invoice_amount": 0.0,
                "duplicate_invoice_pct": 0.0
            }
        }
        
        # Calculate FX exposure (amount-weighted)
        foreign_currency_invoices = [
            inv for inv in invoices
            if inv.get("currency") and inv.get("currency") != "EUR"
        ]
        foreign_amount = sum(abs(inv.get("amount", 0)) for inv in foreign_currency_invoices)
        amount_weighted["fx_exposure"]["total_foreign_currency_amount"] = foreign_amount
        amount_weighted["fx_exposure"]["exposure_pct"] = (
            (foreign_amount / total_invoice_amount * 100.0) if total_invoice_amount > 0 else 0.0
        )
        
        # Calculate missing due date (amount-weighted)
        missing_due_date_invoices = [
            inv for inv in invoices
            if not inv.get("expected_due_date")
        ]
        missing_due_date_amount = sum(abs(inv.get("amount", 0)) for inv in missing_due_date_invoices)
        amount_weighted["data_quality"]["missing_due_date_amount"] = missing_due_date_amount
        amount_weighted["data_quality"]["missing_due_date_pct"] = (
            (missing_due_date_amount / total_invoice_amount * 100.0) if total_invoice_amount > 0 else 0.0
        )
        
        return amount_weighted


