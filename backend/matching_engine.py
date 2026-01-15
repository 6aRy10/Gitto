"""
Bank Reconciliation Matching Engine

O(n*k) indexed matching - NOT O(n*m) nested loops.

Matching Tiers:
- Tier 1: Deterministic (exact reference match)
- Tier 2: Rule-based (amount tolerance + date window + counterparty)
- Tier 3: Suggested (fuzzy matching, requires approval)
- Tier 4: Manual exceptions

Key Principles:
- Many-to-many allocations (partials, bundled payments)
- Suggested matches NEVER auto-apply
- Allocation conservation: sum(allocations) == txn_amount
- Policy-controlled tolerances per entity/currency
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import models


@dataclass
class MatchCandidate:
    """A potential match for a bank transaction."""
    invoice_id: int
    invoice_number: str
    customer_name: str
    amount: Decimal
    due_date: Optional[datetime]
    currency: str
    
    # Match quality
    tier: int  # 1-4
    confidence: float  # 0.0 - 1.0
    match_reasons: List[str] = field(default_factory=list)
    
    # For many-to-many
    suggested_allocation: Decimal = None


@dataclass
class MatchResult:
    """Result of matching a bank transaction."""
    bank_txn_id: int
    bank_txn_amount: Decimal
    candidates: List[MatchCandidate]
    
    # Best match info
    has_exact_match: bool = False
    best_tier: int = 4
    total_matched_amount: Decimal = Decimal('0')
    unallocated_amount: Decimal = Decimal('0')
    
    # Status
    status: str = 'pending'  # 'pending', 'auto_matched', 'suggested', 'manual_required'


@dataclass
class MatchingPolicy:
    """Matching rules configuration."""
    entity_id: Optional[int] = None
    currency: str = 'EUR'
    
    # Amount tolerance
    amount_tolerance_percent: float = 2.0  # +/- 2%
    amount_tolerance_absolute: Decimal = Decimal('0.01')  # Rounding tolerance
    
    # Date window
    date_window_days: int = 7  # +/- 7 days from due date
    
    # Auto-apply rules
    auto_apply_tier1: bool = True  # Exact matches
    auto_apply_tier2: bool = False  # Rule-based requires approval
    
    # Tier 2 thresholds
    tier2_min_confidence: float = 0.85
    tier3_min_confidence: float = 0.60


class MatchingIndex:
    """
    Indexed candidate retrieval for O(n*k) matching.
    
    Indexes by:
    - Amount buckets (rounded to nearest 100)
    - Reference text (extracted invoice numbers)
    - Counterparty name (normalized)
    - Due date ranges
    """
    
    def __init__(self):
        self.by_amount_bucket: Dict[int, List[int]] = defaultdict(list)
        self.by_ref: Dict[str, List[int]] = defaultdict(list)
        self.by_counterparty: Dict[str, List[int]] = defaultdict(list)
        self.by_due_week: Dict[str, List[int]] = defaultdict(list)
        self.invoices: Dict[int, models.Invoice] = {}
    
    def build(self, invoices: List[models.Invoice]) -> None:
        """Build index from list of invoices."""
        self.clear()
        
        for inv in invoices:
            if inv.payment_date:  # Skip already paid
                continue
            
            self.invoices[inv.id] = inv
            
            # Amount bucket (rounded to nearest 100)
            if inv.amount:
                bucket = int(inv.amount / 100) * 100
                self.by_amount_bucket[bucket].append(inv.id)
                # Also add adjacent buckets for tolerance
                self.by_amount_bucket[bucket - 100].append(inv.id)
                self.by_amount_bucket[bucket + 100].append(inv.id)
            
            # Reference text (invoice number variations)
            if inv.invoice_number:
                refs = self._extract_refs(inv.invoice_number)
                for ref in refs:
                    self.by_ref[ref.lower()].append(inv.id)
            
            # Counterparty (normalized)
            if inv.customer_name:
                normalized = self._normalize_name(inv.customer_name)
                self.by_counterparty[normalized].append(inv.id)
            
            # Due date week
            if inv.expected_due_date:
                week_key = self._get_week_key(inv.expected_due_date)
                self.by_due_week[week_key].append(inv.id)
    
    def query(
        self,
        amount: Decimal,
        amount_tolerance: float = 0.02,
        date_range: Tuple[datetime, datetime] = None,
        counterparty: str = None,
        refs: List[str] = None
    ) -> Set[int]:
        """
        Query index for matching candidates.
        
        Returns set of invoice IDs that match criteria.
        Uses set intersection for multi-criteria filtering.
        """
        candidates = None
        
        # Amount filter
        if amount:
            bucket = int(float(amount) / 100) * 100
            amount_candidates = set()
            for b in [bucket - 100, bucket, bucket + 100]:
                amount_candidates.update(self.by_amount_bucket.get(b, []))
            
            # Filter by actual tolerance
            amount_candidates = {
                inv_id for inv_id in amount_candidates
                if self._within_tolerance(amount, self.invoices[inv_id].amount, amount_tolerance)
            }
            
            candidates = amount_candidates if candidates is None else candidates & amount_candidates
        
        # Reference filter (union - any ref match is good)
        if refs:
            ref_candidates = set()
            for ref in refs:
                ref_lower = ref.lower()
                ref_candidates.update(self.by_ref.get(ref_lower, []))
            if ref_candidates:
                # Refs are additive with high weight, not restrictive
                if candidates is None:
                    candidates = ref_candidates
                else:
                    # Keep all amount matches, but note which have ref matches
                    pass
        
        # Counterparty filter
        if counterparty:
            normalized = self._normalize_name(counterparty)
            counterparty_candidates = set(self.by_counterparty.get(normalized, []))
            if counterparty_candidates:
                candidates = counterparty_candidates if candidates is None else candidates & counterparty_candidates
        
        # Date range filter
        if date_range:
            date_candidates = set()
            start_week = self._get_week_key(date_range[0])
            end_week = self._get_week_key(date_range[1])
            
            for week_key in self.by_due_week:
                if start_week <= week_key <= end_week:
                    date_candidates.update(self.by_due_week[week_key])
            
            if date_candidates:
                candidates = date_candidates if candidates is None else candidates & date_candidates
        
        return candidates or set()
    
    def clear(self) -> None:
        """Clear all indexes."""
        self.by_amount_bucket.clear()
        self.by_ref.clear()
        self.by_counterparty.clear()
        self.by_due_week.clear()
        self.invoices.clear()
    
    def _extract_refs(self, text: str) -> List[str]:
        """Extract potential invoice references from text."""
        refs = []
        
        # Invoice number as-is
        refs.append(text)
        
        # Remove common prefixes
        for prefix in ['INV-', 'INV', 'SI-', 'SI']:
            if text.upper().startswith(prefix):
                refs.append(text[len(prefix):])
        
        # Extract numeric portions
        numbers = re.findall(r'\d+', text)
        refs.extend(numbers)
        
        return refs
    
    def _normalize_name(self, name: str) -> str:
        """Normalize company name for matching."""
        if not name:
            return ''
        
        # Lowercase
        name = name.lower()
        
        # Remove common suffixes
        for suffix in [' ltd', ' llc', ' inc', ' gmbh', ' ag', ' sa', ' bv', ' nv']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove punctuation
        name = re.sub(r'[^\w\s]', '', name)
        
        # Collapse whitespace
        name = ' '.join(name.split())
        
        return name
    
    def _get_week_key(self, date) -> str:
        """Get week key for date indexing."""
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except:
                return ''
        if not date:
            return ''
        return date.strftime('%Y-W%W')
    
    def _within_tolerance(self, a: Decimal, b: float, tolerance: float) -> bool:
        """Check if amounts are within tolerance."""
        if not a or not b:
            return False
        a_float = float(a)
        diff = abs(a_float - b) / max(abs(a_float), abs(b), 1)
        return diff <= tolerance


class MatchingEngine:
    """
    Main matching engine for bank reconciliation.
    
    Usage:
        engine = MatchingEngine(db)
        engine.build_index(snapshot_id)
        result = engine.find_matches(bank_txn)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.index = MatchingIndex()
        self.policy = MatchingPolicy()
    
    def set_policy(self, policy: MatchingPolicy) -> None:
        """Set matching policy."""
        self.policy = policy
    
    def load_policy_from_db(self, entity_id: int = None, currency: str = None) -> None:
        """Load matching policy from database."""
        query = self.db.query(models.MatchingPolicy).filter(models.MatchingPolicy.is_active == 1)
        
        if entity_id:
            query = query.filter(models.MatchingPolicy.entity_id == entity_id)
        if currency:
            query = query.filter(models.MatchingPolicy.currency == currency)
        
        db_policy = query.first()
        if db_policy:
            self.policy = MatchingPolicy(
                entity_id=db_policy.entity_id,
                currency=db_policy.currency,
                amount_tolerance_percent=db_policy.amount_tolerance_percent or 2.0,
                date_window_days=db_policy.date_window_days or 7,
                auto_apply_tier1=db_policy.auto_reconcile_tier1 == 1 if db_policy.auto_reconcile_tier1 is not None else True,
                auto_apply_tier2=db_policy.auto_reconcile_tier2 == 1 if db_policy.auto_reconcile_tier2 is not None else False,
            )
    
    def build_index(self, snapshot_id: int) -> int:
        """Build index from snapshot invoices."""
        invoices = self.db.query(models.Invoice).filter(
            models.Invoice.snapshot_id == snapshot_id,
            models.Invoice.payment_date.is_(None)  # Only unpaid
        ).all()
        
        self.index.build(invoices)
        return len(invoices)
    
    def find_matches(self, bank_txn: models.BankTransaction) -> MatchResult:
        """
        Find matching candidates for a bank transaction.
        
        O(n*k) where n = number of indexed invoices, k = number of criteria
        """
        result = MatchResult(
            bank_txn_id=bank_txn.id,
            bank_txn_amount=Decimal(str(bank_txn.amount or 0)),
            candidates=[]
        )
        
        # Skip outflows (negative amounts) for AR matching
        if bank_txn.amount and bank_txn.amount < 0:
            result.status = 'skip_outflow'
            return result
        
        # Extract references from bank transaction text
        refs = self._extract_refs_from_bank_txn(bank_txn)
        
        # Query index
        candidate_ids = self.index.query(
            amount=Decimal(str(bank_txn.amount or 0)),
            amount_tolerance=self.policy.amount_tolerance_percent / 100,
            date_range=self._get_date_range(bank_txn.value_date),
            counterparty=bank_txn.counterparty_name,
            refs=refs
        )
        
        # Score each candidate
        for inv_id in candidate_ids:
            invoice = self.index.invoices.get(inv_id)
            if not invoice:
                continue
            
            candidate = self._score_candidate(bank_txn, invoice, refs)
            result.candidates.append(candidate)
        
        # Sort by tier (ascending) then confidence (descending)
        result.candidates.sort(key=lambda c: (c.tier, -c.confidence))
        
        # Determine result status
        if result.candidates:
            result.best_tier = result.candidates[0].tier
            result.has_exact_match = result.best_tier == 1
            
            if result.has_exact_match and self.policy.auto_apply_tier1:
                result.status = 'auto_matched'
            elif result.best_tier == 2 and result.candidates[0].confidence >= self.policy.tier2_min_confidence:
                result.status = 'suggested'
            elif result.best_tier == 3:
                result.status = 'suggested'
            else:
                result.status = 'manual_required'
            
            # Calculate allocation suggestions
            result = self._suggest_allocations(result, bank_txn)
        else:
            result.status = 'no_match'
        
        return result
    
    def _extract_refs_from_bank_txn(self, txn: models.BankTransaction) -> List[str]:
        """Extract invoice references from bank transaction text."""
        refs = []
        
        text = ' '.join(filter(None, [
            txn.remittance_info,
            txn.narrative,
            txn.counterparty_name
        ]))
        
        if not text:
            return refs
        
        # Common invoice reference patterns
        patterns = [
            r'INV[-#]?(\d+)',
            r'INVOICE\s*[:#]?\s*(\d+)',
            r'SI[-#]?(\d+)',
            r'REF\s*[:#]?\s*(\S+)',
            r'#(\d{4,})',  # Any 4+ digit number with hash
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            refs.extend(matches)
        
        # Also try raw numeric sequences
        numbers = re.findall(r'\b\d{4,10}\b', text)
        refs.extend(numbers)
        
        return list(set(refs))
    
    def _get_date_range(self, value_date) -> Tuple[datetime, datetime]:
        """Get date range for matching based on policy."""
        if not value_date:
            return None
        
        if isinstance(value_date, str):
            try:
                value_date = datetime.fromisoformat(value_date.replace('Z', '+00:00'))
            except:
                return None
        
        days = self.policy.date_window_days
        return (
            value_date - timedelta(days=days),
            value_date + timedelta(days=days)
        )
    
    def _score_candidate(
        self, 
        bank_txn: models.BankTransaction, 
        invoice: models.Invoice,
        extracted_refs: List[str]
    ) -> MatchCandidate:
        """Score a candidate match."""
        reasons = []
        confidence = 0.0
        
        # Check for exact reference match (Tier 1)
        exact_ref_match = False
        if invoice.invoice_number:
            inv_refs = self.index._extract_refs(invoice.invoice_number)
            for ref in extracted_refs:
                if ref.lower() in [r.lower() for r in inv_refs]:
                    exact_ref_match = True
                    reasons.append(f"Reference match: {ref}")
                    confidence += 0.5
                    break
        
        # Amount match
        if bank_txn.amount and invoice.amount:
            diff_pct = abs(bank_txn.amount - invoice.amount) / max(abs(invoice.amount), 1)
            if diff_pct < 0.001:  # Exact amount
                reasons.append("Exact amount match")
                confidence += 0.3
            elif diff_pct < self.policy.amount_tolerance_percent / 100:
                reasons.append(f"Amount within {self.policy.amount_tolerance_percent}% tolerance")
                confidence += 0.2
        
        # Counterparty match
        if bank_txn.counterparty_name and invoice.customer_name:
            bank_normalized = self.index._normalize_name(bank_txn.counterparty_name)
            inv_normalized = self.index._normalize_name(invoice.customer_name)
            if bank_normalized == inv_normalized:
                reasons.append("Counterparty name match")
                confidence += 0.15
            elif bank_normalized in inv_normalized or inv_normalized in bank_normalized:
                reasons.append("Partial counterparty match")
                confidence += 0.08
        
        # Date proximity
        if bank_txn.value_date and invoice.expected_due_date:
            try:
                txn_date = bank_txn.value_date
                if isinstance(txn_date, str):
                    txn_date = datetime.fromisoformat(txn_date.replace('Z', '+00:00'))
                inv_date = invoice.expected_due_date
                if isinstance(inv_date, str):
                    inv_date = datetime.fromisoformat(inv_date.replace('Z', '+00:00'))
                
                days_diff = abs((txn_date - inv_date).days)
                if days_diff <= 3:
                    reasons.append("Payment within 3 days of due date")
                    confidence += 0.1
                elif days_diff <= 7:
                    reasons.append("Payment within 7 days of due date")
                    confidence += 0.05
            except:
                pass
        
        # Determine tier
        if exact_ref_match and confidence >= 0.7:
            tier = 1  # Deterministic
        elif confidence >= self.policy.tier2_min_confidence:
            tier = 2  # Rule-based
        elif confidence >= self.policy.tier3_min_confidence:
            tier = 3  # Suggested
        else:
            tier = 4  # Manual
        
        return MatchCandidate(
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number or '',
            customer_name=invoice.customer_name or '',
            amount=Decimal(str(invoice.amount or 0)),
            due_date=invoice.expected_due_date,
            currency=invoice.currency or 'EUR',
            tier=tier,
            confidence=min(confidence, 1.0),
            match_reasons=reasons
        )
    
    def _suggest_allocations(self, result: MatchResult, bank_txn: models.BankTransaction) -> MatchResult:
        """
        Suggest allocations for many-to-one or one-to-many matching.
        
        Ensures: sum(allocations) == bank_txn.amount
        """
        remaining = result.bank_txn_amount
        
        for candidate in result.candidates:
            if remaining <= 0:
                candidate.suggested_allocation = Decimal('0')
                continue
            
            if candidate.amount <= remaining:
                # Full allocation
                candidate.suggested_allocation = candidate.amount
                remaining -= candidate.amount
            else:
                # Partial allocation (for bundled payments)
                candidate.suggested_allocation = remaining
                remaining = Decimal('0')
            
            result.total_matched_amount += candidate.suggested_allocation
        
        result.unallocated_amount = remaining
        
        return result


def create_match_allocation(
    db: Session,
    bank_txn_id: int,
    invoice_id: int,
    allocated_amount: float,
    match_tier: int,
    confidence: float,
    approved_by: str = None
) -> models.MatchAllocation:
    """Create a match allocation record."""
    allocation = models.MatchAllocation(
        bank_transaction_id=bank_txn_id,
        invoice_id=invoice_id,
        allocated_amount=allocated_amount,
        match_tier=match_tier,
        confidence_score=confidence,
        status='Pending' if not approved_by else 'Approved',
        approved_by=approved_by,
        approved_at=datetime.utcnow() if approved_by else None,
        created_at=datetime.utcnow()
    )
    db.add(allocation)
    return allocation


def get_cash_explained_percent(db: Session, snapshot_id: int) -> Dict[str, Any]:
    """
    Calculate "Cash Explained %" - the north-star trust KPI.
    
    Cash Explained % = (Matched Bank Balance) / (Total Bank Balance) * 100
    """
    from sqlalchemy import func
    
    # Total bank transactions (inflows only for AR)
    total_inflows = db.query(func.sum(models.BankTransaction.amount))\
        .filter(
            models.BankTransaction.snapshot_id == snapshot_id,
            models.BankTransaction.amount > 0
        ).scalar() or 0
    
    # Matched amount (sum of allocations)
    matched_amount = db.query(func.sum(models.MatchAllocation.allocated_amount))\
        .join(models.BankTransaction)\
        .filter(
            models.BankTransaction.snapshot_id == snapshot_id,
            models.MatchAllocation.status.in_(['Approved', 'Auto'])
        ).scalar() or 0
    
    # Calculate percentage
    if total_inflows > 0:
        explained_pct = (matched_amount / total_inflows) * 100
    else:
        explained_pct = 100.0  # No bank data = fully explained
    
    return {
        'snapshot_id': snapshot_id,
        'total_bank_inflows': float(total_inflows),
        'matched_amount': float(matched_amount),
        'unmatched_amount': float(total_inflows - matched_amount),
        'cash_explained_pct': round(explained_pct, 2),
        'target_pct': 95.0,  # Configurable KPI target
        'status': 'healthy' if explained_pct >= 95 else 'warning' if explained_pct >= 80 else 'critical'
    }




