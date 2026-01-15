"""
Matching Policy Service
Configurable matching policies per entity, per currency (tolerance, date window).
"""

from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import models


class MatchingPolicy:
    """Matching policy configuration"""
    def __init__(
        self,
        entity_id: int,
        currency: Optional[str] = None,
        amount_tolerance: float = 0.01,
        date_window_days: int = 30,
        deterministic_enabled: bool = True,
        rules_enabled: bool = True,
        suggested_enabled: bool = True
    ):
        self.entity_id = entity_id
        self.currency = currency
        self.amount_tolerance = amount_tolerance
        self.date_window_days = date_window_days
        self.deterministic_enabled = deterministic_enabled
        self.rules_enabled = rules_enabled
        self.suggested_enabled = suggested_enabled


def get_matching_policy(
    db: Session,
    entity_id: int,
    currency: Optional[str] = None
) -> MatchingPolicy:
    """
    Get matching policy for entity/currency.
    Falls back to entity default, then system default.
    """
    # Check for currency-specific policy
    if currency and hasattr(models, 'MatchingPolicy'):
        policy = db.query(models.MatchingPolicy).filter(
            models.MatchingPolicy.entity_id == entity_id,
            models.MatchingPolicy.currency == currency
        ).first()
        
        if policy:
            return MatchingPolicy(
                entity_id=entity_id,
                currency=currency,
                amount_tolerance=policy.amount_tolerance,
                date_window_days=policy.date_window_days,
                deterministic_enabled=policy.deterministic_enabled == 1,
                rules_enabled=policy.rules_enabled == 1,
                suggested_enabled=policy.suggested_enabled == 1
            )
    
    # Check for entity default policy (if MatchingPolicy model exists)
    if hasattr(models, 'MatchingPolicy'):
        policy = db.query(models.MatchingPolicy).filter(
            models.MatchingPolicy.entity_id == entity_id,
            models.MatchingPolicy.currency == None
        ).first()
        
        if policy:
            return MatchingPolicy(
                entity_id=entity_id,
                currency=None,
                amount_tolerance=policy.amount_tolerance,
                date_window_days=policy.date_window_days,
                deterministic_enabled=policy.deterministic_enabled == 1,
                rules_enabled=policy.rules_enabled == 1,
                suggested_enabled=policy.suggested_enabled == 1
            )
    
    # System default
    entity = db.query(models.Entity).filter(models.Entity.id == entity_id).first()
    return MatchingPolicy(
        entity_id=entity_id,
        currency=currency,
        amount_tolerance=0.01,  # Default tolerance
        date_window_days=30,    # Default window
        deterministic_enabled=True,
        rules_enabled=True,
        suggested_enabled=True
    )


def set_matching_policy(
    db: Session,
    entity_id: int,
    currency: Optional[str],
    amount_tolerance: float,
    date_window_days: int,
    deterministic_enabled: bool = True,
    rules_enabled: bool = True,
    suggested_enabled: bool = True
):
    """Set matching policy for entity/currency"""
    policy = db.query(models.MatchingPolicy).filter(
        models.MatchingPolicy.entity_id == entity_id,
        models.MatchingPolicy.currency == currency
    ).first()
    
    if policy:
        # Update existing
        policy.amount_tolerance = amount_tolerance
        policy.date_window_days = date_window_days
        policy.deterministic_enabled = 1 if deterministic_enabled else 0
        policy.rules_enabled = 1 if rules_enabled else 0
        policy.suggested_enabled = 1 if suggested_enabled else 0
    else:
        # Create new
        policy = models.MatchingPolicy(
            entity_id=entity_id,
            currency=currency,
            amount_tolerance=amount_tolerance,
            date_window_days=date_window_days,
            deterministic_enabled=1 if deterministic_enabled else 0,
            rules_enabled=1 if rules_enabled else 0,
            suggested_enabled=1 if suggested_enabled else 0
        )
        db.add(policy)
    
    db.commit()
    return policy


