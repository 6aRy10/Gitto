"""
Role-Based Access Control (RBAC) Service
Finance-native collaboration permissions for treasury teams.

Roles and what they do:
- Treasury Manager: runs reconciliation + weekly meeting pack
- FP&A: scenarios, commentary, variance interpretation
- AP Manager: confirms payment runs, holds, vendor priorities
- AR/Collections: confirms collections actions, disputed items, promises to pay
- Controller: governs mappings, policies, close alignment
- CFO: approves scenarios/actions; signs off weekly snapshot
- CEO: sees runway, red weeks, top risks, approved plan (read-only)
"""

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import wraps
from fastapi import HTTPException, Header
import models

# ═══════════════════════════════════════════════════════════════════════════════
# FINANCE-NATIVE ROLE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

ROLES = {
    "admin": {
        "level": 100,
        "display_name": "Administrator",
        "description": "Full system access",
        "permissions": ["*"]  # All permissions
    },
    
    "cfo": {
        "level": 95,
        "display_name": "CFO",
        "description": "Approves scenarios/actions; signs off weekly snapshot",
        "permissions": [
            # Snapshot - full control including lock
            "snapshot:create", "snapshot:view", "snapshot:ready", "snapshot:lock", "snapshot:delete",
            # Reconciliation - full control
            "reconciliation:view", "reconciliation:approve", "reconciliation:override", "reconciliation:allocate",
            # Exceptions - full control
            "exception:view", "exception:assign", "exception:resolve", "exception:escalate",
            # Scenarios - approve/reject
            "scenario:view", "scenario:create", "scenario:approve", "scenario:reject",
            # Actions - approve/reject
            "action:view", "action:create", "action:approve", "action:reject", "action:execute",
            # Levers - full control
            "lever:view", "lever:execute", "lever:approve",
            # Comments
            "comment:view", "comment:create",
            # Weekly pack
            "pack:view", "pack:generate",
            # Policy & system
            "policy:view", "policy:edit", "fx:view", "fx:edit",
            "audit:view", "report:all", "meeting:present"
        ]
    },
    
    "ceo": {
        "level": 90,
        "display_name": "CEO",
        "description": "Read-only: sees runway, red weeks, top risks, approved plan",
        "permissions": [
            # Read-only access to everything
            "snapshot:view",
            "reconciliation:view",
            "exception:view",
            "scenario:view",
            "action:view",
            "lever:view",
            "comment:view",
            "pack:view",
            "policy:view", "fx:view",
            "audit:view", "report:all", "meeting:view"
        ]
    },
    
    "treasury_manager": {
        "level": 85,
        "display_name": "Treasury Manager",
        "description": "Runs reconciliation + weekly meeting pack (owner/operator)",
        "permissions": [
            # Snapshot - create and prepare
            "snapshot:create", "snapshot:view", "snapshot:ready",
            # Reconciliation - full operational control
            "reconciliation:view", "reconciliation:approve", "reconciliation:allocate", "reconciliation:assign",
            # Exceptions - full operational control
            "exception:view", "exception:assign", "exception:resolve", "exception:escalate",
            # Scenarios - create and propose
            "scenario:view", "scenario:create", "scenario:submit",
            # Actions - create and propose
            "action:view", "action:create", "action:submit", "action:execute",
            # Levers - execute within limits
            "lever:view", "lever:execute",
            # Comments
            "comment:view", "comment:create",
            # Weekly pack
            "pack:view", "pack:generate",
            # Policy - view only
            "policy:view", "fx:view",
            "audit:view", "report:standard", "meeting:present"
        ]
    },
    
    "controller": {
        "level": 80,
        "display_name": "Controller / Accounting",
        "description": "Governs mappings, policies, close alignment",
        "permissions": [
            # Snapshot - view and approve readiness
            "snapshot:view", "snapshot:ready",
            # Reconciliation - approve accounting-sensitive changes
            "reconciliation:view", "reconciliation:approve",
            # Exceptions - resolve accounting issues
            "exception:view", "exception:resolve",
            # Scenarios - view
            "scenario:view",
            # Actions - view
            "action:view",
            # Comments
            "comment:view", "comment:create",
            # Weekly pack
            "pack:view",
            # Policy - full control
            "policy:view", "policy:edit", "fx:view", "fx:edit",
            "mapping:view", "mapping:edit",
            "audit:view", "report:standard"
        ]
    },
    
    "fp_and_a": {
        "level": 70,
        "display_name": "FP&A Analyst",
        "description": "Scenarios, commentary, variance interpretation",
        "permissions": [
            # Snapshot - view
            "snapshot:view",
            # Reconciliation - view and suggest
            "reconciliation:view", "reconciliation:suggest",
            # Exceptions - view
            "exception:view",
            # Scenarios - create and propose
            "scenario:view", "scenario:create", "scenario:submit",
            # Actions - create and propose
            "action:view", "action:create", "action:submit",
            # Levers - view and model
            "lever:view", "lever:model",
            # Comments - full access for analysis notes
            "comment:view", "comment:create",
            # Weekly pack
            "pack:view",
            # Policy - view only
            "policy:view", "fx:view",
            "audit:view", "report:standard"
        ]
    },
    
    "ap_manager": {
        "level": 60,
        "display_name": "AP Manager",
        "description": "Confirms payment runs, holds, vendor priorities",
        "permissions": [
            # Snapshot - view
            "snapshot:view",
            # Reconciliation - view only
            "reconciliation:view",
            # Exceptions - view and resolve AP-related
            "exception:view", "exception:resolve:ap",
            # Scenarios - view
            "scenario:view",
            # Actions - create AP-related, confirm payment runs
            "action:view", "action:create:ap", "action:confirm:payment",
            # Levers - view
            "lever:view",
            # Comments
            "comment:view", "comment:create",
            # AP-specific
            "vendor_bill:view", "vendor_bill:edit", "vendor_bill:hold",
            "payment_run:view", "payment_run:confirm",
            "report:ap"
        ]
    },
    
    "ar_collections": {
        "level": 60,
        "display_name": "AR / Collections",
        "description": "Confirms collections actions, disputed items, promises to pay",
        "permissions": [
            # Snapshot - view
            "snapshot:view",
            # Reconciliation - view only
            "reconciliation:view",
            # Exceptions - view and resolve AR-related
            "exception:view", "exception:resolve:ar",
            # Scenarios - view
            "scenario:view",
            # Actions - create AR-related, propose collections
            "action:view", "action:create:ar", "action:confirm:collection",
            # Levers - view
            "lever:view",
            # Comments
            "comment:view", "comment:create",
            # AR-specific
            "invoice:view", "invoice:edit:dispute", "invoice:mark_promise",
            "collection:view", "collection:create",
            "report:ar"
        ]
    },
    
    "viewer": {
        "level": 10,
        "display_name": "Viewer",
        "description": "Read-only access to dashboards",
        "permissions": [
            "snapshot:view",
            "reconciliation:view",
            "exception:view",
            "scenario:view",
            "action:view",
            "lever:view",
            "comment:view",
            "pack:view",
            "report:basic"
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION CATEGORIES FOR UI
# ═══════════════════════════════════════════════════════════════════════════════

PERMISSION_CATEGORIES = {
    "snapshot": {
        "display_name": "Snapshots",
        "permissions": ["create", "view", "ready", "lock", "delete"]
    },
    "reconciliation": {
        "display_name": "Reconciliation",
        "permissions": ["view", "approve", "override", "allocate", "assign", "suggest"]
    },
    "exception": {
        "display_name": "Exceptions",
        "permissions": ["view", "assign", "resolve", "escalate", "resolve:ap", "resolve:ar"]
    },
    "scenario": {
        "display_name": "Scenarios",
        "permissions": ["view", "create", "submit", "approve", "reject"]
    },
    "action": {
        "display_name": "Actions",
        "permissions": ["view", "create", "submit", "approve", "reject", "execute", "create:ap", "create:ar", "confirm:payment", "confirm:collection"]
    },
    "lever": {
        "display_name": "Liquidity Levers",
        "permissions": ["view", "execute", "approve", "model"]
    },
    "comment": {
        "display_name": "Comments",
        "permissions": ["view", "create"]
    },
    "pack": {
        "display_name": "Weekly Pack",
        "permissions": ["view", "generate"]
    },
    "policy": {
        "display_name": "Policies",
        "permissions": ["view", "edit"]
    },
    "audit": {
        "display_name": "Audit Log",
        "permissions": ["view"]
    },
    "report": {
        "display_name": "Reports",
        "permissions": ["basic", "standard", "all", "ap", "ar"]
    },
    "meeting": {
        "display_name": "Meeting Mode",
        "permissions": ["view", "present"]
    }
}

# Hard rule: Only CFO (or Treasury + CFO) can LOCK snapshot
LOCK_CAPABLE_ROLES = ["admin", "cfo"]


class User(models.Base):
    """User model for RBAC"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    role = Column(String, default="viewer")
    entity_ids = Column(JSON, default=list)  # List of entity IDs user can access
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


def get_user_role(user_email: str, db: Session) -> str:
    """Get user's role from database"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return "viewer"  # Default role
    return user.role


def has_permission(role: str, permission: str) -> bool:
    """Check if role has specific permission"""
    if role not in ROLES:
        return False
    
    role_perms = ROLES[role]["permissions"]
    
    # Admin has all permissions
    if "*" in role_perms:
        return True
    
    # Check exact permission
    if permission in role_perms:
        return True
    
    # Check wildcard permission (e.g., "snapshot:*" matches "snapshot:view")
    perm_parts = permission.split(":")
    if len(perm_parts) == 2:
        wildcard_perm = f"{perm_parts[0]}:*"
        if wildcard_perm in role_perms:
            return True
    
    return False


def can_access_entity(user_email: str, entity_id: int, db: Session) -> bool:
    """Check if user can access specific entity"""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return False
    
    role = user.role
    
    # Admin and CFO can access all entities
    if role in ["admin", "cfo"]:
        return True
    
    # Others need explicit entity access
    if not user.entity_ids:
        return True  # No restrictions = all access
    
    return entity_id in user.entity_ids


def require_permission(permission: str):
    """Decorator to require specific permission for endpoint"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, x_user_email: Optional[str] = Header(None, alias="X-User-Email"), db: Session = None, **kwargs):
            if db is None:
                # Try to get db from kwargs
                db = kwargs.get("db")
            
            if not x_user_email:
                # Allow anonymous for development, default to viewer
                x_user_email = "anonymous@dev.local"
            
            role = get_user_role(x_user_email, db)
            
            if not has_permission(role, permission):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Permission denied",
                        "required_permission": permission,
                        "user_role": role,
                        "user_email": x_user_email
                    }
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_permissions_for_role(role: str) -> List[str]:
    """Get all permissions for a role"""
    if role not in ROLES:
        return []
    return ROLES[role]["permissions"]


def create_user(
    db: Session,
    email: str,
    name: str,
    role: str = "viewer",
    entity_ids: Optional[List[int]] = None
) -> User:
    """Create a new user"""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError(f"User with email {email} already exists")
    
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role}. Valid roles: {list(ROLES.keys())}")
    
    user = User(
        email=email,
        name=name,
        role=role,
        entity_ids=entity_ids or []
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_role(db: Session, email: str, new_role: str, updater: str) -> User:
    """Update user's role with audit logging"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError(f"User {email} not found")
    
    if new_role not in ROLES:
        raise ValueError(f"Invalid role: {new_role}")
    
    old_role = user.role
    user.role = new_role
    db.commit()
    
    # Audit log
    from audit_service import log_policy_action
    log_policy_action(
        db, updater, "RoleChange", 0, "user_role",
        changes={"user_email": email, "old_role": old_role, "new_role": new_role}
    )
    
    return user


def get_role_hierarchy() -> Dict[str, Any]:
    """Get role hierarchy for UI display"""
    return {
        role: {
            "level": config["level"],
            "display_name": config["display_name"],
            "permissions_count": len(config["permissions"])
        }
        for role, config in sorted(ROLES.items(), key=lambda x: -x[1]["level"])
    }



