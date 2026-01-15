"""
P1 Fix: Secrets Manager for secure credential handling.

Instead of storing passwords in plain text, we:
1. Store environment variable names in the database
2. Resolve passwords from environment variables at runtime
3. Never return passwords in API responses
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Prefix for environment variable names
ENV_VAR_PREFIX = "GITTO_SNOWFLAKE_"


def get_password_from_env(env_var_name: Optional[str]) -> Optional[str]:
    """
    P1 Fix: Resolve password from environment variable.
    
    Args:
        env_var_name: Name of environment variable (e.g., "GITTO_SNOWFLAKE_PASSWORD_1")
    
    Returns:
        Password value from environment, or None if not set
    """
    if not env_var_name:
        return None
    
    password = os.getenv(env_var_name)
    if not password:
        logger.warning(f"Environment variable {env_var_name} not set")
    return password


def set_password_env_var_name(config_id: int) -> str:
    """
    Generate a standard environment variable name for a config.
    
    Args:
        config_id: SnowflakeConfig ID
    
    Returns:
        Environment variable name (e.g., "GITTO_SNOWFLAKE_PASSWORD_1")
    """
    return f"{ENV_VAR_PREFIX}PASSWORD_{config_id}"


def resolve_snowflake_password(config_id: int, password_env_var: Optional[str] = None) -> Optional[str]:
    """
    P1 Fix: Resolve Snowflake password from environment variable.
    
    Priority:
    1. Use provided password_env_var if set
    2. Use standard env var name based on config_id
    3. Fallback to legacy password field (for migration)
    
    Args:
        config_id: SnowflakeConfig ID
        password_env_var: Optional custom env var name
    
    Returns:
        Password from environment variable
    """
    # Try custom env var name first
    if password_env_var:
        password = get_password_from_env(password_env_var)
        if password:
            return password
    
    # Try standard env var name
    standard_env_var = set_password_env_var_name(config_id)
    password = get_password_from_env(standard_env_var)
    if password:
        return password
    
    # Legacy fallback (for migration period)
    legacy_env_var = os.getenv(f"{ENV_VAR_PREFIX}LEGACY_PASSWORD")
    if legacy_env_var:
        logger.warning("Using legacy password environment variable. Please migrate to config-specific variables.")
        return legacy_env_var
    
    return None


def sanitize_config_for_api(config_dict: dict) -> dict:
    """
    P1 Fix: Remove sensitive fields from config before returning via API.
    
    Args:
        config_dict: Configuration dictionary
    
    Returns:
        Sanitized dictionary without password fields
    """
    sanitized = config_dict.copy()
    
    # Remove password fields
    if 'password' in sanitized:
        del sanitized['password']
    
    # Replace with env var indicator
    if 'password_env_var' in sanitized and sanitized['password_env_var']:
        sanitized['password_source'] = 'environment_variable'
        sanitized['password_env_var'] = sanitized['password_env_var']
    else:
        sanitized['password_source'] = 'not_configured'
    
    return sanitized







