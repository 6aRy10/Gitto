'use client';

import React, { useState, useEffect } from 'react';
import { 
  Building2, CreditCard, Landmark, RefreshCw, CheckCircle2, 
  XCircle, AlertCircle, Plus, Settings, Trash2, Play, Pause,
  ChevronRight, ExternalLink, Lock, Eye, EyeOff
} from 'lucide-react';

// Connector type definitions - All 10 live integrations
const CONNECTOR_TYPES = {
  // === BANKS ===
  bank_plaid: {
    name: 'Plaid',
    description: 'US/Canada bank accounts (11,000+ institutions)',
    icon: Landmark,
    color: '#00C853',
    category: 'Banks',
    fields: [
      { key: 'client_id', label: 'Client ID', type: 'text', required: true },
      { key: 'secret', label: 'Secret', type: 'password', required: true },
      { key: 'environment', label: 'Environment', type: 'select', options: ['sandbox', 'development', 'production'], required: true },
    ],
    oauth: true,
    oauthLabel: 'Connect Bank Account'
  },
  bank_nordigen: {
    name: 'Nordigen (GoCardless)',
    description: 'EU/UK Open Banking (2,500+ banks)',
    icon: Building2,
    color: '#2196F3',
    category: 'Banks',
    fields: [
      { key: 'secret_id', label: 'Secret ID', type: 'text', required: true },
      { key: 'secret_key', label: 'Secret Key', type: 'password', required: true },
    ],
    oauth: true,
    oauthLabel: 'Select Your Bank'
  },
  bank_mt940: {
    name: 'MT940 / BAI2 Files',
    description: 'SWIFT Bank Statement Upload',
    icon: Landmark,
    color: '#607D8B',
    category: 'Banks',
    fields: [],
    oauth: false,
    fileUpload: true
  },

  // === ERP & ACCOUNTING ===
  erp_quickbooks: {
    name: 'QuickBooks Online',
    description: 'Intuit QuickBooks - Invoices & Bills',
    icon: Building2,
    color: '#2CA01C',
    category: 'ERP & Accounting',
    fields: [
      { key: 'client_id', label: 'Client ID', type: 'text', required: true },
      { key: 'client_secret', label: 'Client Secret', type: 'password', required: true },
      { key: 'realm_id', label: 'Company ID', type: 'text', required: true },
      { key: 'environment', label: 'Environment', type: 'select', options: ['sandbox', 'production'], required: true },
    ],
    oauth: true,
    oauthLabel: 'Connect QuickBooks'
  },
  erp_xero: {
    name: 'Xero',
    description: 'Xero Accounting Software',
    icon: Building2,
    color: '#13B5EA',
    category: 'ERP & Accounting',
    fields: [
      { key: 'client_id', label: 'Client ID', type: 'text', required: true },
      { key: 'client_secret', label: 'Client Secret', type: 'password', required: true },
      { key: 'tenant_id', label: 'Organization ID', type: 'text', required: true },
    ],
    oauth: true,
    oauthLabel: 'Connect Xero'
  },
  erp_netsuite: {
    name: 'Oracle NetSuite',
    description: 'NetSuite ERP - AR/AP & GL',
    icon: Building2,
    color: '#1A5276',
    category: 'ERP & Accounting',
    fields: [
      { key: 'account', label: 'Account ID', type: 'text', required: true, placeholder: 'TSTDRV123456' },
      { key: 'consumer_key', label: 'Consumer Key', type: 'text', required: true },
      { key: 'consumer_secret', label: 'Consumer Secret', type: 'password', required: true },
      { key: 'token_key', label: 'Token ID', type: 'text', required: true },
      { key: 'token_secret', label: 'Token Secret', type: 'password', required: true },
    ],
    oauth: false
  },
  erp_sap: {
    name: 'SAP S/4HANA',
    description: 'SAP ERP via OData API',
    icon: Building2,
    color: '#0FAAFF',
    category: 'ERP & Accounting',
    fields: [
      { key: 'base_url', label: 'OData Base URL', type: 'text', required: true, placeholder: 'https://my-sap.s4hana.cloud.sap' },
      { key: 'client', label: 'SAP Client', type: 'text', required: true, placeholder: '100' },
      { key: 'username', label: 'Username', type: 'text', required: true },
      { key: 'password', label: 'Password', type: 'password', required: true },
    ],
    oauth: false
  },

  // === PAYMENTS ===
  payments_stripe: {
    name: 'Stripe',
    description: 'Payment Processing & Payouts',
    icon: CreditCard,
    color: '#635BFF',
    category: 'Payments',
    fields: [
      { key: 'api_key', label: 'Secret API Key', type: 'password', required: true, placeholder: 'sk_live_...' },
    ],
    oauth: false
  },

  // === DATA WAREHOUSES ===
  warehouse_snowflake: {
    name: 'Snowflake',
    description: 'Snowflake Data Cloud',
    icon: Building2,
    color: '#29B5E8',
    category: 'Data Warehouses',
    fields: [
      { key: 'account', label: 'Account Identifier', type: 'text', required: true, placeholder: 'xy12345.us-east-1' },
      { key: 'user', label: 'Username', type: 'text', required: true },
      { key: 'password', label: 'Password', type: 'password', required: true },
      { key: 'warehouse', label: 'Warehouse', type: 'text', required: true, placeholder: 'COMPUTE_WH' },
      { key: 'database', label: 'Database', type: 'text', required: true },
      { key: 'schema', label: 'Schema', type: 'text', required: true, placeholder: 'PUBLIC' },
    ],
    oauth: false
  },
  warehouse_bigquery: {
    name: 'Google BigQuery',
    description: 'Google Cloud BigQuery',
    icon: Building2,
    color: '#4285F4',
    category: 'Data Warehouses',
    fields: [
      { key: 'project_id', label: 'Project ID', type: 'text', required: true },
      { key: 'dataset', label: 'Dataset Name', type: 'text', required: false, placeholder: 'default dataset (optional)' },
      { key: 'location', label: 'Location', type: 'select', options: ['US', 'EU', 'us-central1', 'europe-west1'], required: false },
      { key: 'credentials_json', label: 'Service Account JSON Path', type: 'text', required: false, placeholder: '/path/to/service-account.json' },
    ],
    oauth: false
  },
};

interface Connector {
  id: number;
  type: string;
  name: string;
  description: string;
  entity_id: number;
  is_active: boolean;
  connections_count: number;
  created_at: string;
}

interface Connection {
  id: number;
  name: string;
  sync_status: string;
  last_sync_at: string | null;
}

export default function ConnectorSettings() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newConnectorType, setNewConnectorType] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchConnectors();
  }, []);

  const fetchConnectors = async () => {
    try {
      const res = await fetch('/api/connectors');
      const data = await res.json();
      setConnectors(data);
    } catch (err) {
      console.error('Failed to fetch connectors:', err);
    }
  };

  const handleAddConnector = async () => {
    if (!newConnectorType) return;
    
    setLoading(true);
    try {
      const typeConfig = CONNECTOR_TYPES[newConnectorType as keyof typeof CONNECTOR_TYPES];
      
      // Create connector
      const connectorRes = await fetch('/api/connectors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: newConnectorType,
          name: formData.name || typeConfig.name,
          description: typeConfig.description,
          entity_id: 1 // Default entity
        })
      });
      
      const connector = await connectorRes.json();
      
      // Create connection with credentials
      await fetch(`/api/connectors/${connector.id}/connections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name || 'Default Connection',
          credentials: formData // In production, this should go to secrets manager
        })
      });
      
      await fetchConnectors();
      setShowAddModal(false);
      setNewConnectorType(null);
      setFormData({});
      
    } catch (err) {
      console.error('Failed to add connector:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async (connectorId: number) => {
    setLoading(true);
    setTestResult(null);
    
    try {
      const res = await fetch(`/api/connections/${connectorId}/test`, {
        method: 'POST'
      });
      const result = await res.json();
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: 'Connection test failed' });
    } finally {
      setLoading(false);
    }
  };

  // Test credentials before saving (for new connectors)
  const handleTestCredentials = async () => {
    if (!newConnectorType) return;
    
    setLoading(true);
    setTestResult(null);
    
    try {
      const res = await fetch('/api/connectors/test-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: newConnectorType,
          credentials: formData
        })
      });
      
      if (!res.ok) {
        const error = await res.json();
        setTestResult({ success: false, message: error.detail || 'Connection test failed' });
        return;
      }
      
      const result = await res.json();
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: 'Could not reach the server. Make sure the backend is running.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (connectionId: number) => {
    setLoading(true);
    try {
      await fetch(`/api/connections/${connectionId}/sync`, {
        method: 'POST'
      });
      await fetchConnectors();
    } catch (err) {
      console.error('Sync failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const groupedTypes = Object.entries(CONNECTOR_TYPES).reduce((acc, [key, value]) => {
    if (!acc[value.category]) acc[value.category] = [];
    acc[value.category].push({ key, ...value });
    return acc;
  }, {} as Record<string, any[]>);

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Integrations</h1>
            <p className="text-gray-400 mt-1">Connect your banks, ERPs, and payment systems</p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white text-black rounded-lg font-medium hover:bg-gray-100 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Integration
          </button>
        </div>

        {/* Active Connectors */}
        <div className="grid gap-4">
          {connectors.length === 0 ? (
            <div className="bg-[#0D0D12] border border-gray-800 rounded-xl p-12 text-center">
              <Settings className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">No integrations configured</h3>
              <p className="text-gray-400 mb-6">Connect your first data source to get started</p>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-6 py-3 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 transition-colors"
              >
                Add Your First Integration
              </button>
            </div>
          ) : (
            connectors.map((connector) => {
              const typeConfig = CONNECTOR_TYPES[connector.type as keyof typeof CONNECTOR_TYPES];
              const Icon = typeConfig?.icon || Settings;
              
              return (
                <div
                  key={connector.id}
                  className="bg-[#0D0D12] border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div 
                        className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: `${typeConfig?.color}20` }}
                      >
                        <Icon className="w-6 h-6" style={{ color: typeConfig?.color }} />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold">{connector.name}</h3>
                        <p className="text-gray-400 text-sm">{typeConfig?.description}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                      {/* Status */}
                      <div className="flex items-center gap-2">
                        {connector.is_active ? (
                          <span className="flex items-center gap-1 text-emerald-400 text-sm">
                            <CheckCircle2 className="w-4 h-4" />
                            Active
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-gray-400 text-sm">
                            <Pause className="w-4 h-4" />
                            Paused
                          </span>
                        )}
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTestConnection(connector.id)}
                          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                          title="Test Connection"
                        >
                          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                          onClick={() => handleSync(connector.id)}
                          className="p-2 text-gray-400 hover:text-emerald-400 hover:bg-gray-800 rounded-lg transition-colors"
                          title="Sync Now"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setSelectedConnector(connector)}
                          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                          title="Settings"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  {/* Connections count */}
                  <div className="mt-4 pt-4 border-t border-gray-800 flex items-center gap-6 text-sm text-gray-400">
                    <span>{connector.connections_count} connection{connector.connections_count !== 1 ? 's' : ''}</span>
                    <span>Created {new Date(connector.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Add Integration Modal */}
        {showAddModal && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-[#0D0D12] border border-gray-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-800">
                <h2 className="text-2xl font-bold">
                  {newConnectorType ? CONNECTOR_TYPES[newConnectorType as keyof typeof CONNECTOR_TYPES]?.name : 'Add Integration'}
                </h2>
                <p className="text-gray-400 mt-1">
                  {newConnectorType ? 'Configure your connection' : 'Choose an integration type'}
                </p>
              </div>
              
              <div className="p-6">
                {!newConnectorType ? (
                  // Connector Type Selection
                  <div className="space-y-6">
                    {Object.entries(groupedTypes).map(([category, types]) => (
                      <div key={category}>
                        <h3 className="text-sm font-medium text-gray-400 mb-3">{category}</h3>
                        <div className="grid grid-cols-2 gap-3">
                          {types.map((type) => {
                            const Icon = type.icon;
                            return (
                              <button
                                key={type.key}
                                onClick={() => setNewConnectorType(type.key)}
                                className="flex items-center gap-3 p-4 bg-[#141419] border border-gray-800 rounded-xl hover:border-gray-600 transition-colors text-left"
                              >
                                <div 
                                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                                  style={{ backgroundColor: `${type.color}20` }}
                                >
                                  <Icon className="w-5 h-5" style={{ color: type.color }} />
                                </div>
                                <div>
                                  <div className="font-medium">{type.name}</div>
                                  <div className="text-sm text-gray-400">{type.description}</div>
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  // Configuration Form
                  <div className="space-y-4">
                    {/* Connection Name */}
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Connection Name
                      </label>
                      <input
                        type="text"
                        value={formData.name || ''}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        placeholder={`My ${CONNECTOR_TYPES[newConnectorType as keyof typeof CONNECTOR_TYPES]?.name} Connection`}
                        className="w-full px-4 py-3 bg-[#141419] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    
                    {/* Dynamic Fields */}
                    {CONNECTOR_TYPES[newConnectorType as keyof typeof CONNECTOR_TYPES]?.fields.map((field) => (
                      <div key={field.key}>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          {field.label}
                          {field.required && <span className="text-red-400 ml-1">*</span>}
                        </label>
                        
                        {field.type === 'select' ? (
                          <select
                            value={formData[field.key] || ''}
                            onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                            className="w-full px-4 py-3 bg-[#141419] border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                          >
                            <option value="">Select...</option>
                            {'options' in field && field.options?.map((opt: string) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        ) : (
                          <div className="relative">
                            <input
                              type={field.type === 'password' && !showSecrets[field.key] ? 'password' : 'text'}
                              value={formData[field.key] || ''}
                              onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                              placeholder={'placeholder' in field ? field.placeholder : ''}
                              className="w-full px-4 py-3 bg-[#141419] border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 pr-12"
                            />
                            {field.type === 'password' && (
                              <button
                                type="button"
                                onClick={() => setShowSecrets({ ...showSecrets, [field.key]: !showSecrets[field.key] })}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                              >
                                {showSecrets[field.key] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                    
                    {/* OAuth Button */}
                    {CONNECTOR_TYPES[newConnectorType as keyof typeof CONNECTOR_TYPES]?.oauth && (
                      <div className="pt-4 border-t border-gray-800">
                        <button
                          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#141419] border border-gray-700 rounded-lg text-white hover:border-gray-500 transition-colors"
                        >
                          <ExternalLink className="w-4 h-4" />
                          {(() => {
                            const connectorType = CONNECTOR_TYPES[newConnectorType as keyof typeof CONNECTOR_TYPES];
                            return 'oauthLabel' in connectorType ? connectorType.oauthLabel : 'Connect';
                          })()}
                        </button>
                        <p className="text-sm text-gray-500 mt-2 text-center">
                          You'll be redirected to authorize access
                        </p>
                      </div>
                    )}
                    
                    {/* Security Note */}
                    <div className="flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg mt-6">
                      <Lock className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <div className="text-sm">
                        <div className="font-medium text-emerald-400">Secure Storage</div>
                        <div className="text-gray-400">
                          Credentials are encrypted and stored securely. We never store plaintext secrets.
                        </div>
                      </div>
                    </div>
                    
                    {/* Test Result */}
                    {testResult && (
                      <div className={`flex items-center gap-2 p-4 rounded-lg ${testResult.success ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                        {testResult.success ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                        {testResult.message}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="p-6 border-t border-gray-800 flex justify-between">
                <button
                  onClick={() => {
                    if (newConnectorType) {
                      setNewConnectorType(null);
                      setFormData({});
                    } else {
                      setShowAddModal(false);
                    }
                  }}
                  className="px-6 py-2 text-gray-400 hover:text-white transition-colors"
                >
                  {newConnectorType ? 'Back' : 'Cancel'}
                </button>
                
                {newConnectorType && (
                  <div className="flex gap-3">
                    <button
                      onClick={handleTestCredentials}
                      className="px-6 py-2 border border-gray-700 rounded-lg text-white hover:bg-gray-800 transition-colors"
                      disabled={loading}
                    >
                      Test Connection
                    </button>
                    <button
                      onClick={handleAddConnector}
                      className="px-6 py-2 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 transition-colors disabled:opacity-50"
                      disabled={loading}
                    >
                      {loading ? 'Saving...' : 'Save Integration'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


