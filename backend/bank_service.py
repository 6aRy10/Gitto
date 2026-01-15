from sqlalchemy.orm import Session
import models
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib

def build_invoice_indexes(invoices: List[models.Invoice]) -> Dict:
    """
    P1 Fix: Build indexes for O(1) lookups instead of O(n) scans.
    
    Returns:
        {
            'by_document_number': {doc_num: [invoice, ...], ...},
            'by_amount': {amount_bucket: [invoice, ...], ...},
            'by_customer': {customer_name: [invoice, ...], ...},
            'all_invoices': [invoice, ...]  # For fallback
        }
    """
    indexes = {
        'by_document_number': {},
        'by_amount': {},
        'by_customer': {},
        'all_invoices': invoices
    }
    
    for inv in invoices:
        # Index by document number (for Tier 1 matching)
        if inv.document_number:
            doc_num = str(inv.document_number).upper().strip()
            if doc_num:
                if doc_num not in indexes['by_document_number']:
                    indexes['by_document_number'][doc_num] = []
                indexes['by_document_number'][doc_num].append(inv)
        
        # Index by amount bucket (for Tier 2 matching)
        if inv.amount is not None and inv.payment_date is None:
            try:
                amount_bucket = round(float(inv.amount), 2)
                if amount_bucket not in indexes['by_amount']:
                    indexes['by_amount'][amount_bucket] = []
                indexes['by_amount'][amount_bucket].append(inv)
            except (TypeError, ValueError):
                pass
        
        # Index by customer name (for Tier 3 fuzzy matching)
        if inv.customer and inv.payment_date is None:
            customer_name = str(inv.customer).lower().strip()
            if customer_name:
                if customer_name not in indexes['by_customer']:
                    indexes['by_customer'][customer_name] = []
                indexes['by_customer'][customer_name].append(inv)
    
    return indexes

def find_deterministic_match_optimized(txn: models.BankTransaction, indexes: Dict, amount_tolerance: float = 0.01) -> Optional[models.Invoice]:
    """
    P1 Fix: Optimized deterministic match using document_number index.
    O(1) lookup instead of O(n) scan.
    """
    ref = str(txn.reference or "").upper().strip()
    if not ref:
        return None
    
    # Try exact match first
    if ref in indexes['by_document_number']:
        for inv in indexes['by_document_number'][ref]:
            if inv and inv.amount is not None and inv.payment_date is None:
                if abs(txn.amount - inv.amount) < 0.01:
                    return inv
    
    # Try substring match
    for doc_num, invoices in indexes['by_document_number'].items():
        if doc_num in ref or ref in doc_num:
            for inv in invoices:
                if inv and inv.amount is not None and inv.payment_date is None:
                    if abs(txn.amount - inv.amount) < amount_tolerance:
                        return inv
    
    return None

def find_rules_match_optimized(txn: models.BankTransaction, indexes: Dict, amount_tolerance: float = 0.01, date_window_days: int = 30) -> Optional[models.Invoice]:
    """
    P1 Fix: Optimized rules match using amount index.
    """
    txn_date = txn.transaction_date
    if not txn_date:
        return None
    
    amount_bucket = round(txn.amount, 2)
    
    candidates = []
    for check_amount in [amount_bucket, amount_bucket + 0.01, amount_bucket - 0.01]:
        if check_amount in indexes['by_amount']:
            candidates.extend(indexes['by_amount'][check_amount])
    
    for inv in candidates:
        if inv.expected_due_date:
            days_diff = abs((txn_date - inv.expected_due_date).days)
            if days_diff <= date_window_days:
                return inv
    
    return None

def find_suggested_matches_optimized(txn: models.BankTransaction, indexes: Dict) -> List[Dict]:
    """
    P1 Fix: Optimized suggested matches using customer and amount indexes.
    """
    suggestions = []
    txn_ref = str(txn.reference or "").lower()
    txn_counterparty = str(txn.counterparty or "").lower()
    txn_amount = txn.amount
    
    checked_invoices = set()
    
    if txn_counterparty:
        for customer_name, invoices in indexes['by_customer'].items():
            if customer_name in txn_ref or customer_name in txn_counterparty:
                for inv in invoices:
                    if inv.id not in checked_invoices:
                        checked_invoices.add(inv.id)
                        confidence = 0.5
                        
                        if abs(txn_amount - inv.amount) < 0.01:
                            confidence += 0.4
                        
                        if confidence >= 0.5:
                            suggestions.append({"invoice": inv, "confidence": confidence})
    
    amount_bucket = round(txn_amount, 2)
    if amount_bucket in indexes['by_amount']:
        for inv in indexes['by_amount'][amount_bucket]:
            if inv.id not in checked_invoices:
                checked_invoices.add(inv.id)
                confidence = 0.4
                
                if inv.customer:
                    customer = str(inv.customer).lower()
                    if customer in txn_ref or customer in txn_counterparty:
                        confidence += 0.5
                
                if confidence >= 0.5:
                    suggestions.append({"invoice": inv, "confidence": confidence})
    
    return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)

def generate_match_ladder(db: Session, entity_id: int):
    """
    Executes the 4-tier reconciliation ladder:
    1. Deterministic (Exact Reference)
    2. Rules-based (Amount + Entity + Date Window)
    3. Suggested (Fuzzy similarity)
    4. Manual (User Queue)
    """
    unreconciled_txns = db.query(models.BankTransaction).join(
        models.BankAccount
    ).filter(
        models.BankTransaction.is_reconciled == 0,
        models.BankAccount.entity_id == entity_id
    ).all()

    open_invoices = db.query(models.Invoice).filter(
        models.Invoice.entity_id == entity_id,
        models.Invoice.payment_date == None
    ).all()

    invoice_indexes = build_invoice_indexes(open_invoices)

    match_results = []

    for txn in unreconciled_txns:
        from matching_policy_service import get_matching_policy
        currency = txn.currency or "EUR"
        policy = get_matching_policy(db, entity_id, currency)
        
        # Try bundled invoice matching first (many-to-many)
        bundled_matches = find_bundled_invoice_matches(db, txn, open_invoices, policy.amount_tolerance)
        if bundled_matches and len(bundled_matches[0]) > 1:
            # Found a bundled payment - suggest for approval
            txn.reconciliation_type = "Suggested (Bundled)"
            txn.match_confidence = 0.85
            db.commit()
            match_results.append({
                "txn_id": txn.id, 
                "match_type": "Suggested (Bundled)", 
                "invoice_count": len(bundled_matches[0]),
                "confidence": 0.85
            })
            continue
        
        # Tier 1: Deterministic (Exact Reference Match)
        if policy.deterministic_enabled:
            tier1_match = find_deterministic_match_optimized(txn, invoice_indexes, policy.amount_tolerance)
            if tier1_match:
                record_match(db, txn, tier1_match, "Deterministic", 1.0)
                match_results.append({"txn_id": txn.id, "match_type": "Deterministic", "invoice_id": tier1_match.id, "confidence": 1.0})
                continue

        # Tier 2: Rules-based (Amount +/- tolerance + Date Window)
        if policy.rules_enabled:
            tier2_match = find_rules_match_optimized(txn, invoice_indexes, policy.amount_tolerance, policy.date_window_days)
            if tier2_match:
                record_match(db, txn, tier2_match, "Rule", 0.9)
                match_results.append({"txn_id": txn.id, "match_type": "Rule", "invoice_id": tier2_match.id, "confidence": 0.9})
                continue

        # Tier 3: Suggested (Fuzzy/Familiarity)
        if policy.suggested_enabled:
            tier3_matches = find_suggested_matches_optimized(txn, invoice_indexes)
            if tier3_matches:
                txn.reconciliation_type = "Suggested"
                txn.match_confidence = tier3_matches[0]['confidence']
                db.commit()
                match_results.append({"txn_id": txn.id, "match_type": "Suggested", "options": len(tier3_matches), "confidence": tier3_matches[0]['confidence']})
                continue

        # Tier 4: Manual (Unmatched Queue)
        txn.reconciliation_type = "Manual"
        txn.lifecycle_status = "New"
        db.commit()

    return match_results

# Backward compatibility wrappers
def find_deterministic_match(txn: models.BankTransaction, invoices: List[models.Invoice]):
    """DEPRECATED: Use find_deterministic_match_optimized with indexes instead."""
    indexes = build_invoice_indexes(invoices)
    return find_deterministic_match_optimized(txn, indexes)

def find_rules_match(txn: models.BankTransaction, invoices: List[models.Invoice]):
    """DEPRECATED: Use find_rules_match_optimized with indexes instead."""
    indexes = build_invoice_indexes(invoices)
    return find_rules_match_optimized(txn, indexes)

def find_suggested_matches(txn: models.BankTransaction, invoices: List[models.Invoice]):
    """DEPRECATED: Use find_suggested_matches_optimized with indexes instead."""
    indexes = build_invoice_indexes(invoices)
    return find_suggested_matches_optimized(txn, indexes)

def record_match(db: Session, txn: models.BankTransaction, inv: models.Invoice, match_type: str, confidence: float, amount_allocated: float = None):
    """Commits a match to the database. Supports partial allocations for many-to-many matching."""
    allocation = amount_allocated if amount_allocated is not None else txn.amount
    
    recon = models.ReconciliationTable(
        bank_transaction_id=txn.id,
        invoice_id=inv.id,
        amount_allocated=allocation,
        match_type=match_type,
        confidence=confidence
    )
    db.add(recon)
    
    txn.is_reconciled = 1
    txn.reconciliation_type = match_type
    txn.match_confidence = confidence
    txn.lifecycle_status = "Resolved"
    txn.resolved_at = datetime.utcnow()
    
    # Update invoice truth label
    inv.truth_label = "reconciled"
    
    # CRITICAL FIX: Only update payment_date if snapshot is not locked
    snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == inv.snapshot_id).first()
    if snapshot and not snapshot.is_locked:
        inv.payment_date = txn.transaction_date
    
    db.commit()


# ========== MANY-TO-MANY MATCHING ==========

def record_many_to_many_match(
    db: Session, 
    txn: models.BankTransaction, 
    invoices_with_allocations: List[Dict],
    match_type: str,
    confidence: float,
    user: str = "system"
):
    """
    Many-to-Many Matching: One bank transaction matched to multiple invoices.
    
    Args:
        txn: Bank transaction
        invoices_with_allocations: List of {"invoice": Invoice, "amount": float}
        match_type: Deterministic, Rule, Manual
        confidence: Match confidence score
        user: User performing the match
    
    Raises:
        ValueError: If allocations don't sum to transaction amount
    """
    total_allocated = sum(item["amount"] for item in invoices_with_allocations)
    if abs(total_allocated - abs(txn.amount)) > 0.01:
        raise ValueError(
            f"Allocation mismatch: allocated {total_allocated} but transaction is {txn.amount}. "
            f"Sum(allocations) must equal transaction amount."
        )
    
    # Validate: No over-allocation per invoice
    for item in invoices_with_allocations:
        inv = item["invoice"]
        alloc = item["amount"]
        
        existing_allocs = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.invoice_id == inv.id
        ).all()
        existing_total = sum(a.amount_allocated for a in existing_allocs)
        
        if existing_total + alloc > inv.amount + 0.01:
            raise ValueError(
                f"Over-allocation: Invoice {inv.document_number} amount is {inv.amount}, "
                f"existing allocations {existing_total}, new allocation {alloc} would exceed total."
            )
    
    # Create reconciliation records
    records = []
    for item in invoices_with_allocations:
        inv = item["invoice"]
        alloc = item["amount"]
        
        recon = models.ReconciliationTable(
            bank_transaction_id=txn.id,
            invoice_id=inv.id,
            amount_allocated=alloc,
            match_type=match_type,
            confidence=confidence,
            created_by=user
        )
        db.add(recon)
        records.append(recon)
        
        inv.truth_label = "reconciled"
        
        # Check if invoice is fully paid
        existing_allocs = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.invoice_id == inv.id
        ).all()
        total_paid = sum(a.amount_allocated for a in existing_allocs) + alloc
        
        if total_paid >= inv.amount - 0.01:
            snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == inv.snapshot_id).first()
            if snapshot and not snapshot.is_locked:
                inv.payment_date = txn.transaction_date
    
    txn.is_reconciled = 1
    txn.reconciliation_type = match_type
    txn.match_confidence = confidence
    txn.lifecycle_status = "Resolved"
    txn.resolved_at = datetime.utcnow()
    
    db.commit()
    return records


def record_invoice_to_many_txns(
    db: Session,
    inv: models.Invoice,
    transactions_with_allocations: List[Dict],
    match_type: str,
    confidence: float,
    user: str = "system"
):
    """
    Many-to-Many Matching: One invoice matched to multiple bank transactions (partial payments).
    """
    existing_allocs = db.query(models.ReconciliationTable).filter(
        models.ReconciliationTable.invoice_id == inv.id
    ).all()
    existing_total = sum(a.amount_allocated for a in existing_allocs)
    
    new_total = sum(item["amount"] for item in transactions_with_allocations)
    if existing_total + new_total > inv.amount + 0.01:
        raise ValueError(
            f"Over-allocation: Invoice {inv.document_number} amount is {inv.amount}, "
            f"existing allocations {existing_total}, new allocations {new_total} would exceed total."
        )
    
    records = []
    for item in transactions_with_allocations:
        txn = item["transaction"]
        alloc = item["amount"]
        
        recon = models.ReconciliationTable(
            bank_transaction_id=txn.id,
            invoice_id=inv.id,
            amount_allocated=alloc,
            match_type=match_type,
            confidence=confidence,
            created_by=user
        )
        db.add(recon)
        records.append(recon)
        
        # Check if transaction is fully allocated
        txn_allocs = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.bank_transaction_id == txn.id
        ).all()
        txn_total_allocated = sum(a.amount_allocated for a in txn_allocs) + alloc
        
        if txn_total_allocated >= abs(txn.amount) - 0.01:
            txn.is_reconciled = 1
            txn.reconciliation_type = match_type
            txn.match_confidence = confidence
            txn.lifecycle_status = "Resolved"
            txn.resolved_at = datetime.utcnow()
    
    inv.truth_label = "reconciled"
    
    final_total = existing_total + new_total
    if final_total >= inv.amount - 0.01:
        snapshot = db.query(models.Snapshot).filter(models.Snapshot.id == inv.snapshot_id).first()
        if snapshot and not snapshot.is_locked:
            inv.payment_date = datetime.utcnow()
    
    db.commit()
    return records


def get_allocation_summary(db: Session, invoice_id: int = None, transaction_id: int = None):
    """Get allocation summary for an invoice or transaction."""
    if invoice_id:
        inv = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
        if not inv:
            return None
        
        allocs = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.invoice_id == invoice_id
        ).all()
        
        total_allocated = sum(a.amount_allocated for a in allocs)
        return {
            "invoice_id": invoice_id,
            "invoice_amount": inv.amount,
            "total_allocated": total_allocated,
            "remaining": inv.amount - total_allocated,
            "is_fully_paid": total_allocated >= inv.amount - 0.01,
            "allocations": [
                {
                    "transaction_id": a.bank_transaction_id,
                    "amount": a.amount_allocated,
                    "match_type": a.match_type,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in allocs
            ]
        }
    
    if transaction_id:
        txn = db.query(models.BankTransaction).filter(models.BankTransaction.id == transaction_id).first()
        if not txn:
            return None
        
        allocs = db.query(models.ReconciliationTable).filter(
            models.ReconciliationTable.bank_transaction_id == transaction_id
        ).all()
        
        total_allocated = sum(a.amount_allocated for a in allocs)
        return {
            "transaction_id": transaction_id,
            "transaction_amount": abs(txn.amount),
            "total_allocated": total_allocated,
            "remaining": abs(txn.amount) - total_allocated,
            "is_fully_allocated": total_allocated >= abs(txn.amount) - 0.01,
            "allocations": [
                {
                    "invoice_id": a.invoice_id,
                    "amount": a.amount_allocated,
                    "match_type": a.match_type,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in allocs
            ]
        }
    
    return None


def find_bundled_invoice_matches(db: Session, txn: models.BankTransaction, invoices: List[models.Invoice], tolerance: float = 0.01):
    """
    Find invoices that sum to the transaction amount (bundled payment detection).
    One bank transaction = sum of multiple invoices.
    """
    txn_amount = abs(txn.amount)
    
    candidates = [inv for inv in invoices if inv.amount and inv.payment_date is None and inv.amount <= txn_amount]
    candidates.sort(key=lambda x: x.amount, reverse=True)
    
    result_combinations = []
    
    # Try single invoice first
    for inv in candidates:
        if abs(inv.amount - txn_amount) <= tolerance:
            result_combinations.append([{"invoice": inv, "amount": inv.amount}])
    
    # Try pairs
    for i, inv1 in enumerate(candidates):
        for inv2 in candidates[i+1:]:
            if abs(inv1.amount + inv2.amount - txn_amount) <= tolerance:
                result_combinations.append([
                    {"invoice": inv1, "amount": inv1.amount},
                    {"invoice": inv2, "amount": inv2.amount}
                ])
    
    # Try triples
    for i, inv1 in enumerate(candidates):
        for j, inv2 in enumerate(candidates[i+1:], i+1):
            for inv3 in candidates[j+1:]:
                if abs(inv1.amount + inv2.amount + inv3.amount - txn_amount) <= tolerance:
                    result_combinations.append([
                        {"invoice": inv1, "amount": inv1.amount},
                        {"invoice": inv2, "amount": inv2.amount},
                        {"invoice": inv3, "amount": inv3.amount}
                    ])
    
    return result_combinations


# ========== OTHER FUNCTIONS ==========

def detect_intercompany_washes(db: Session, entity_id: int):
    """
    Identifies transactions between internal accounts.
    Uses configured internal_account_ids first, then falls back to entity name matching.
    Suggested only - requires approval.
    """
    entities = db.query(models.Entity).all()
    internal_names = {e.name.lower(): e.id for e in entities}
    
    # Also check internal_account_ids for each entity
    internal_account_ids = set()
    for e in entities:
        if e.internal_account_ids:
            internal_account_ids.update(e.internal_account_ids)
    
    txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_account.has(entity_id=entity_id),
        models.BankTransaction.is_wash == 0
    ).all()
    
    washes_found = 0
    for txn in txns:
        cp = str(txn.counterparty or "").lower()
        ref = str(txn.reference or "")
        
        # Check by configured internal accounts first
        if any(acc_id in ref for acc_id in internal_account_ids):
            txn.is_wash = 1
            txn.reconciliation_type = "Suggested Wash"
            washes_found += 1
            continue
        
        # Fallback to entity name matching
        if cp in internal_names and internal_names[cp] != entity_id:
            txn.is_wash = 1
            txn.reconciliation_type = "Suggested Wash"
            washes_found += 1
            
    db.commit()
    return washes_found

def calculate_cash_explained_pct(db: Session, entity_id: int):
    """
    CFO Trust Metric: Single north-star trust KPI
    Shows % of bank cash movements that are explained (matched + categorized).
    """
    accounts = db.query(models.BankAccount).filter(models.BankAccount.entity_id == entity_id).all()
    if not accounts:
        return {
            "explained_pct": 0.0,
            "trend_vs_prior_week": 0.0,
            "breakdown": {"deterministic": 0, "rules": 0, "manual": 0, "suggested": 0, "unmatched": 0},
            "total_movements": 0,
            "total_amount": 0.0,
            "unmatched_amount": 0.0
        }
    
    account_ids = [a.id for a in accounts]
    
    all_txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_account_id.in_(account_ids)
    ).all()
    
    total_count = len(all_txns)
    total_amount = sum(abs(t.amount) for t in all_txns)
    
    if total_count == 0:
        return {
            "explained_pct": 100.0,
            "trend_vs_prior_week": 0.0,
            "breakdown": {"deterministic": 0, "rules": 0, "manual": 0, "suggested": 0, "unmatched": 0},
            "total_movements": 0,
            "total_amount": 0.0,
            "unmatched_amount": 0.0
        }
    
    breakdown = {"deterministic": 0, "rules": 0, "manual": 0, "suggested": 0, "unmatched": 0}
    explained_count = 0
    explained_amount = 0.0
    unmatched_amount = 0.0
    
    for txn in all_txns:
        if txn.is_reconciled:
            explained_count += 1
            explained_amount += abs(txn.amount)
            
            rec_type = (txn.reconciliation_type or "").lower()
            if "deterministic" in rec_type:
                breakdown["deterministic"] += 1
            elif "rule" in rec_type:
                breakdown["rules"] += 1
            elif "manual" in rec_type:
                breakdown["manual"] += 1
            elif "suggested" in rec_type or "wash" in rec_type:
                breakdown["suggested"] += 1
        else:
            breakdown["unmatched"] += 1
            unmatched_amount += abs(txn.amount)
    
    explained_pct = (explained_count / total_count * 100) if total_count > 0 else 0.0
    
    one_week_ago = datetime.now() - timedelta(days=7)
    prior_txns = [t for t in all_txns if t.transaction_date and t.transaction_date < one_week_ago]
    prior_explained = sum(1 for t in prior_txns if t.is_reconciled)
    prior_pct = (prior_explained / len(prior_txns) * 100) if prior_txns else 0.0
    
    trend = explained_pct - prior_pct
    
    return {
        "explained_pct": round(explained_pct, 1),
        "trend_vs_prior_week": round(trend, 1),
        "breakdown": breakdown,
        "total_movements": total_count,
        "total_amount": round(total_amount, 2),
        "unmatched_amount": round(unmatched_amount, 2)
    }

def get_reconciliation_suggestions(db: Session, entity_id: int):
    """Get suggested matches that need user approval."""
    txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_account.has(entity_id=entity_id),
        models.BankTransaction.is_reconciled == 0,
        models.BankTransaction.reconciliation_type.like("Suggested%")
    ).all()
    
    open_invoices = db.query(models.Invoice).filter(
        models.Invoice.entity_id == entity_id,
        models.Invoice.payment_date == None
    ).all()
    
    invoice_indexes = build_invoice_indexes(open_invoices)
    
    suggestions = []
    for txn in txns:
        if "Bundled" in (txn.reconciliation_type or ""):
            # Find bundled matches
            bundled = find_bundled_invoice_matches(db, txn, open_invoices)
            if bundled:
                suggestions.append({
                    "transaction": {
                        "id": txn.id,
                        "amount": txn.amount,
                        "counterparty": txn.counterparty,
                        "date": txn.transaction_date.isoformat() if txn.transaction_date else None
                    },
                    "match_type": "bundled",
                    "invoices": [
                        {
                            "id": item["invoice"].id,
                            "document_number": item["invoice"].document_number,
                            "amount": item["amount"]
                        }
                        for item in bundled[0]
                    ],
                    "confidence": txn.match_confidence
                })
        else:
            matches = find_suggested_matches_optimized(txn, invoice_indexes)
            if matches:
                suggestions.append({
                    "transaction": {
                        "id": txn.id,
                        "amount": txn.amount,
                        "counterparty": txn.counterparty,
                        "date": txn.transaction_date.isoformat() if txn.transaction_date else None
                    },
                    "match_type": "single",
                    "suggestion": {
                        "id": matches[0]['invoice'].id,
                        "document_number": matches[0]['invoice'].document_number,
                        "customer": matches[0]['invoice'].customer,
                        "amount": matches[0]['invoice'].amount,
                        "confidence": matches[0]['confidence']
                    }
                })
    
    return suggestions

def reconcile_transactions(db: Session, entity_id: int):
    """Run the full reconciliation engine for an entity."""
    results = generate_match_ladder(db, entity_id)
    washes = detect_intercompany_washes(db, entity_id)
    return {"matches": len(results), "washes_flagged": washes}

def get_cash_ledger_summary(db: Session, entity_id: int):
    """Get summary of cash ledger for display."""
    accounts = db.query(models.BankAccount).filter(models.BankAccount.entity_id == entity_id).all()
    
    total_cash = sum(a.balance for a in accounts)
    
    account_ids = [a.id for a in accounts]
    recent_txns = db.query(models.BankTransaction).filter(
        models.BankTransaction.bank_account_id.in_(account_ids)
    ).order_by(models.BankTransaction.transaction_date.desc()).limit(50).all()
    
    return {
        "total_cash": total_cash,
        "accounts": [{
            "id": a.id,
            "name": a.account_name,
            "bank": a.bank_name,
            "balance": a.balance,
            "balance_as_of": a.balance_as_of.isoformat() if a.balance_as_of else None,
            "statement_start": a.statement_start.isoformat() if a.statement_start else None,
            "statement_end": a.statement_end.isoformat() if a.statement_end else None,
            "last_sync": a.last_sync_at.isoformat() if a.last_sync_at else None
        } for a in accounts],
        "recent_transactions": [{
            "id": t.id,
            "transaction_date": t.transaction_date.isoformat() if t.transaction_date else None,
            "amount": t.amount,
            "counterparty": t.counterparty,
            "transaction_type": t.transaction_type,
            "is_reconciled": t.is_reconciled == 1,
            "reconciliation_type": t.reconciliation_type,
            "lifecycle_status": t.lifecycle_status,
            "days_unmatched": t.days_unmatched
        } for t in recent_txns]
    }

def approve_wash_service(db: Session, tx1_id: int, tx2_id: int, user: str = "system"):
    """Approve an intercompany wash between two transactions."""
    tx1 = db.query(models.BankTransaction).filter(models.BankTransaction.id == tx1_id).first()
    tx2 = db.query(models.BankTransaction).filter(models.BankTransaction.id == tx2_id).first()
    
    if tx1:
        tx1.is_reconciled = 1
        tx1.reconciliation_type = "Approved Wash"
        tx1.lifecycle_status = "Resolved"
        tx1.resolved_at = datetime.utcnow()
    if tx2:
        tx2.is_reconciled = 1
        tx2.reconciliation_type = "Approved Wash"
        tx2.lifecycle_status = "Resolved"
        tx2.resolved_at = datetime.utcnow()
    
    # Create IntercompanyWash record if model exists
    if hasattr(models, 'IntercompanyWash') and tx1 and tx2:
        wash = models.IntercompanyWash(
            entity_a_id=tx1.bank_account.entity_id if tx1.bank_account else None,
            entity_b_id=tx2.bank_account.entity_id if tx2.bank_account else None,
            transaction_a_id=tx1_id,
            transaction_b_id=tx2_id,
            amount=abs(tx1.amount),
            currency=tx1.currency,
            detection_method="heuristic",
            status="Approved",
            approved_by=user,
            approved_at=datetime.utcnow()
        )
        db.add(wash)
    
    db.commit()
    return {"status": "success"}
