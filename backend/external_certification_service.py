"""
External System Certification Service

Compares external TMS cash positions against Gitto bank-truth totals
and generates certification reports with discrepancy attribution.
"""

import csv
import hashlib
import io
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

import models
from external_certification_models import (
    ExternalSystemImport, ExternalCashPosition, CertificationReport,
    CertificationDiscrepancy, AccountComparison,
    DiscrepancyCategory, CertificationStatus
)


# ═══════════════════════════════════════════════════════════════════════════════
# COLUMN ALIASES FOR FLEXIBLE CSV PARSING
# ═══════════════════════════════════════════════════════════════════════════════

TMS_COLUMN_ALIASES = {
    "account_id": ["account_id", "accountid", "account_no", "account_number", "acct_id", "acct_no", "account"],
    "account_name": ["account_name", "accountname", "acct_name", "name", "description"],
    "bank_name": ["bank_name", "bankname", "bank", "institution", "fi_name"],
    "currency": ["currency", "ccy", "curr", "currency_code", "iso_currency"],
    "amount": ["amount", "balance", "position", "cash_position", "cash_balance", "ledger_balance", "available_balance"],
    "fx_rate": ["fx_rate", "fxrate", "rate", "exchange_rate", "conversion_rate"],
    "position_date": ["position_date", "as_of_date", "value_date", "date", "statement_date", "balance_date"],
}


def normalize_column_name(name: str) -> Optional[str]:
    """Map various column names to canonical names."""
    clean = name.lower().strip().replace(" ", "_").replace("-", "_")
    
    for canonical, aliases in TMS_COLUMN_ALIASES.items():
        if clean in aliases:
            return canonical
    
    return None


def parse_amount(value: str) -> Optional[float]:
    """Parse amount from various formats."""
    if not value or str(value).strip() in ("", "-", "N/A", "null"):
        return None
    
    clean = str(value).strip()
    
    # Handle parentheses for negative
    if clean.startswith("(") and clean.endswith(")"):
        clean = "-" + clean[1:-1]
    
    # Remove currency symbols and thousand separators
    for char in ["$", "€", "£", "¥", ",", " "]:
        clean = clean.replace(char, "")
    
    # Handle European decimal format (1.234,56)
    if "," in clean and "." in clean:
        if clean.index(",") > clean.index("."):
            clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        clean = clean.replace(",", ".")
    
    try:
        return float(clean)
    except ValueError:
        return None


def parse_date(value: str) -> Optional[datetime]:
    """Parse date from various formats."""
    if not value or str(value).strip() in ("", "-", "N/A", "null"):
        return None
    
    clean = str(value).strip()
    
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# EXTERNAL SYSTEM CERTIFICATION SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class ExternalCertificationService:
    """
    Service for importing external TMS data and generating certification reports.
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Tolerance thresholds
        self.rounding_tolerance = 0.01  # €0.01
        self.stale_data_threshold_hours = 24
        self.fx_tolerance_pct = 0.5  # 0.5% FX difference tolerance
    
    def import_tms_csv(
        self,
        snapshot_id: int,
        file_content: bytes,
        file_name: str,
        system_name: str,
        external_as_of: datetime,
        imported_by: str = "system",
        base_currency: str = "EUR"
    ) -> ExternalSystemImport:
        """
        Import cash position data from external TMS CSV file.
        """
        # Verify snapshot exists
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == snapshot_id
        ).first()
        
        if not snapshot:
            raise ValueError(f"Snapshot {snapshot_id} not found")
        
        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Parse CSV
        content_str = file_content.decode("utf-8-sig")  # Handle BOM
        reader = csv.DictReader(io.StringIO(content_str))
        
        # Normalize headers
        original_fieldnames = reader.fieldnames or []
        column_mapping = {}
        for col in original_fieldnames:
            canonical = normalize_column_name(col)
            if canonical:
                column_mapping[col] = canonical
        
        # Parse rows
        raw_data = []
        positions = []
        total_base = 0.0
        
        for row in reader:
            raw_data.append(row)
            
            # Extract normalized values
            normalized = {}
            for orig_col, canonical_col in column_mapping.items():
                normalized[canonical_col] = row.get(orig_col, "")
            
            # Parse position
            amount = parse_amount(normalized.get("amount", ""))
            if amount is None:
                continue
            
            currency = normalized.get("currency", base_currency).upper().strip()
            if not currency:
                currency = base_currency
            
            fx_rate = parse_amount(normalized.get("fx_rate", ""))
            position_date = parse_date(normalized.get("position_date", ""))
            
            # Convert to base currency
            if currency == base_currency:
                amount_base = amount
                fx_rate_used = 1.0
            elif fx_rate:
                amount_base = amount * fx_rate
                fx_rate_used = fx_rate
            else:
                # Try to get FX rate from Gitto
                gitto_fx = self._get_gitto_fx_rate(snapshot_id, currency, base_currency)
                if gitto_fx:
                    amount_base = amount * gitto_fx
                    fx_rate_used = gitto_fx
                else:
                    # Flag as needing attention
                    amount_base = amount  # Will cause FX discrepancy
                    fx_rate_used = 1.0
            
            positions.append({
                "external_account_id": normalized.get("account_id", ""),
                "account_name": normalized.get("account_name", ""),
                "bank_name": normalized.get("bank_name", ""),
                "currency": currency,
                "amount": amount,
                "amount_base": amount_base,
                "fx_rate_used": fx_rate_used,
                "position_date": position_date or external_as_of,
            })
            
            total_base += amount_base
        
        # Create import record
        import_record = ExternalSystemImport(
            snapshot_id=snapshot_id,
            system_name=system_name,
            file_name=file_name,
            file_hash=file_hash,
            imported_at=datetime.utcnow(),
            imported_by=imported_by,
            external_as_of=external_as_of,
            gitto_as_of=snapshot.created_at,
            raw_data_json=raw_data,
            row_count=len(positions),
            external_total_base=total_base,
            external_currency=base_currency,
        )
        self.db.add(import_record)
        self.db.flush()
        
        # Create position records
        for pos_data in positions:
            position = ExternalCashPosition(
                import_id=import_record.id,
                **pos_data
            )
            
            # Try to map to Gitto account
            gitto_account = self._find_matching_gitto_account(
                pos_data["external_account_id"],
                pos_data["account_name"],
                pos_data["bank_name"],
                snapshot.entity_id
            )
            
            if gitto_account:
                position.gitto_account_id = gitto_account.id
                position.is_mapped = True
                position.mapping_confidence = 0.9
            
            self.db.add(position)
        
        self.db.commit()
        self.db.refresh(import_record)
        
        return import_record
    
    def generate_certification_report(
        self,
        import_id: int,
        created_by: str = "system"
    ) -> CertificationReport:
        """
        Generate a certification report comparing external TMS vs Gitto totals.
        """
        # Get import record
        import_record = self.db.query(ExternalSystemImport).filter(
            ExternalSystemImport.id == import_id
        ).first()
        
        if not import_record:
            raise ValueError(f"Import {import_id} not found")
        
        snapshot = self.db.query(models.Snapshot).filter(
            models.Snapshot.id == import_record.snapshot_id
        ).first()
        
        # Calculate Gitto totals
        gitto_total = self._calculate_gitto_total(snapshot)
        
        # Calculate gross difference
        gross_difference = import_record.external_total_base - gitto_total
        
        # Create report
        report = CertificationReport(
            snapshot_id=import_record.snapshot_id,
            import_id=import_id,
            created_at=datetime.utcnow(),
            created_by=created_by,
            status=CertificationStatus.IN_PROGRESS,
            external_total_base=import_record.external_total_base,
            gitto_total_base=gitto_total,
            gross_difference_base=gross_difference,
        )
        self.db.add(report)
        self.db.flush()
        
        # Generate account-level comparisons
        self._generate_account_comparisons(report, import_record, snapshot)
        
        # Attribute discrepancies
        self._attribute_discrepancies(report, import_record, snapshot)
        
        # Calculate certification score
        report.certification_score = self._calculate_certification_score(report)
        
        # Determine if certifiable
        report.is_certified = (
            report.certification_score >= 95.0 and
            abs(report.unexplained_amount) < 1000.0  # Less than €1000 unexplained
        )
        
        report.status = CertificationStatus.COMPLETED
        
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def _calculate_gitto_total(self, snapshot: models.Snapshot) -> float:
        """Calculate total cash position from Gitto bank-truth data."""
        # Sum all bank account balances
        result = self.db.query(func.sum(models.BankAccount.balance)).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).scalar()
        
        return float(result or 0.0)
    
    def _get_gitto_fx_rate(
        self,
        snapshot_id: int,
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """Get FX rate from Gitto snapshot."""
        fx = self.db.query(models.WeeklyFXRate).filter(
            models.WeeklyFXRate.snapshot_id == snapshot_id,
            models.WeeklyFXRate.from_currency == from_currency,
            models.WeeklyFXRate.to_currency == to_currency
        ).first()
        
        return fx.rate if fx else None
    
    def _find_matching_gitto_account(
        self,
        external_id: str,
        account_name: str,
        bank_name: str,
        entity_id: int
    ) -> Optional[models.BankAccount]:
        """Try to match external account to Gitto bank account."""
        # Try exact account number match
        account = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == entity_id,
            models.BankAccount.account_number == external_id
        ).first()
        
        if account:
            return account
        
        # Try name match
        account = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == entity_id,
            models.BankAccount.account_name.ilike(f"%{account_name}%")
        ).first()
        
        if account:
            return account
        
        # Try bank name + fuzzy match
        accounts = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == entity_id,
            models.BankAccount.bank_name.ilike(f"%{bank_name}%")
        ).all()
        
        if len(accounts) == 1:
            return accounts[0]
        
        return None
    
    def _generate_account_comparisons(
        self,
        report: CertificationReport,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ):
        """Generate per-account comparisons."""
        # Get external positions
        external_positions = self.db.query(ExternalCashPosition).filter(
            ExternalCashPosition.import_id == import_record.id
        ).all()
        
        # Get Gitto accounts
        gitto_accounts = self.db.query(models.BankAccount).filter(
            models.BankAccount.entity_id == snapshot.entity_id
        ).all()
        
        gitto_by_id = {a.id: a for a in gitto_accounts}
        matched_gitto_ids = set()
        
        # Compare mapped positions
        for pos in external_positions:
            comparison = AccountComparison(
                report_id=report.id,
                external_account_id=pos.external_account_id,
                external_account_name=pos.account_name,
                external_amount=pos.amount,
                external_currency=pos.currency,
                external_amount_base=pos.amount_base,
            )
            
            if pos.is_mapped and pos.gitto_account_id:
                gitto_acct = gitto_by_id.get(pos.gitto_account_id)
                if gitto_acct:
                    comparison.gitto_account_id = gitto_acct.id
                    comparison.gitto_account_name = gitto_acct.account_name
                    comparison.gitto_amount = gitto_acct.balance
                    comparison.gitto_amount_base = gitto_acct.balance  # Assume EUR
                    comparison.is_matched = True
                    comparison.match_confidence = pos.mapping_confidence
                    
                    comparison.difference_base = pos.amount_base - gitto_acct.balance
                    if gitto_acct.balance != 0:
                        comparison.difference_pct = (comparison.difference_base / gitto_acct.balance) * 100
                    
                    # Determine primary discrepancy category
                    comparison.primary_discrepancy_category = self._categorize_account_difference(
                        pos, gitto_acct, import_record
                    )
                    
                    matched_gitto_ids.add(gitto_acct.id)
            else:
                comparison.is_matched = False
                comparison.primary_discrepancy_category = DiscrepancyCategory.MAPPING_GAP
            
            self.db.add(comparison)
        
        # Add unmatched Gitto accounts
        for acct in gitto_accounts:
            if acct.id not in matched_gitto_ids:
                comparison = AccountComparison(
                    report_id=report.id,
                    gitto_account_id=acct.id,
                    gitto_account_name=acct.account_name,
                    gitto_amount=acct.balance,
                    gitto_amount_base=acct.balance,
                    is_matched=False,
                    primary_discrepancy_category=DiscrepancyCategory.MAPPING_GAP,
                    difference_base=-acct.balance,
                )
                self.db.add(comparison)
    
    def _categorize_account_difference(
        self,
        external_pos: ExternalCashPosition,
        gitto_acct: models.BankAccount,
        import_record: ExternalSystemImport
    ) -> DiscrepancyCategory:
        """Determine the primary category for an account-level difference."""
        diff = abs(external_pos.amount_base - gitto_acct.balance)
        
        # Check for rounding
        if diff < self.rounding_tolerance:
            return DiscrepancyCategory.ROUNDING
        
        # Check for FX difference
        if external_pos.currency != gitto_acct.currency:
            return DiscrepancyCategory.FX_POLICY_DIFFERENCE
        
        # Check for stale data
        hours_diff = abs(
            (import_record.external_as_of - import_record.gitto_as_of).total_seconds() / 3600
        )
        if hours_diff > self.stale_data_threshold_hours:
            return DiscrepancyCategory.STALE_DATA
        
        return DiscrepancyCategory.TIMING_DIFFERENCE
    
    def _attribute_discrepancies(
        self,
        report: CertificationReport,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ):
        """Attribute gross difference to specific categories with evidence."""
        remaining = report.gross_difference_base
        
        # 1. Unmatched bank transactions
        unmatched_exposure = self._find_unmatched_bank_txn_exposure(snapshot)
        if unmatched_exposure != 0:
            explained = min(abs(remaining), abs(unmatched_exposure))
            if remaining * unmatched_exposure > 0:  # Same sign
                explained = unmatched_exposure
            
            self._create_discrepancy(
                report,
                DiscrepancyCategory.UNMATCHED_BANK_TXN,
                explained,
                "Unreconciled bank transactions not reflected in external system",
                self._get_unmatched_txn_evidence(snapshot)
            )
            report.explained_by_unmatched = explained
            remaining -= explained
        
        # 2. FX policy differences
        fx_exposure = self._find_fx_policy_exposure(import_record, snapshot)
        if fx_exposure != 0:
            self._create_discrepancy(
                report,
                DiscrepancyCategory.FX_POLICY_DIFFERENCE,
                fx_exposure,
                "Different FX rates used between systems",
                self._get_fx_evidence(import_record, snapshot)
            )
            report.explained_by_fx_policy = fx_exposure
            remaining -= fx_exposure
        
        # 3. Stale data
        stale_exposure = self._find_stale_data_exposure(import_record, snapshot)
        if stale_exposure != 0:
            self._create_discrepancy(
                report,
                DiscrepancyCategory.STALE_DATA,
                stale_exposure,
                f"Data freshness mismatch: {self._get_staleness_hours(import_record):.1f} hours",
                self._get_stale_data_evidence(import_record, snapshot)
            )
            report.explained_by_stale_data = stale_exposure
            remaining -= stale_exposure
        
        # 4. Mapping gaps
        mapping_exposure = self._find_mapping_gap_exposure(report)
        if mapping_exposure != 0:
            self._create_discrepancy(
                report,
                DiscrepancyCategory.MAPPING_GAP,
                mapping_exposure,
                "Accounts not mapped between systems",
                self._get_mapping_gap_evidence(report)
            )
            report.explained_by_mapping_gap = mapping_exposure
            remaining -= mapping_exposure
        
        # 5. Timing differences (intraday)
        timing_exposure = self._find_timing_exposure(import_record, snapshot)
        if timing_exposure != 0 and abs(remaining) > self.rounding_tolerance:
            explained = min(abs(remaining), abs(timing_exposure)) * (1 if remaining > 0 else -1)
            self._create_discrepancy(
                report,
                DiscrepancyCategory.TIMING_DIFFERENCE,
                explained,
                "Intraday timing differences in transaction capture",
                self._get_timing_evidence(import_record, snapshot)
            )
            report.explained_by_timing = explained
            remaining -= explained
        
        # 6. Rounding
        if abs(remaining) <= self.rounding_tolerance * 100:  # Up to €1 rounding
            self._create_discrepancy(
                report,
                DiscrepancyCategory.ROUNDING,
                remaining,
                "Rounding differences across currency conversions",
                []
            )
            report.explained_by_rounding = remaining
            remaining = 0
        
        # 7. Unexplained remainder
        if abs(remaining) > self.rounding_tolerance:
            self._create_discrepancy(
                report,
                DiscrepancyCategory.UNKNOWN,
                remaining,
                "Unexplained difference requiring investigation",
                []
            )
            report.unexplained_amount = remaining
        
        report.net_difference_base = remaining
    
    def _create_discrepancy(
        self,
        report: CertificationReport,
        category: DiscrepancyCategory,
        amount: float,
        description: str,
        evidence: List[Dict[str, Any]]
    ):
        """Create a discrepancy record with evidence."""
        discrepancy = CertificationDiscrepancy(
            report_id=report.id,
            category=category,
            description=description,
            amount_base=amount,
            currency="EUR",
            evidence_refs_json=evidence,
        )
        self.db.add(discrepancy)
    
    def _find_unmatched_bank_txn_exposure(self, snapshot: models.Snapshot) -> float:
        """Find total exposure from unmatched bank transactions."""
        result = self.db.query(func.sum(models.BankTransaction.amount)).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id,
            models.BankTransaction.is_reconciled == 0
        ).scalar()
        
        return float(result or 0.0)
    
    def _get_unmatched_txn_evidence(self, snapshot: models.Snapshot) -> List[Dict]:
        """Get evidence refs for unmatched transactions."""
        txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id,
            models.BankTransaction.is_reconciled == 0
        ).limit(10).all()
        
        return [
            {
                "type": "bank_txn",
                "id": txn.id,
                "reference": txn.reference,
                "amount": txn.amount,
                "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
                "description": f"Unmatched: {txn.counterparty}"
            }
            for txn in txns
        ]
    
    def _find_fx_policy_exposure(
        self,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ) -> float:
        """Calculate exposure from FX rate differences."""
        exposure = 0.0
        
        positions = self.db.query(ExternalCashPosition).filter(
            ExternalCashPosition.import_id == import_record.id,
            ExternalCashPosition.currency != import_record.external_currency
        ).all()
        
        for pos in positions:
            gitto_rate = self._get_gitto_fx_rate(
                snapshot.id,
                pos.currency,
                import_record.external_currency
            )
            
            if gitto_rate and pos.fx_rate_used:
                rate_diff_pct = abs(gitto_rate - pos.fx_rate_used) / gitto_rate * 100
                if rate_diff_pct > self.fx_tolerance_pct:
                    exposure += pos.amount * (gitto_rate - pos.fx_rate_used)
        
        return exposure
    
    def _get_fx_evidence(
        self,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ) -> List[Dict]:
        """Get evidence for FX differences."""
        evidence = []
        
        positions = self.db.query(ExternalCashPosition).filter(
            ExternalCashPosition.import_id == import_record.id,
            ExternalCashPosition.currency != import_record.external_currency
        ).all()
        
        for pos in positions:
            gitto_rate = self._get_gitto_fx_rate(
                snapshot.id,
                pos.currency,
                import_record.external_currency
            )
            
            if gitto_rate:
                evidence.append({
                    "type": "fx_rate",
                    "currency_pair": f"{pos.currency}/{import_record.external_currency}",
                    "external_rate": pos.fx_rate_used,
                    "gitto_rate": gitto_rate,
                    "difference": abs(gitto_rate - pos.fx_rate_used) if pos.fx_rate_used else None,
                    "description": f"FX rate difference for {pos.currency}"
                })
        
        return evidence[:10]
    
    def _find_stale_data_exposure(
        self,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ) -> float:
        """Estimate exposure from data staleness."""
        hours_diff = self._get_staleness_hours(import_record)
        
        if hours_diff <= self.stale_data_threshold_hours:
            return 0.0
        
        # Estimate based on average daily cash movement
        avg_daily_movement = self._estimate_daily_movement(snapshot)
        stale_days = hours_diff / 24
        
        return avg_daily_movement * stale_days * 0.5  # Conservative estimate
    
    def _get_staleness_hours(self, import_record: ExternalSystemImport) -> float:
        """Get hours between external and Gitto as-of times."""
        return abs(
            (import_record.external_as_of - import_record.gitto_as_of).total_seconds() / 3600
        )
    
    def _get_stale_data_evidence(
        self,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ) -> List[Dict]:
        """Get evidence for stale data."""
        return [{
            "type": "freshness",
            "external_as_of": import_record.external_as_of.isoformat(),
            "gitto_as_of": import_record.gitto_as_of.isoformat(),
            "hours_difference": self._get_staleness_hours(import_record),
            "description": "Data timestamp mismatch between systems"
        }]
    
    def _estimate_daily_movement(self, snapshot: models.Snapshot) -> float:
        """Estimate average daily cash movement."""
        # Get recent transactions
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        result = self.db.query(func.sum(func.abs(models.BankTransaction.amount))).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id,
            models.BankTransaction.transaction_date >= thirty_days_ago
        ).scalar()
        
        total_movement = float(result or 0.0)
        return total_movement / 30
    
    def _find_mapping_gap_exposure(self, report: CertificationReport) -> float:
        """Calculate exposure from unmapped accounts."""
        # External unmapped
        external_unmapped = self.db.query(func.sum(AccountComparison.external_amount_base)).filter(
            AccountComparison.report_id == report.id,
            AccountComparison.is_matched == False,
            AccountComparison.gitto_account_id == None
        ).scalar() or 0.0
        
        # Gitto unmapped
        gitto_unmapped = self.db.query(func.sum(AccountComparison.gitto_amount_base)).filter(
            AccountComparison.report_id == report.id,
            AccountComparison.is_matched == False,
            AccountComparison.external_account_id == None
        ).scalar() or 0.0
        
        return float(external_unmapped) - float(gitto_unmapped)
    
    def _get_mapping_gap_evidence(self, report: CertificationReport) -> List[Dict]:
        """Get evidence for mapping gaps."""
        unmapped = self.db.query(AccountComparison).filter(
            AccountComparison.report_id == report.id,
            AccountComparison.is_matched == False
        ).limit(10).all()
        
        evidence = []
        for comp in unmapped:
            if comp.external_account_id:
                evidence.append({
                    "type": "unmapped_external",
                    "account_id": comp.external_account_id,
                    "account_name": comp.external_account_name,
                    "amount": comp.external_amount_base,
                    "description": f"External account not found in Gitto"
                })
            elif comp.gitto_account_id:
                evidence.append({
                    "type": "unmapped_gitto",
                    "account_id": comp.gitto_account_id,
                    "account_name": comp.gitto_account_name,
                    "amount": comp.gitto_amount_base,
                    "description": f"Gitto account not found in external import"
                })
        
        return evidence
    
    def _find_timing_exposure(
        self,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ) -> float:
        """Estimate exposure from timing differences."""
        # Get transactions within the timing window
        start = min(import_record.external_as_of, import_record.gitto_as_of)
        end = max(import_record.external_as_of, import_record.gitto_as_of)
        
        result = self.db.query(func.sum(models.BankTransaction.amount)).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id,
            models.BankTransaction.transaction_date >= start,
            models.BankTransaction.transaction_date <= end
        ).scalar()
        
        return float(result or 0.0)
    
    def _get_timing_evidence(
        self,
        import_record: ExternalSystemImport,
        snapshot: models.Snapshot
    ) -> List[Dict]:
        """Get evidence for timing differences."""
        start = min(import_record.external_as_of, import_record.gitto_as_of)
        end = max(import_record.external_as_of, import_record.gitto_as_of)
        
        txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankAccount.entity_id == snapshot.entity_id,
            models.BankTransaction.transaction_date >= start,
            models.BankTransaction.transaction_date <= end
        ).limit(10).all()
        
        return [
            {
                "type": "timing_txn",
                "id": txn.id,
                "date": txn.transaction_date.isoformat() if txn.transaction_date else None,
                "amount": txn.amount,
                "description": f"Transaction in timing window: {txn.reference}"
            }
            for txn in txns
        ]
    
    def _calculate_certification_score(self, report: CertificationReport) -> float:
        """Calculate certification score (0-100)."""
        if report.external_total_base == 0:
            return 100.0 if report.gitto_total_base == 0 else 0.0
        
        # Score based on explained vs unexplained
        explained = (
            abs(report.explained_by_unmatched) +
            abs(report.explained_by_fx_policy) +
            abs(report.explained_by_stale_data) +
            abs(report.explained_by_mapping_gap) +
            abs(report.explained_by_timing) +
            abs(report.explained_by_rounding)
        )
        
        gross_diff = abs(report.gross_difference_base)
        
        if gross_diff == 0:
            return 100.0
        
        # Explained percentage
        explained_pct = min(100.0, (explained / gross_diff) * 100)
        
        # Base score from explained percentage
        score = explained_pct * 0.7
        
        # Bonus for low unexplained amount
        if abs(report.unexplained_amount) < 1000:
            score += 30
        elif abs(report.unexplained_amount) < 10000:
            score += 20
        elif abs(report.unexplained_amount) < 50000:
            score += 10
        
        return min(100.0, max(0.0, score))
    
    def export_report(
        self,
        report_id: int,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export certification report in specified format."""
        report = self.db.query(CertificationReport).filter(
            CertificationReport.id == report_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Get related data
        import_record = self.db.query(ExternalSystemImport).filter(
            ExternalSystemImport.id == report.import_id
        ).first()
        
        discrepancies = self.db.query(CertificationDiscrepancy).filter(
            CertificationDiscrepancy.report_id == report_id
        ).all()
        
        comparisons = self.db.query(AccountComparison).filter(
            AccountComparison.report_id == report_id
        ).all()
        
        export_data = {
            "report": {
                "id": report.id,
                "snapshot_id": report.snapshot_id,
                "created_at": report.created_at.isoformat(),
                "created_by": report.created_by,
                "status": report.status.value,
                "certification_score": report.certification_score,
                "is_certified": report.is_certified,
            },
            "summary": {
                "external_total_base": report.external_total_base,
                "gitto_total_base": report.gitto_total_base,
                "gross_difference_base": report.gross_difference_base,
                "net_difference_base": report.net_difference_base,
            },
            "explained_amounts": {
                "unmatched_bank_txn": report.explained_by_unmatched,
                "fx_policy": report.explained_by_fx_policy,
                "stale_data": report.explained_by_stale_data,
                "mapping_gap": report.explained_by_mapping_gap,
                "timing": report.explained_by_timing,
                "rounding": report.explained_by_rounding,
                "unexplained": report.unexplained_amount,
            },
            "source": {
                "system_name": import_record.system_name if import_record else None,
                "file_name": import_record.file_name if import_record else None,
                "external_as_of": import_record.external_as_of.isoformat() if import_record else None,
                "gitto_as_of": import_record.gitto_as_of.isoformat() if import_record else None,
            },
            "discrepancies": [
                {
                    "category": d.category.value,
                    "description": d.description,
                    "amount_base": d.amount_base,
                    "evidence": d.evidence_refs_json,
                    "is_resolved": d.is_resolved,
                }
                for d in discrepancies
            ],
            "account_comparisons": [
                {
                    "external_account": {
                        "id": c.external_account_id,
                        "name": c.external_account_name,
                        "amount": c.external_amount_base,
                    } if c.external_account_id else None,
                    "gitto_account": {
                        "id": c.gitto_account_id,
                        "name": c.gitto_account_name,
                        "amount": c.gitto_amount_base,
                    } if c.gitto_account_id else None,
                    "difference_base": c.difference_base,
                    "is_matched": c.is_matched,
                    "primary_category": c.primary_discrepancy_category.value if c.primary_discrepancy_category else None,
                }
                for c in comparisons
            ],
        }
        
        # Update export metadata
        report.exported_at = datetime.utcnow()
        report.export_format = format
        self.db.commit()
        
        return export_data
    
    def certify_report(
        self,
        report_id: int,
        certified_by: str,
        notes: str = ""
    ) -> CertificationReport:
        """Mark a report as certified."""
        report = self.db.query(CertificationReport).filter(
            CertificationReport.id == report_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        report.is_certified = True
        report.certified_at = datetime.utcnow()
        report.certified_by = certified_by
        report.certification_notes = notes
        report.status = CertificationStatus.CERTIFIED
        
        self.db.commit()
        self.db.refresh(report)
        
        return report
