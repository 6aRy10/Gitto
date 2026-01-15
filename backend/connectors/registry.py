"""
Connector Registry - Manages available connector types.
"""

from typing import Dict, Type, Optional
from .base import BaseConnector, ConnectorType


class ConnectorRegistry:
    """
    Registry of available connector implementations.
    
    Use register() to add new connector types.
    Use get() to instantiate a connector by type.
    """
    
    _connectors: Dict[str, Type[BaseConnector]] = {}
    
    @classmethod
    def register(cls, connector_type: str, connector_class: Type[BaseConnector]) -> None:
        """Register a connector implementation."""
        cls._connectors[connector_type] = connector_class
    
    @classmethod
    def get(cls, connector_type: str, config: dict) -> Optional[BaseConnector]:
        """
        Get a connector instance by type.
        
        Args:
            connector_type: One of ConnectorType values
            config: Configuration for the connector
            
        Returns:
            Instantiated connector or None if type not found
        """
        connector_class = cls._connectors.get(connector_type)
        if connector_class:
            return connector_class(config)
        return None
    
    @classmethod
    def list_available(cls) -> Dict[str, str]:
        """
        List all registered connector types.
        
        Returns:
            Dict mapping type name to description
        """
        return {
            name: getattr(conn, 'description', 'No description')
            for name, conn in cls._connectors.items()
        }
    
    @classmethod
    def is_registered(cls, connector_type: str) -> bool:
        """Check if a connector type is registered."""
        return connector_type in cls._connectors


# Auto-register connectors on import
def _auto_register():
    """Register all built-in connectors."""
    try:
        from .bank_mt940 import MT940Connector
        ConnectorRegistry.register(ConnectorType.BANK_MT940.value, MT940Connector)
    except ImportError:
        pass
    
    try:
        from .bank_csv import BankCSVConnector
        ConnectorRegistry.register(ConnectorType.BANK_CSV.value, BankCSVConnector)
    except ImportError:
        pass
    
    try:
        from .erp_quickbooks import QuickBooksConnector
        ConnectorRegistry.register(ConnectorType.ERP_QUICKBOOKS.value, QuickBooksConnector)
    except ImportError:
        pass
    
    try:
        from .erp_xero import XeroConnector
        ConnectorRegistry.register(ConnectorType.ERP_XERO.value, XeroConnector)
    except ImportError:
        pass
    
    # Bank API Connectors
    try:
        from .bank_plaid import PlaidConnector
        ConnectorRegistry.register(ConnectorType.BANK_PLAID.value, PlaidConnector)
    except ImportError:
        pass
    
    try:
        from .bank_nordigen import NordigenConnector
        ConnectorRegistry.register(ConnectorType.BANK_NORDIGEN.value, NordigenConnector)
    except ImportError:
        pass
    
    # Payment Processor Connectors
    try:
        from .payments_stripe import StripeConnector
        ConnectorRegistry.register(ConnectorType.PAYMENTS_STRIPE.value, StripeConnector)
    except ImportError:
        pass
    
    # Enterprise ERP Connectors
    try:
        from .erp_netsuite import NetSuiteConnector
        ConnectorRegistry.register(ConnectorType.ERP_NETSUITE.value, NetSuiteConnector)
    except ImportError:
        pass
    
    try:
        from .erp_sap import SAPConnector
        ConnectorRegistry.register(ConnectorType.ERP_SAP.value, SAPConnector)
    except ImportError:
        pass
    
    # Data Warehouse Connectors
    try:
        from .warehouse_snowflake import SnowflakeConnector
        ConnectorRegistry.register(ConnectorType.WAREHOUSE_SNOWFLAKE.value, SnowflakeConnector)
    except ImportError:
        pass
    
    try:
        from .warehouse_bigquery import BigQueryConnector
        ConnectorRegistry.register(ConnectorType.WAREHOUSE_BIGQUERY.value, BigQueryConnector)
    except ImportError:
        pass


_auto_register()

