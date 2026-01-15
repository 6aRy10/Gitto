"""
Reconciliation Service V2

Rebuilt with:
- Blocking indexes for candidate generation (O(n*k) not O(n*m))
- Embedding similarity for suggested matches (never auto-apply)
- Constrained solver for many-to-many allocation
- Performance optimized for 50k+ transactions
"""

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import models

# For constrained optimization
try:
    from scipy.optimize import linprog
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("WARNING: scipy not available, using fallback solver")

# For embeddings (simple TF-IDF based similarity, can be replaced with actual embeddings)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
try:
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("WARNING: sklearn not available, using fallback similarity")


@dataclass
class MatchCandidate:
    """A candidate match between transaction and invoice."""
    invoice_id: int
    invoice_number: str
    customer_name: str
    open_amount: float  # Remaining unpaid amount
    due_date: Optional[datetime]
    currency: str
    
    # Match quality signals
    ref_match: bool = False  # Invoice ref found in transaction reference
    amount_match: bool = False  # Amount within tolerance
    date_match: bool = False  # Date within window
    counterparty_match: bool = False  # Counterparty name matches
    
    # Scoring
    confidence: float = 0.0
    match_type: str = "candidate"  # "deterministic", "rule", "suggested"
    
    # For many-to-many
    suggested_allocation: Optional[float] = None


@dataclass
class AllocationSolution:
    """Solution from constrained solver for many-to-many allocation."""
    allocations: Dict[int, float]  # invoice_id -> allocated_amount
    fees: float = 0.0
    writeoffs: float = 0.0
    unallocated: float = 0.0
    is_optimal: bool = True
    solver_status: str = "optimal"


class BlockingIndex:
    """
    Blocking index for efficient candidate generation.
    
    Blocks by:
    - Extracted invoice references (from transaction reference text)
    - Amount buckets (rounded to configurable precision)
    - Counterparty key (normalized name)
    - Date window (week-based)
    """
    
    def __init__(self, amount_bucket_size: float = 100.0, date_window_days: int = 7):
        self.amount_bucket_size = amount_bucket_size
        self.date_window_days = date_window_days
        
        # Indexes
        self.by_ref: Dict[str, Set[int]] = defaultdict(set)
        self.by_amount_bucket: Dict[int, Set[int]] = defaultdict(set)
        self.by_counterparty: Dict[str, Set[int]] = defaultdict(set)
        self.by_date_week: Dict[str, Set[int]] = defaultdict(set)
        
        # Invoice metadata
        self.invoices: Dict[int, models.Invoice] = {}
        self.invoice_open_amounts: Dict[int, float] = {}  # invoice_id -> open_amount
    
    def build(self, invoices: List[models.Invoice], db: Session):
        """Build blocking index from invoices."""
        self.clear()
        
        for inv in invoices:
            if inv.payment_date is not None:
                continue  # Skip paid invoices
            
            self.invoices[inv.id] = inv
            
            # Calculate open amount (invoice amount - existing allocations)
            existing_allocations = db.query(func.sum(models.ReconciliationTable.amount_allocated)).filter(
                models.ReconciliationTable.invoice_id == inv.id
            ).scalar() or 0.0
            
            open_amount = float(inv.amount or 0) - float(existing_allocations)
            self.invoice_open_amounts[inv.id] = max(0.0, open_amount)
            
            # Index by extracted invoice references
            if inv.document_number:
                refs = self._extract_refs(str(inv.document_number))
                for ref in refs:
                    self.by_ref[ref].add(inv.id)
            
            # Index by amount bucket
            if inv.amount:
                bucket = int(float(inv.amount) / self.amount_bucket_size) * int(self.amount_bucket_size)
                self.by_amount_bucket[bucket].add(inv.id)
                # Also index adjacent buckets for tolerance
                self.by_amount_bucket[bucket - int(self.amount_bucket_size)].add(inv.id)
                self.by_amount_bucket[bucket + int(self.amount_bucket_size)].add(inv.id)
            
            # Index by counterparty (normalized)
            if inv.customer:
                counterparty_key = self._normalize_counterparty(str(inv.customer))
                self.by_counterparty[counterparty_key].add(inv.id)
            
            # Index by date week
            if inv.expected_due_date:
                week_key = self._get_week_key(inv.expected_due_date)
                self.by_date_week[week_key].add(inv.id)
                # Also index adjacent weeks for tolerance
                try:
                    year, week = week_key.split("-W")
                    week_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                    prev_week_date = week_date - timedelta(days=7)
                    next_week_date = week_date + timedelta(days=7)
                    prev_year, prev_week, _ = prev_week_date.isocalendar()
                    next_year, next_week, _ = next_week_date.isocalendar()
                    prev_week_key = f"{prev_year}-W{prev_week:02d}"
                    next_week_key = f"{next_year}-W{next_week:02d}"
                    self.by_date_week[prev_week_key].add(inv.id)
                    self.by_date_week[next_week_key].add(inv.id)
                except:
                    pass  # Skip if date parsing fails
    
    def query_candidates(
        self,
        txn: models.BankTransaction,
        amount_tolerance: float = 0.02,
        date_window_days: int = 7
    ) -> Set[int]:
        """
        Query blocking index for candidate invoice IDs.
        
        Uses set intersection for multi-block filtering.
        """
        candidates = None
        
        # Block 1: Extracted invoice references
        txn_refs = self._extract_refs(str(txn.reference or ""))
        if txn_refs:
            ref_candidates = set()
            for ref in txn_refs:
                ref_candidates.update(self.by_ref.get(ref, set()))
            if ref_candidates:
                candidates = ref_candidates
        
        # Block 2: Amount bucket
        if txn.amount:
            amount_bucket = int(abs(float(txn.amount)) / self.amount_bucket_size) * int(self.amount_bucket_size)
            amount_candidates = set()
            for bucket in [amount_bucket - int(self.amount_bucket_size), amount_bucket, amount_bucket + int(self.amount_bucket_size)]:
                amount_candidates.update(self.by_amount_bucket.get(bucket, set()))
            
            # Filter by actual tolerance
            amount_candidates = {
                inv_id for inv_id in amount_candidates
                if self._within_amount_tolerance(
                    abs(txn.amount),
                    self.invoices[inv_id].amount,
                    amount_tolerance
                )
            }
            
            if candidates is None:
                candidates = amount_candidates
            else:
                candidates = candidates & amount_candidates
        
        # Block 3: Counterparty
        if txn.counterparty:
            counterparty_key = self._normalize_counterparty(str(txn.counterparty))
            counterparty_candidates = self.by_counterparty.get(counterparty_key, set())
            
            if candidates is None:
                candidates = counterparty_candidates
            elif counterparty_candidates:
                candidates = candidates & counterparty_candidates
        
        # Block 4: Date window
        if txn.transaction_date:
            txn_week = self._get_week_key(txn.transaction_date)
            date_candidates = set()
            
            # Check current week and adjacent weeks
            try:
                # Parse week key (format: YYYY-WWW)
                year, week = txn_week.split("-W")
                # Create date from ISO week
                txn_week_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                for week_offset in [-1, 0, 1]:
                    week_date = txn_week_date + timedelta(weeks=week_offset)
                    year, week, _ = week_date.isocalendar()
                    week_key = f"{year}-W{week:02d}"
                    date_candidates.update(self.by_date_week.get(week_key, set()))
            except:
                # Fallback: use all date candidates if parsing fails
                date_candidates.update(self.by_date_week.get(txn_week, set()))
            
            # Filter by actual date window
            date_candidates = {
                inv_id for inv_id in date_candidates
                if self.invoices[inv_id].expected_due_date and
                abs((txn.transaction_date - self.invoices[inv_id].expected_due_date).days) <= date_window_days
            }
            
            if candidates is None:
                candidates = date_candidates
            elif date_candidates:
                candidates = candidates & date_candidates
        
        return candidates or set()
    
    def _extract_refs(self, text: str) -> List[str]:
        """Extract invoice reference numbers from text."""
        if not text:
            return []
        
        refs = []
        text_upper = text.upper()
        
        # Pattern: INV-XXX, INVOICE-XXX, #XXX, etc.
        patterns = [
            r'INV[-\s]?(\d+)',
            r'INVOICE[-\s]?(\d+)',
            r'#(\d+)',
            r'REF[-\s]?(\d+)',
            r'DOC[-\s]?(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_upper)
            for match in matches:
                refs.append(f"INV-{match}")
                refs.append(match)  # Also add raw number
        
        # Also try to find any sequence of digits that might be invoice number
        digit_sequences = re.findall(r'\d{4,}', text_upper)
        for seq in digit_sequences:
            refs.append(seq)
        
        return list(set(refs))  # Deduplicate
    
    def _normalize_counterparty(self, name: str) -> str:
        """Normalize counterparty name for matching."""
        if not name:
            return ""
        
        # Lowercase, remove special chars, normalize whitespace
        normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common suffixes
        suffixes = [' inc', ' ltd', ' llc', ' corp', ' corporation', ' limited']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        return normalized
    
    def _get_week_key(self, date: datetime) -> str:
        """Get week key for date indexing."""
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except:
                date = datetime.strptime(date, "%Y-%m-%d")
        # Use ISO week format: YYYY-WWW
        year, week, _ = date.isocalendar()
        return f"{year}-W{week:02d}"
    
    def _within_amount_tolerance(self, amount1: float, amount2: float, tolerance: float) -> bool:
        """Check if two amounts are within tolerance."""
        if amount2 == 0:
            return False
        relative_diff = abs(amount1 - amount2) / abs(amount2)
        return relative_diff <= tolerance
    
    def clear(self):
        """Clear all indexes."""
        self.by_ref.clear()
        self.by_amount_bucket.clear()
        self.by_counterparty.clear()
        self.by_date_week.clear()
        self.invoices.clear()
        self.invoice_open_amounts.clear()


class EmbeddingSimilarityMatcher:
    """
    Embedding-based similarity matcher for suggested matches.
    Uses TF-IDF vectors and cosine similarity.
    """
    
    def __init__(self):
        self.vectorizer = None
        self.invoice_vectors = None
        self.invoice_ids = None
    
    def build(self, invoices: List[models.Invoice]):
        """Build embedding vectors for invoices."""
        if not SKLEARN_AVAILABLE:
            return
        
        # Create text features for each invoice
        texts = []
        self.invoice_ids = []
        
        for inv in invoices:
            if inv.payment_date is not None:
                continue
            
            # Combine invoice features into text
            text_parts = []
            if inv.document_number:
                text_parts.append(str(inv.document_number))
            if inv.customer:
                text_parts.append(str(inv.customer))
            if inv.project:
                text_parts.append(str(inv.project))
            
            text = " ".join(text_parts)
            texts.append(text)
            self.invoice_ids.append(inv.id)
        
        if not texts:
            return
        
        # Build TF-IDF vectors
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.invoice_vectors = self.vectorizer.fit_transform(texts)
    
    def find_similar(
        self,
        txn: models.BankTransaction,
        candidate_ids: Set[int],
        top_k: int = 5,
        min_similarity: float = 0.3
    ) -> List[Tuple[int, float]]:
        """
        Find similar invoices using embedding similarity.
        
        Returns:
            List of (invoice_id, similarity_score) tuples, sorted by similarity
        """
        if not SKLEARN_AVAILABLE or self.vectorizer is None or self.invoice_vectors is None:
            return []
        
        # Create text for transaction
        txn_text_parts = []
        if txn.reference:
            txn_text_parts.append(str(txn.reference))
        if txn.counterparty:
            txn_text_parts.append(str(txn.counterparty))
        
        txn_text = " ".join(txn_text_parts)
        if not txn_text:
            return []
        
        # Vectorize transaction
        txn_vector = self.vectorizer.transform([txn_text])
        
        # Calculate similarity with candidate invoices
        similarities = []
        for idx, inv_id in enumerate(self.invoice_ids):
            if inv_id not in candidate_ids:
                continue
            
            similarity = cosine_similarity(txn_vector, self.invoice_vectors[idx:idx+1])[0][0]
            if similarity >= min_similarity:
                similarities.append((inv_id, float(similarity)))
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


class ConstrainedAllocationSolver:
    """
    Constrained solver for many-to-many allocation.
    
    Constraints:
    - Sum of allocations per transaction = transaction amount
    - Allocations to invoice <= open_amount
    - Handle fees and writeoffs explicitly
    """
    
    def solve(
        self,
        txn_amount: float,
        candidates: List[MatchCandidate],
        fees: float = 0.0,
        writeoffs: float = 0.0
    ) -> AllocationSolution:
        """
        Solve allocation problem using linear programming.
        
        Objective: Maximize total allocation (prefer larger matches)
        Constraints:
        1. Sum(allocations) + fees + writeoffs = txn_amount
        2. allocation[i] <= open_amount[i] for each invoice
        3. allocation[i] >= 0 for each invoice
        """
        if not candidates:
            return AllocationSolution(
                allocations={},
                fees=fees,
                writeoffs=writeoffs,
                unallocated=abs(txn_amount) - fees - writeoffs,
                is_optimal=False,
                solver_status="no_candidates"
            )
        
        txn_abs = abs(txn_amount)
        net_amount = txn_abs - fees - writeoffs
        
        if net_amount <= 0:
            return AllocationSolution(
                allocations={},
                fees=fees,
                writeoffs=writeoffs,
                unallocated=0.0,
                is_optimal=True,
                solver_status="fully_allocated_to_fees"
            )
        
        # If scipy not available, use greedy allocation
        if not SCIPY_AVAILABLE:
            return self._greedy_allocation(txn_abs, candidates, fees, writeoffs)
        
        # Build linear programming problem
        n = len(candidates)
        
        # Objective: Maximize sum of allocations (negative for minimization)
        c = [-1.0] * n
        
        # Constraint 1: Sum of allocations = net_amount
        A_eq = [[1.0] * n]
        b_eq = [net_amount]
        
        # Constraint 2: Each allocation <= open_amount
        A_ub = []
        b_ub = []
        for cand in candidates:
            A_ub.append([0.0] * n)
            A_ub[-1][candidates.index(cand)] = 1.0
            b_ub.append(cand.open_amount)
        
        # Bounds: allocations >= 0
        bounds = [(0, None)] * n
        
        try:
            result = linprog(
                c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                bounds=bounds, method='highs'
            )
            
            if result.success:
                allocations = {}
                for i, cand in enumerate(candidates):
                    alloc = float(result.x[i])
                    if alloc > 0.01:  # Only include non-trivial allocations
                        allocations[cand.invoice_id] = alloc
                
                return AllocationSolution(
                    allocations=allocations,
                    fees=fees,
                    writeoffs=writeoffs,
                    unallocated=net_amount - sum(allocations.values()),
                    is_optimal=True,
                    solver_status="optimal"
                )
            else:
                # Fallback to greedy
                return self._greedy_allocation(txn_abs, candidates, fees, writeoffs)
        except Exception as e:
            # Fallback to greedy on error
            return self._greedy_allocation(txn_abs, candidates, fees, writeoffs)
    
    def _greedy_allocation(
        self,
        txn_amount: float,
        candidates: List[MatchCandidate],
        fees: float,
        writeoffs: float
    ) -> AllocationSolution:
        """Greedy allocation fallback when solver unavailable."""
        net_amount = abs(txn_amount) - fees - writeoffs
        allocations = {}
        remaining = net_amount
        
        # Sort by confidence (highest first)
        sorted_candidates = sorted(candidates, key=lambda c: c.confidence, reverse=True)
        
        for cand in sorted_candidates:
            if remaining <= 0.01:
                break
            
            alloc = min(remaining, cand.open_amount)
            if alloc > 0.01:
                allocations[cand.invoice_id] = alloc
                remaining -= alloc
        
        return AllocationSolution(
            allocations=allocations,
            fees=fees,
            writeoffs=writeoffs,
            unallocated=remaining,
            is_optimal=False,
            solver_status="greedy_fallback"
        )


class ReconciliationServiceV2:
    """
    Rebuilt reconciliation service with blocking indexes, embedding similarity, and constrained solver.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.blocking_index = BlockingIndex()
        self.embedding_matcher = EmbeddingSimilarityMatcher()
        self.allocation_solver = ConstrainedAllocationSolver()
    
    def reconcile_entity(self, entity_id: int) -> Dict[str, Any]:
        """
        Reconcile all unreconciled transactions for an entity.
        
        Returns:
            Dict with reconciliation results and statistics
        """
        # Get unreconciled transactions
        unreconciled_txns = self.db.query(models.BankTransaction).join(
            models.BankAccount
        ).filter(
            models.BankTransaction.is_reconciled == 0,
            models.BankAccount.entity_id == entity_id
        ).all()
        
        # Get open invoices
        open_invoices = self.db.query(models.Invoice).filter(
            models.Invoice.entity_id == entity_id,
            models.Invoice.payment_date == None
        ).all()
        
        if not open_invoices:
            return {
                "status": "no_invoices",
                "transactions_processed": 0,
                "matches": []
            }
        
        # Build indexes
        self.blocking_index.build(open_invoices, self.db)
        self.embedding_matcher.build(open_invoices)
        
        # Get matching policy
        from matching_policy_service import get_matching_policy
        currency = "EUR"  # Default, should get from entity
        policy = get_matching_policy(self.db, entity_id, currency)
        
        results = {
            "deterministic": 0,
            "rule_based": 0,
            "suggested": 0,
            "manual": 0,
            "many_to_many": 0,
            "matches": []
        }
        
        # Process each transaction
        for txn in unreconciled_txns:
            match_result = self._reconcile_transaction(txn, policy)
            results[match_result["type"]] += 1
            results["matches"].append(match_result)
            
            if match_result["type"] == "many_to_many":
                results["many_to_many"] += 1
        
        return results
    
    def _reconcile_transaction(
        self,
        txn: models.BankTransaction,
        policy
    ) -> Dict[str, Any]:
        """Reconcile a single transaction."""
        
        # Step 1: Generate candidates using blocking index
        candidates = self._generate_candidates(txn, policy)
        
        if not candidates:
            # No candidates - manual queue
            txn.reconciliation_type = "Manual"
            txn.lifecycle_status = "New"
            self.db.commit()
            return {
                "txn_id": txn.id,
                "type": "manual",
                "reason": "no_candidates"
            }
        
        # Step 2: Classify candidates by match type
        deterministic_candidates = [c for c in candidates if c.match_type == "deterministic"]
        rule_candidates = [c for c in candidates if c.match_type == "rule"]
        suggested_candidates = [c for c in candidates if c.match_type == "suggested"]
        
        # Step 3: Try deterministic match (auto-apply)
        if deterministic_candidates and policy.deterministic_enabled:
            best = max(deterministic_candidates, key=lambda c: c.confidence)
            if best.confidence >= 0.95:
                self._apply_match(txn, [best], "Deterministic", best.confidence)
                return {
                    "txn_id": txn.id,
                    "type": "deterministic",
                    "invoice_id": best.invoice_id,
                    "confidence": best.confidence
                }
        
        # Step 4: Try rule-based match (auto-apply if policy allows)
        if rule_candidates and policy.rules_enabled:
            best = max(rule_candidates, key=lambda c: c.confidence)
            if best.confidence >= policy.tier2_min_confidence and policy.auto_apply_tier2:
                self._apply_match(txn, [best], "Rule", best.confidence)
                return {
                    "txn_id": txn.id,
                    "type": "rule_based",
                    "invoice_id": best.invoice_id,
                    "confidence": best.confidence
                }
        
        # Step 5: Check for many-to-many matches
        all_candidates = deterministic_candidates + rule_candidates
        if len(all_candidates) > 1:
            # Try to allocate across multiple invoices
            solution = self.allocation_solver.solve(
                txn.amount,
                all_candidates,
                fees=0.0,  # Could extract from transaction
                writeoffs=0.0
            )
            
            if solution.allocations and len(solution.allocations) > 1:
                # Many-to-many match found
                allocation_candidates = [
                    c for c in all_candidates
                    if c.invoice_id in solution.allocations
                ]
                self._apply_many_to_many_match(txn, allocation_candidates, solution, "Rule")
                return {
                    "txn_id": txn.id,
                    "type": "many_to_many",
                    "invoice_count": len(solution.allocations),
                    "allocations": solution.allocations
                }
        
        # Step 6: Generate suggested matches using embedding similarity (never auto-apply)
        if suggested_candidates or (policy.suggested_enabled and not all_candidates):
            # Use embedding similarity for suggestions
            candidate_ids = {c.invoice_id for c in all_candidates}
            similar = self.embedding_matcher.find_similar(
                txn,
                candidate_ids,
                top_k=5,
                min_similarity=0.3
            )
            
            if similar:
                # Mark as suggested (requires approval)
                txn.reconciliation_type = "Suggested"
                txn.match_confidence = similar[0][1]
                txn.lifecycle_status = "New"
                self.db.commit()
                return {
                    "txn_id": txn.id,
                    "type": "suggested",
                    "candidate_count": len(similar),
                    "top_confidence": similar[0][1]
                }
        
        # Step 7: Manual queue
        txn.reconciliation_type = "Manual"
        txn.lifecycle_status = "New"
        self.db.commit()
        return {
            "txn_id": txn.id,
            "type": "manual",
            "reason": "no_auto_match"
        }
    
    def _generate_candidates(
        self,
        txn: models.BankTransaction,
        policy
    ) -> List[MatchCandidate]:
        """Generate match candidates using blocking index."""
        # Query blocking index
        candidate_ids = self.blocking_index.query_candidates(
            txn,
            amount_tolerance=policy.amount_tolerance,
            date_window_days=policy.date_window_days
        )
        
        candidates = []
        for inv_id in candidate_ids:
            inv = self.blocking_index.invoices[inv_id]
            open_amount = self.blocking_index.invoice_open_amounts[inv_id]
            
            if open_amount <= 0.01:
                continue  # Invoice fully paid
            
            cand = MatchCandidate(
                invoice_id=inv.id,
                invoice_number=inv.document_number or "",
                customer_name=inv.customer or "",
                open_amount=open_amount,
                due_date=inv.expected_due_date,
                currency=inv.currency or "EUR"
            )
            
            # Check match signals
            txn_ref = str(txn.reference or "").upper()
            inv_ref = str(inv.document_number or "").upper()
            
            # Ref match
            if inv_ref and (inv_ref in txn_ref or txn_ref in inv_ref):
                cand.ref_match = True
                cand.confidence += 0.5
                cand.match_type = "deterministic"
            
            # Amount match
            if abs(abs(txn.amount) - inv.amount) / inv.amount <= policy.amount_tolerance:
                cand.amount_match = True
                cand.confidence += 0.3
            
            # Date match
            if inv.expected_due_date and txn.transaction_date:
                days_diff = abs((txn.transaction_date - inv.expected_due_date).days)
                if days_diff <= policy.date_window_days:
                    cand.date_match = True
                    cand.confidence += 0.1
            
            # Counterparty match
            if txn.counterparty and inv.customer:
                txn_cp = self.blocking_index._normalize_counterparty(str(txn.counterparty))
                inv_cp = self.blocking_index._normalize_counterparty(str(inv.customer))
                if txn_cp == inv_cp:
                    cand.counterparty_match = True
                    cand.confidence += 0.1
            
            # Classify match type
            if cand.match_type != "deterministic":
                if cand.amount_match and cand.date_match:
                    cand.match_type = "rule"
                    cand.confidence = max(cand.confidence, 0.7)
                else:
                    cand.match_type = "suggested"
                    cand.confidence = max(cand.confidence, 0.4)
            
            candidates.append(cand)
        
        return candidates
    
    def _apply_match(
        self,
        txn: models.BankTransaction,
        candidates: List[MatchCandidate],
        match_type: str,
        confidence: float
    ):
        """Apply a single match."""
        if not candidates:
            return
        
        cand = candidates[0]  # Take first candidate
        inv = self.blocking_index.invoices[cand.invoice_id]
        
        allocation = min(abs(txn.amount), cand.open_amount)
        
        recon = models.ReconciliationTable(
            bank_transaction_id=txn.id,
            invoice_id=inv.id,
            amount_allocated=allocation,
            match_type=match_type,
            confidence=confidence
        )
        self.db.add(recon)
        
        txn.is_reconciled = 1
        txn.reconciliation_type = match_type
        txn.match_confidence = confidence
        txn.lifecycle_status = "Resolved"
        txn.resolved_at = datetime.now(timezone.utc)
        
        inv.truth_label = "reconciled"
        
        self.db.commit()
    
    def _apply_many_to_many_match(
        self,
        txn: models.BankTransaction,
        candidates: List[MatchCandidate],
        solution: AllocationSolution,
        match_type: str
    ):
        """Apply many-to-many match using solver solution."""
        # Validate solution
        total_allocated = sum(solution.allocations.values())
        expected = abs(txn.amount) - solution.fees - solution.writeoffs
        
        if abs(total_allocated - expected) > 0.01:
            raise ValueError(f"Allocation mismatch: {total_allocated} vs {expected}")
        
        # Create reconciliation records
        for cand in candidates:
            if cand.invoice_id not in solution.allocations:
                continue
            
            alloc = solution.allocations[cand.invoice_id]
            inv = self.blocking_index.invoices[cand.invoice_id]
            
            # Validate allocation doesn't exceed open amount
            if alloc > cand.open_amount + 0.01:
                raise ValueError(
                    f"Allocation {alloc} exceeds open amount {cand.open_amount} for invoice {inv.id}"
                )
            
            recon = models.ReconciliationTable(
                bank_transaction_id=txn.id,
                invoice_id=inv.id,
                amount_allocated=alloc,
                match_type=match_type,
                confidence=cand.confidence
            )
            self.db.add(recon)
            
            inv.truth_label = "reconciled"
        
        txn.is_reconciled = 1
        txn.reconciliation_type = match_type
        txn.match_confidence = min(c.confidence for c in candidates) if candidates else 0.8
        txn.lifecycle_status = "Resolved"
        txn.resolved_at = datetime.now(timezone.utc)
        
        self.db.commit()

