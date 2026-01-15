#!/usr/bin/env python3
"""
Synthetic Finance Dataset Generator for Gitto
Generates realistic test data for AR invoices, AP bills, bank statements, FX rates, and intercompany transfers.
"""

import json
import csv
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
import math

# Configuration
OUTPUT_DIR = Path(__file__).parent
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Realistic data pools
CUSTOMERS = [
    "Acme Corporation", "TechStart Inc", "Global Solutions Ltd", "Enterprise Systems",
    "Digital Dynamics", "Cloud Services Co", "Innovation Partners", "Future Tech",
    "Smart Solutions", "NextGen Industries", "MegaCorp International", "StartupHub"
]

COUNTRIES = ["US", "UK", "DE", "FR", "IT", "ES", "NL", "BE", "CH", "AT", "SE", "NO"]

VENDORS = [
    "Office Supplies Pro", "Cloud Infrastructure Inc", "Legal Services Group",
    "Marketing Agency Ltd", "IT Support Services", "Facilities Management",
    "Consulting Partners", "Software Licenses Co", "Travel Services", "Utilities Corp"
]

PAYMENT_TERMS = ["Net 30", "Net 60", "Net 15", "Net 45", "2/10 Net 30", "Due on Receipt"]

CURRENCIES = ["EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK"]

BANKS = ["HSBC", "J.P. Morgan", "Deutsche Bank", "BNP Paribas", "Barclays", "UBS"]

# Edge case configuration
@dataclass
class EdgeCaseConfig:
    duplicate_rate: float = 0.02  # 2% duplicates
    credit_note_rate: float = 0.05  # 5% credit notes
    rebill_rate: float = 0.03  # 3% rebills
    partial_payment_rate: float = 0.10  # 10% partial payments
    noisy_reference_rate: float = 0.15  # 15% noisy references
    blank_field_rate: float = 0.05  # 5% blank fields
    scientific_notation_rate: float = 0.01  # 1% scientific notation
    missing_fx_rate: float = 0.08  # 8% missing FX rates

class SyntheticDataGenerator:
    def __init__(self, edge_config: EdgeCaseConfig = None):
        self.edge_config = edge_config or EdgeCaseConfig()
        self.entities = []
        self.invoices = []
        self.vendor_bills = []
        self.bank_transactions = []
        self.fx_rates = []
        self.intercompany_transfers = []
        self.manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "random_seed": RANDOM_SEED,
            "edge_case_config": asdict(self.edge_config),
            "datasets": {},
            "invariants": [],
            "known_exceptions": []
        }
        
    def generate_entities(self, count: int = 3) -> List[Dict]:
        """Generate multi-entity structure"""
        entities = []
        entity_names = ["Gitto US", "Gitto EU", "Gitto UK"]
        entity_currencies = ["USD", "EUR", "GBP"]
        payment_run_days = [3, 1, 2]  # Thu, Mon, Tue
        
        for i in range(count):
            entity = {
                "id": i + 1,
                "name": entity_names[i] if i < len(entity_names) else f"Entity {i+1}",
                "currency": entity_currencies[i] if i < len(entity_currencies) else random.choice(CURRENCIES),
                "payment_run_day": payment_run_days[i] if i < len(payment_run_days) else random.randint(0, 6),
                "internal_account_ids": [f"INT-ACC-{i+1}-{j}" for j in range(2)]
            }
            entities.append(entity)
            self.entities.append(entity)
        
        return entities
    
    def generate_ar_invoices(self, entity_id: int, count: int = 200, start_date: datetime = None) -> List[Dict]:
        """Generate AR invoices with open and paid history"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=180)
        
        invoices = []
        invoice_counter = 1
        
        for i in range(count):
            # Determine if paid or open
            is_paid = random.random() < 0.65  # 65% paid, 35% open
            
            # Invoice dates
            invoice_date = start_date + timedelta(days=random.randint(0, 120))
            payment_terms_days = random.choice([15, 30, 45, 60])
            due_date = invoice_date + timedelta(days=payment_terms_days)
            
            # Payment date (if paid)
            payment_date = None
            if is_paid:
                # Realistic payment delay (some pay early, most pay late)
                delay_days = random.gauss(7, 10)  # Mean 7 days late, std dev 10
                delay_days = max(-10, min(60, int(delay_days)))  # Clamp between -10 and 60
                payment_date = due_date + timedelta(days=delay_days)
            
            customer = random.choice(CUSTOMERS)
            country = random.choice(COUNTRIES)
            currency = random.choice(CURRENCIES)
            amount = round(random.uniform(1000, 50000), 2)
            
            # Edge case: scientific notation (store as string for CSV)
            amount_str = str(amount)
            if random.random() < self.edge_config.scientific_notation_rate:
                amount_str = f"{amount:.2e}"
            else:
                amount_str = str(amount)
            
            document_number = f"INV-{entity_id:02d}-{invoice_counter:05d}"
            
            # Edge case: duplicate invoice
            if random.random() < self.edge_config.duplicate_rate and len(invoices) > 0:
                duplicate = random.choice(invoices)
                document_number = duplicate["document_number"]
            
            invoice = {
                "entity_id": entity_id,
                "document_number": document_number,
                "customer": customer,
                "country": country,
                "currency": currency,
                "amount": amount_str if 'amount_str' in locals() else amount,
                "invoice_issue_date": invoice_date.isoformat(),
                "expected_due_date": due_date.isoformat(),
                "payment_date": payment_date.isoformat() if payment_date else None,
                "payment_terms_days": payment_terms_days,
                "terms_of_payment": random.choice(PAYMENT_TERMS),
                "document_type": "Invoice",
                "project": f"Project-{random.randint(1, 20)}",
                "project_desc": f"Services for {customer}",
                "relationship_type": None,
                "parent_invoice_id": None,
                "is_blocked": 0,
                "dispute_status": "active"
            }
            
            # Edge case: blank fields
            if random.random() < self.edge_config.blank_field_rate:
                blank_field = random.choice(["country", "project", "project_desc"])
                invoice[blank_field] = ""
            
            invoices.append(invoice)
            invoice_counter += 1
        
        # Generate credit notes and rebills
        credit_notes = self._generate_credit_notes(invoices, entity_id)
        rebills = self._generate_rebills(invoices, entity_id)
        
        # Generate partial payments
        partials = self._generate_partial_payments(invoices, entity_id)
        
        all_invoices = invoices + credit_notes + rebills + partials
        self.invoices.extend(all_invoices)
        
        return all_invoices
    
    def _generate_credit_notes(self, invoices: List[Dict], entity_id: int) -> List[Dict]:
        """Generate credit notes linked to existing invoices"""
        credit_notes = []
        credit_count = int(len(invoices) * self.edge_config.credit_note_rate)
        
        for _ in range(credit_count):
            parent = random.choice([inv for inv in invoices if inv.get("payment_date")])
            if not parent:
                continue
            
            # Handle amount (could be string for scientific notation)
            parent_amount = parent["amount"]
            if isinstance(parent_amount, str):
                try:
                    parent_amount = float(parent_amount)
                except (ValueError, TypeError):
                    continue
            
            credit_note = {
                "entity_id": entity_id,
                "document_number": f"CN-{parent['document_number']}",
                "customer": parent["customer"],
                "country": parent["country"],
                "currency": parent["currency"],
                "amount": -round(parent_amount * random.uniform(0.1, 0.5), 2),  # Negative amount
                "invoice_issue_date": (datetime.fromisoformat(parent["invoice_issue_date"]) + timedelta(days=random.randint(5, 30))).isoformat(),
                "expected_due_date": None,
                "payment_date": None,
                "payment_terms_days": 0,
                "terms_of_payment": parent["terms_of_payment"],
                "document_type": "Credit Note",
                "project": parent.get("project", ""),
                "project_desc": f"Credit for {parent['document_number']}",
                "relationship_type": "credit_note",
                "parent_invoice_id": parent.get("id"),
                "is_blocked": 0,
                "dispute_status": "active"
            }
            credit_notes.append(credit_note)
        
        return credit_notes
    
    def _generate_rebills(self, invoices: List[Dict], entity_id: int) -> List[Dict]:
        """Generate rebills linked to existing invoices"""
        rebills = []
        rebill_count = int(len(invoices) * self.edge_config.rebill_rate)
        
        for _ in range(rebill_count):
            parent = random.choice(invoices)
            
            # Handle amount (could be string for scientific notation)
            parent_amount = parent["amount"]
            if isinstance(parent_amount, str):
                try:
                    parent_amount = float(parent_amount)
                except (ValueError, TypeError):
                    continue
            
            rebill = {
                "entity_id": entity_id,
                "document_number": f"RE-{parent['document_number']}",
                "customer": parent["customer"],
                "country": parent["country"],
                "currency": parent["currency"],
                "amount": round(parent_amount * random.uniform(0.8, 1.2), 2),
                "invoice_issue_date": (datetime.fromisoformat(parent["invoice_issue_date"]) + timedelta(days=random.randint(1, 10))).isoformat(),
                "expected_due_date": (datetime.fromisoformat(parent["expected_due_date"]) + timedelta(days=random.randint(1, 10))).isoformat(),
                "payment_date": None,
                "payment_terms_days": parent["payment_terms_days"],
                "terms_of_payment": parent["terms_of_payment"],
                "document_type": "Rebill",
                "project": parent.get("project", ""),
                "project_desc": f"Rebill of {parent['document_number']}",
                "relationship_type": "rebill",
                "parent_invoice_id": parent.get("id"),
                "is_blocked": 0,
                "dispute_status": "active"
            }
            rebills.append(rebill)
        
        return rebills
    
    def _generate_partial_payments(self, invoices: List[Dict], entity_id: int) -> List[Dict]:
        """Generate partial payment records"""
        partials = []
        partial_count = int(len(invoices) * self.edge_config.partial_payment_rate)
        
        for _ in range(partial_count):
            parent = random.choice([inv for inv in invoices if not inv.get("payment_date")])
            if not parent:
                continue
            
            # Handle amount (could be string for scientific notation)
            parent_amount = parent["amount"]
            if isinstance(parent_amount, str):
                try:
                    parent_amount = float(parent_amount)
                except (ValueError, TypeError):
                    continue
            
            # Create partial payment invoice
            partial_amount = round(parent_amount * random.uniform(0.3, 0.7), 2)
            
            partial = {
                "entity_id": entity_id,
                "document_number": f"PART-{parent['document_number']}",
                "customer": parent["customer"],
                "country": parent["country"],
                "currency": parent["currency"],
                "amount": partial_amount,
                "invoice_issue_date": parent["invoice_issue_date"],
                "expected_due_date": parent["expected_due_date"],
                "payment_date": (datetime.fromisoformat(parent["expected_due_date"]) + timedelta(days=random.randint(0, 30))).isoformat(),
                "payment_terms_days": parent["payment_terms_days"],
                "terms_of_payment": parent["terms_of_payment"],
                "document_type": "Partial Payment",
                "project": parent.get("project", ""),
                "project_desc": f"Partial payment for {parent['document_number']}",
                "relationship_type": "partial",
                "parent_invoice_id": parent.get("id"),
                "is_blocked": 0,
                "dispute_status": "active"
            }
            partials.append(partial)
        
        return partials
    
    def generate_ap_vendor_bills(self, entity_id: int, count: int = 150, start_date: datetime = None) -> List[Dict]:
        """Generate AP vendor bills with approval/hold states"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        
        bills = []
        entity = next((e for e in self.entities if e["id"] == entity_id), None)
        payment_run_day = entity["payment_run_day"] if entity else 3
        
        for i in range(count):
            vendor = random.choice(VENDORS)
            currency = random.choice(CURRENCIES)
            amount = round(random.uniform(500, 25000), 2)
            
            bill_date = start_date + timedelta(days=random.randint(0, 60))
            due_date = bill_date + timedelta(days=random.choice([15, 30, 45, 60]))
            
            # Approval state
            is_approved = random.random() < 0.85  # 85% approved
            approval_date = None
            if is_approved:
                approval_date = bill_date + timedelta(days=random.randint(1, 5))
            
            # Hold status
            hold_status = 0
            if random.random() < 0.10:  # 10% on hold
                hold_status = 1
            
            # Scheduled payment date (based on payment run day)
            scheduled_payment_date = None
            if is_approved and hold_status == 0:
                # Calculate next payment run day
                days_until_run = (payment_run_day - due_date.weekday()) % 7
                if days_until_run == 0:
                    days_until_run = 7
                scheduled_payment_date = due_date + timedelta(days=days_until_run)
            
            # Discretionary classification
            is_discretionary = random.random() < 0.20  # 20% discretionary
            
            bill = {
                "entity_id": entity_id,
                "document_number": f"BILL-{entity_id:02d}-{i+1:05d}",
                "vendor_name": vendor,
                "amount": amount,
                "currency": currency,
                "due_date": due_date.isoformat(),
                "approval_date": approval_date.isoformat() if approval_date else None,
                "scheduled_payment_date": scheduled_payment_date.isoformat() if scheduled_payment_date else None,
                "hold_status": hold_status,
                "is_discretionary": 1 if is_discretionary else 0,
                "category": random.choice(["Office", "IT", "Legal", "Marketing", "Facilities", "Travel", "Software"])
            }
            
            bills.append(bill)
        
        self.vendor_bills.extend(bills)
        return bills
    
    def generate_fx_rates(self, snapshot_date: datetime = None, weeks: int = 13) -> List[Dict]:
        """Generate FX rates per week with intentional gaps"""
        if snapshot_date is None:
            snapshot_date = datetime.now()
        
        base_rates = {
            ("USD", "EUR"): 0.92,
            ("GBP", "EUR"): 1.17,
            ("CHF", "EUR"): 1.02,
            ("SEK", "EUR"): 0.089,
            ("NOK", "EUR"): 0.087,
            ("DKK", "EUR"): 0.134
        }
        
        fx_rates = []
        currency_pairs = list(base_rates.keys())
        
        for week in range(weeks):
            week_start = snapshot_date + timedelta(weeks=week)
            week_start = week_start - timedelta(days=week_start.weekday())  # Monday
            
            for from_curr, to_curr in currency_pairs:
                # Intentional gaps
                if random.random() < self.edge_config.missing_fx_rate:
                    continue
                
                base_rate = base_rates[(from_curr, to_curr)]
                # Add realistic variation (±2%)
                variation = random.uniform(-0.02, 0.02)
                rate = round(base_rate * (1 + variation), 6)
                
                fx_rate = {
                    "from_currency": from_curr,
                    "to_currency": to_curr,
                    "rate": rate,
                    "effective_week_start": week_start.isoformat()
                }
                fx_rates.append(fx_rate)
        
        self.fx_rates.extend(fx_rates)
        return fx_rates
    
    def generate_bank_transactions(self, entity_id: int, count: int = 300, start_date: datetime = None) -> List[Dict]:
        """Generate bank transactions for reconciliation"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        
        transactions = []
        bank_account = f"ACC-{entity_id:03d}"
        
        # Match some transactions to invoices
        paid_invoices = [inv for inv in self.invoices if inv.get("payment_date") and inv.get("entity_id") == entity_id]
        
        for i in range(count):
            # Determine transaction type
            if paid_invoices and random.random() < 0.60:  # 60% match to invoices
                invoice = random.choice(paid_invoices)
                amount = invoice["amount"]
                if isinstance(amount, str):
                    try:
                        amount = float(amount)
                    except (ValueError, TypeError):
                        amount = random.uniform(1000, 50000)
                reference = self._generate_reference(invoice["document_number"], noisy=random.random() < self.edge_config.noisy_reference_rate)
                counterparty = invoice["customer"]
                transaction_type = "customer_receipt"
            else:
                # Random transaction
                amount = round(random.uniform(-50000, 50000), 2)
                reference = self._generate_reference(f"TXN-{i+1:06d}", noisy=random.random() < self.edge_config.noisy_reference_rate)
                counterparty = random.choice(CUSTOMERS + VENDORS)
                transaction_type = random.choice(["customer_receipt", "supplier_payment", "payroll", "tax", "rent", "loan"])
            
            transaction_date = start_date + timedelta(days=random.randint(0, 90))
            
            # Edge case: fees
            fee = 0
            if random.random() < 0.15:  # 15% have fees
                fee = round(random.uniform(5, 50), 2)
                amount = amount - fee if amount > 0 else amount + fee
            
            # Edge case: bundled payments
            is_bundled = random.random() < 0.10  # 10% bundled
            
            transaction = {
                "bank_account_id": bank_account,
                "transaction_date": transaction_date.isoformat(),
                "amount": amount,
                "currency": random.choice(CURRENCIES),
                "reference": reference,
                "counterparty": counterparty,
                "transaction_type": transaction_type,
                "fee": fee,
                "is_reconciled": 0,
                "is_wash": 0
            }
            
            transactions.append(transaction)
        
        # Generate intercompany transfers
        intercompany = self._generate_intercompany_transfers(entity_id, start_date)
        transactions.extend(intercompany)
        
        self.bank_transactions.extend(transactions)
        return transactions
    
    def _generate_reference(self, base_ref: str, noisy: bool = False) -> str:
        """Generate transaction reference, optionally with noise"""
        if not noisy:
            return base_ref
        
        # Add noise patterns
        noise_patterns = [
            f"REF: {base_ref}",
            f"{base_ref}-PAYMENT",
            f"PAYMENT FOR {base_ref}",
            f"{base_ref} | BANK REF",
            f"INV-{base_ref.split('-')[-1]}",
            base_ref.replace("-", ""),
            base_ref.upper(),
        ]
        
        return random.choice(noise_patterns)
    
    def _generate_intercompany_transfers(self, entity_id: int, start_date: datetime) -> List[Dict]:
        """Generate intercompany transfers (washes)"""
        transfers = []
        other_entities = [e for e in self.entities if e["id"] != entity_id]
        
        if not other_entities:
            return transfers
        
        transfer_count = random.randint(5, 15)
        
        for i in range(transfer_count):
            target_entity = random.choice(other_entities)
            amount = round(random.uniform(10000, 100000), 2)
            
            transaction_date = start_date + timedelta(days=random.randint(0, 90))
            
            transfer = {
                "bank_account_id": f"ACC-{entity_id:03d}",
                "transaction_date": transaction_date.isoformat(),
                "amount": -amount,  # Outgoing
                "currency": self.entities[entity_id - 1]["currency"],
                "reference": f"IC-TRANSFER-{target_entity['id']}-{i+1}",
                "counterparty": target_entity["name"],
                "transaction_type": "intercompany_transfer",
                "fee": 0,
                "is_reconciled": 0,
                "is_wash": 1  # Mark as intercompany wash
            }
            transfers.append(transfer)
            
            # Corresponding incoming transfer
            incoming = transfer.copy()
            incoming["bank_account_id"] = f"ACC-{target_entity['id']:03d}"
            incoming["amount"] = amount
            incoming["reference"] = f"IC-TRANSFER-{entity_id}-{i+1}"
            incoming["counterparty"] = self.entities[entity_id - 1]["name"]
            transfers.append(incoming)
        
        return transfers
    
    def write_csv(self, data: List[Dict], filename: str, headers: List[str] = None):
        """Write data to CSV file"""
        filepath = OUTPUT_DIR / filename
        if not data:
            return
        
        if headers is None:
            headers = list(data[0].keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"[OK] Generated {filename} ({len(data)} rows)")
    
    def write_mt940(self, transactions: List[Dict], filename: str):
        """Write bank transactions in MT940 format"""
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(":20:REFERENCE\n")
            f.write(":25:ACC123456789\n")
            f.write(":28C:00001/001\n")
            
            for txn in transactions:
                if txn.get("is_wash"):
                    continue  # Skip intercompany for MT940
                
                date_str = datetime.fromisoformat(txn["transaction_date"]).strftime("%y%m%d")
                amount = abs(txn["amount"])
                debit_credit = "D" if txn["amount"] < 0 else "C"
                
                f.write(f":61:{date_str}{date_str}D{amount:.2f}{debit_credit}NTRFNONREF//\n")
                f.write(f":86:{txn['reference']} {txn['counterparty']}\n")
            
            f.write(":62F:C240101EUR1000000,00\n")
        
        print(f"[OK] Generated {filename} (MT940 format)")
    
    def write_bai2(self, transactions: List[Dict], filename: str):
        """Write bank transactions in BAI2 format"""
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("01,999999999,240101,1200,001,USD,+\n")
            f.write("02,ACC123456789,1000000,00,240101,1200,001,+\n")
            
            for txn in transactions:
                if txn.get("is_wash"):
                    continue
                
                date_str = datetime.fromisoformat(txn["transaction_date"]).strftime("%y%m%d")
                amount = abs(txn["amount"])
                type_code = "108" if txn["amount"] > 0 else "475"
                
                f.write(f"16,{type_code},{amount:.2f},{date_str},,{txn['reference'][:16]},,,\n")
                f.write(f"88,{txn['counterparty'][:35]}\n")
            
            f.write("49,1000000,00,1,\n")
            f.write("99,1000000,00,1,\n")
        
        print(f"[OK] Generated {filename} (BAI2 format)")
    
    def write_camt053(self, transactions: List[Dict], filename: str):
        """Write bank transactions in camt.053 (ISO 20022) format"""
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">\n')
            f.write('  <BkToCstmrStmt>\n')
            f.write('    <GrpHdr>\n')
            f.write('      <MsgId>MSG001</MsgId>\n')
            f.write('      <CreDtTm>2024-01-01T12:00:00</CreDtTm>\n')
            f.write('    </GrpHdr>\n')
            f.write('    <Stmt>\n')
            f.write('      <Id>STMT001</Id>\n')
            f.write('      <Acct>\n')
            f.write('        <Id><Othr><Id>ACC123456789</Id></Othr></Id>\n')
            f.write('      </Acct>\n')
            f.write('      <Bal>\n')
            f.write('        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>\n')
            f.write('        <Amt Ccy="EUR">1000000.00</Amt>\n')
            f.write('        <Dt><Dt>2024-01-01</Dt></Dt>\n')
            f.write('      </Bal>\n')
            f.write('      <Ntry>\n')
            
            for txn in transactions:
                if txn.get("is_wash"):
                    continue
                
                date_str = datetime.fromisoformat(txn["transaction_date"]).strftime("%Y-%m-%d")
                amount = abs(txn["amount"])
                ccy = txn.get("currency", "EUR")
                cdt_dbt = "CRDT" if txn["amount"] > 0 else "DBIT"
                
                f.write(f'        <Ntry>\n')
                f.write(f'          <Amt Ccy="{ccy}">{amount:.2f}</Amt>\n')
                f.write(f'          <CdtDbtInd>{cdt_dbt}</CdtDbtInd>\n')
                f.write(f'          <BookgDt><Dt>{date_str}</Dt></BookgDt>\n')
                f.write(f'          <ValDt><Dt>{date_str}</Dt></ValDt>\n')
                f.write(f'          <BkTxCd><Prtry><Cd>PMNT</Cd></Prtry></BkTxCd>\n')
                f.write(f'          <NtryDtls>\n')
                f.write(f'            <TxDtls>\n')
                f.write(f'              <RmtInf><Ustrd>{txn["reference"]}</Ustrd></RmtInf>\n')
                f.write(f'            </TxDtls>\n')
                f.write(f'          </NtryDtls>\n')
                f.write(f'        </Ntry>\n')
            
            f.write('      </Ntry>\n')
            f.write('    </Stmt>\n')
            f.write('  </BkToCstmrStmt>\n')
            f.write('</Document>\n')
        
        print(f"[OK] Generated {filename} (camt.053 format)")
    
    def generate_all(self):
        """Generate all datasets"""
        print("Generating synthetic finance datasets for Gitto...")
        print("=" * 60)
        
        # Generate entities
        entities = self.generate_entities(3)
        self.write_csv(entities, "entities.csv")
        self.manifest["datasets"]["entities"] = {
            "filename": "entities.csv",
            "row_count": len(entities),
            "description": "Multi-entity structure with payment run policies"
        }
        
        # Generate AR invoices per entity
        all_invoices = []
        for entity in entities:
            entity_invoices = self.generate_ar_invoices(entity["id"], count=200)
            all_invoices.extend(entity_invoices)
        
        self.write_csv(all_invoices, "ar_invoices.csv")
        self.manifest["datasets"]["ar_invoices"] = {
            "filename": "ar_invoices.csv",
            "row_count": len(all_invoices),
            "description": "AR invoices with open and paid history, credit notes, rebills, partials"
        }
        
        # Generate AP vendor bills per entity
        all_bills = []
        for entity in entities:
            entity_bills = self.generate_ap_vendor_bills(entity["id"], count=150)
            all_bills.extend(entity_bills)
        
        self.write_csv(all_bills, "ap_vendor_bills.csv")
        self.manifest["datasets"]["ap_vendor_bills"] = {
            "filename": "ap_vendor_bills.csv",
            "row_count": len(all_bills),
            "description": "AP vendor bills with approval/hold states and payment run scheduling"
        }
        
        # Generate FX rates
        fx_rates = self.generate_fx_rates(weeks=13)
        self.write_csv(fx_rates, "fx_rates.csv")
        self.manifest["datasets"]["fx_rates"] = {
            "filename": "fx_rates.csv",
            "row_count": len(fx_rates),
            "description": "FX rates per week with intentional missing-rate gaps"
        }
        
        # Generate bank transactions per entity
        all_transactions = []
        for entity in entities:
            entity_txns = self.generate_bank_transactions(entity["id"], count=300)
            all_transactions.extend(entity_txns)
        
        # Write in multiple formats
        self.write_csv(all_transactions, "bank_transactions.csv")
        self.write_mt940(all_transactions, "bank_statements.mt940")
        self.write_bai2(all_transactions, "bank_statements.bai2")
        self.write_camt053(all_transactions, "bank_statements_camt053.xml")
        
        self.manifest["datasets"]["bank_transactions"] = {
            "filename": "bank_transactions.csv",
            "row_count": len(all_transactions),
            "description": "Bank transactions in CSV format"
        }
        self.manifest["datasets"]["bank_statements_mt940"] = {
            "filename": "bank_statements.mt940",
            "format": "MT940",
            "description": "Bank statements in SWIFT MT940 format"
        }
        self.manifest["datasets"]["bank_statements_bai2"] = {
            "filename": "bank_statements.bai2",
            "format": "BAI2",
            "description": "Bank statements in BAI2 format"
        }
        self.manifest["datasets"]["bank_statements_camt053"] = {
            "filename": "bank_statements_camt053.xml",
            "format": "camt.053 (ISO 20022)",
            "description": "Bank statements in camt.053 XML format"
        }
        
        # Write manifest
        self._write_manifest()
        
        print("=" * 60)
        print("[OK] All datasets generated successfully!")
        print(f"[OK] Output directory: {OUTPUT_DIR}")
    
    def _write_manifest(self):
        """Write manifest.json with invariants and exceptions"""
        # Define invariants
        self.manifest["invariants"] = [
            "All invoices have entity_id matching an entity",
            "All vendor bills have entity_id matching an entity",
            "Credit notes have negative amounts",
            "Partial payments sum to less than or equal to parent invoice amount",
            "Intercompany transfers are marked with is_wash=1",
            "Bank transactions match invoice amounts (within tolerance) when reconciled",
            "FX rates are positive numbers",
            "Payment dates are after invoice dates",
            "Due dates are after invoice dates"
        ]
        
        # Define known exceptions
        self.manifest["known_exceptions"] = [
            {
                "dataset": "ar_invoices.csv",
                "exception": "Some invoices have blank country/project fields (5% rate)",
                "reason": "Simulates merged-cell-like blanks from Excel imports"
            },
            {
                "dataset": "ar_invoices.csv",
                "exception": "Some amounts use scientific notation (1% rate)",
                "reason": "Edge case from Excel exports"
            },
            {
                "dataset": "ar_invoices.csv",
                "exception": "Duplicate document_numbers exist (2% rate)",
                "reason": "Simulates data quality issues"
            },
            {
                "dataset": "bank_transactions.csv",
                "exception": "Some references are noisy/variations of invoice numbers (15% rate)",
                "reason": "Real-world bank statement variations"
            },
            {
                "dataset": "fx_rates.csv",
                "exception": "Some currency pairs missing for certain weeks (8% rate)",
                "reason": "Simulates missing FX rate data"
            },
            {
                "dataset": "bank_transactions.csv",
                "exception": "Intercompany transfers appear in both source and target entity",
                "reason": "Expected behavior - both sides of transfer are recorded"
            }
        ]
        
        # Write manifest
        manifest_path = OUTPUT_DIR / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Generated manifest.json")


if __name__ == "__main__":
    generator = SyntheticDataGenerator()
    generator.generate_all()

