# Gitto Connector SDK
# Enterprise-grade data connectors for banks, ERPs, and warehouses

from .base import BaseConnector, ConnectorResult, SyncContext
from .registry import ConnectorRegistry

__all__ = [
    'BaseConnector',
    'ConnectorResult', 
    'SyncContext',
    'ConnectorRegistry',
]




