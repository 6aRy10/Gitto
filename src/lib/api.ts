import axios from 'axios';

const envApiBase = process.env.NEXT_PUBLIC_API_URL;
const isProd = process.env.NODE_ENV === 'production';

if (isProd && !envApiBase) {
  throw new Error('NEXT_PUBLIC_API_URL must be set in production to reach the backend API');
}

const API_BASE_URL = envApiBase || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getSnapshots = () => api.get('/snapshots').then(res => res.data);
export const getForecast = (snapshotId: number, groupBy: string = 'week') => 
  api.get(`/snapshots/${snapshotId}/forecast?group_by=${groupBy}`).then(res => res.data);
export const getKPIs = (snapshotId: number) => 
  api.get(`/snapshots/${snapshotId}/kpis`).then(res => res.data);
export const uploadExcel = (file: File, entityId?: number) => {
  const formData = new FormData();
  formData.append('file', file);
  const url = entityId ? `/upload?entity_id=${entityId}` : '/upload';
  return api.post(url, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data);
};

// Variance Service
export const getVariance = (snapshotId: number, compareId?: number) => {
  const url = compareId 
    ? `/snapshots/${snapshotId}/variance?compare_id=${compareId}`
    : `/snapshots/${snapshotId}/variance`;
  return api.get(url).then(res => res.data);
};

export const getVarianceDrilldown = (snapshotId: number, compareId: number, weekIndex: number, varianceType: string) =>
  api.get(`/snapshots/${snapshotId}/variance-drilldown?compare_id=${compareId}&week_index=${weekIndex}&variance_type=${varianceType}`).then(res => res.data);

// Red Weeks Service
export const getRedWeeks = (snapshotId: number, threshold?: number) => {
  const url = threshold 
    ? `/snapshots/${snapshotId}/red-weeks?threshold=${threshold}`
    : `/snapshots/${snapshotId}/red-weeks`;
  return api.get(url).then(res => res.data);
};

export const getRedWeekDrilldown = (snapshotId: number, weekIndex: number) =>
  api.get(`/snapshots/${snapshotId}/red-weeks/${weekIndex}/drilldown`).then(res => res.data);

// Truth Labeling Service
export const getTruthLabels = (snapshotId: number) =>
  api.get(`/snapshots/${snapshotId}/truth-labels`).then(res => res.data);

// Unmatched Transaction Lifecycle
export const getUnmatchedTransactions = (entityId: number, status?: string, assignee?: string) => {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (assignee) params.append('assignee', assignee);
  const query = params.toString();
  return api.get(`/entities/${entityId}/unmatched-transactions${query ? '?' + query : ''}`).then(res => res.data);
};

export const updateTransactionStatus = (transactionId: number, status: string) =>
  api.patch(`/transactions/${transactionId}/status`, status).then(res => res.data);

export const assignTransaction = (transactionId: number, assignee: string) =>
  api.post(`/transactions/${transactionId}/assign`, assignee).then(res => res.data);

export const getSLAAging = (entityId: number) =>
  api.get(`/entities/${entityId}/sla-aging`).then(res => res.data);

// Matching Policy
export const getMatchingPolicy = (entityId: number, currency?: string) => {
  const url = currency 
    ? `/entities/${entityId}/matching-policy?currency=${currency}`
    : `/entities/${entityId}/matching-policy`;
  return api.get(url).then(res => res.data);
};

export const setMatchingPolicy = (entityId: number, policy: {
  currency?: string;
  amount_tolerance?: number;
  date_window_days?: number;
  tier_enabled?: Record<string, boolean>;
}) =>
  api.post(`/entities/${entityId}/matching-policy`, policy).then(res => res.data);

// Audit Trail
export const getAuditTrail = (filters?: {
  resource_type?: string;
  resource_id?: number;
  action?: string;
  user?: string;
  since?: string;
}) => {
  const params = new URLSearchParams();
  if (filters?.resource_type) params.append('resource_type', filters.resource_type);
  if (filters?.resource_id) params.append('resource_id', filters.resource_id.toString());
  if (filters?.action) params.append('action', filters.action);
  if (filters?.user) params.append('user', filters.user);
  if (filters?.since) params.append('since', filters.since);
  const query = params.toString();
  return api.get(`/audit-trail${query ? '?' + query : ''}`).then(res => res.data);
};

export const getSnapshotLineage = (snapshotId: number) =>
  api.get(`/snapshots/${snapshotId}/lineage`).then(res => res.data);

// Liquidity Levers
export const predictLeverImpact = (actionId: number) =>
  api.post(`/treasury-actions/${actionId}/predict-impact`).then(res => res.data);

export const trackLeverOutcome = (actionId: number, outcome: {
  actual_amount?: number;
  actual_date?: string;
  notes?: string;
}) =>
  api.post(`/treasury-actions/${actionId}/track-outcome`, outcome).then(res => res.data);

export const getLeverPerformance = (snapshotId: number) =>
  api.get(`/snapshots/${snapshotId}/lever-performance`).then(res => res.data);

// Unknown Bucket
export const setUnknownBucketKPI = (snapshotId: number, kpiTarget: number) =>
  api.patch(`/snapshots/${snapshotId}/unknown-bucket-kpi`, kpiTarget).then(res => res.data);

// Upsert & Meeting Mode
export const setUpsertMode = (snapshotId: number, mode: {
  mode: 'replace' | 'merge';
  dedup_strategy?: string;
}) =>
  api.post(`/snapshots/${snapshotId}/upsert-mode`, mode).then(res => res.data);

export const executeMeetingMode = (snapshotId: number) =>
  api.post(`/snapshots/${snapshotId}/meeting-mode`).then(res => res.data);

// Async Operations
export const startAsyncUploadParsing = (file: File, entityId?: number, mappingConfig?: Record<string, string>) => {
  const formData = new FormData();
  formData.append('file', file);
  if (entityId) formData.append('entity_id', entityId.toString());
  if (mappingConfig) formData.append('mapping_config', JSON.stringify(mappingConfig));
  return api.post('/async/upload-parsing', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data);
};

export const startAsyncReconciliation = (entityId: number) =>
  api.post('/async/reconciliation', entityId).then(res => res.data);

export const startAsyncForecast = (snapshotId: number) =>
  api.post('/async/forecast', snapshotId).then(res => res.data);

export const getAsyncTaskStatus = (taskId: string) =>
  api.get(`/async/tasks/${taskId}`).then(res => res.data);

// ═══════════════════════════════════════════════════════════════════════════════
// TRUST REPORT API
// ═══════════════════════════════════════════════════════════════════════════════

export const getTrustReport = (snapshotId: number, regenerate: boolean = false) =>
  api.get(`/snapshots/${snapshotId}/trust${regenerate ? '?regenerate=true' : ''}`).then(res => res.data);

export const getTrustReportHistory = (snapshotId: number, limit: number = 10) =>
  api.get(`/snapshots/${snapshotId}/trust/history?limit=${limit}`).then(res => res.data);

export const getTrustMetricDetails = (snapshotId: number, metricKey: string) =>
  api.get(`/snapshots/${snapshotId}/trust/metric/${metricKey}`).then(res => res.data);

export const lockSnapshot = (snapshotId: number, payload: {
  user_id: string;
  user_email?: string;
  user_role?: string;
  override_acknowledgment?: string;
  override_reason?: string;
}) =>
  api.post(`/snapshots/${snapshotId}/lock`, payload).then(res => res.data);

export const getOverrideLogs = (snapshotId: number) =>
  api.get(`/snapshots/${snapshotId}/overrides`).then(res => res.data);

// ═══════════════════════════════════════════════════════════════════════════════
// INVARIANT ENGINE API
// ═══════════════════════════════════════════════════════════════════════════════

export const runInvariants = (snapshotId: number, triggeredBy: string = 'ui') =>
  api.post(`/snapshots/${snapshotId}/invariants/run?triggered_by=${triggeredBy}`).then(res => res.data);

export const getLatestInvariants = (snapshotId: number) =>
  api.get(`/snapshots/${snapshotId}/invariants/latest`).then(res => res.data);

export const getInvariantHistory = (snapshotId: number, limit: number = 10) =>
  api.get(`/snapshots/${snapshotId}/invariants/history?limit=${limit}`).then(res => res.data);

export const getInvariantSummary = (snapshotId: number) =>
  api.get(`/snapshots/${snapshotId}/invariants/summary`).then(res => res.data);

// ═══════════════════════════════════════════════════════════════════════════════
// DATA HEALTH REPORT API
// ═══════════════════════════════════════════════════════════════════════════════

export const getDatasetHealth = (datasetId: string) =>
  api.get(`/datasets/${datasetId}/health`).then(res => res.data);

export const getConnectionHealthLatest = (connectionId: number) =>
  api.get(`/connections/${connectionId}/health/latest`).then(res => res.data);

// ═══════════════════════════════════════════════════════════════════════════════
// EXTERNAL SYSTEM CERTIFICATION API
// ═══════════════════════════════════════════════════════════════════════════════

export const importTmsData = (formData: FormData) =>
  api.post('/external-certification/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(res => res.data);

export const listTmsImports = (snapshotId?: number, systemName?: string, limit: number = 20) => {
  const params = new URLSearchParams();
  if (snapshotId) params.append('snapshot_id', snapshotId.toString());
  if (systemName) params.append('system_name', systemName);
  params.append('limit', limit.toString());
  return api.get(`/external-certification/imports?${params}`).then(res => res.data);
};

export const getTmsImport = (importId: number) =>
  api.get(`/external-certification/imports/${importId}`).then(res => res.data);

export const generateCertificationReport = (importId: number, createdBy: string = 'api') =>
  api.post(`/external-certification/imports/${importId}/generate-report?created_by=${createdBy}`).then(res => res.data);

export const listCertificationReports = (snapshotId?: number, status?: string, limit: number = 20) => {
  const params = new URLSearchParams();
  if (snapshotId) params.append('snapshot_id', snapshotId.toString());
  if (status) params.append('status', status);
  params.append('limit', limit.toString());
  return api.get(`/external-certification/reports?${params}`).then(res => res.data);
};

export const getCertificationReport = (reportId: number) =>
  api.get(`/external-certification/reports/${reportId}`).then(res => res.data);

export const certifyReport = (reportId: number, certifiedBy: string, notes?: string) =>
  api.post(`/external-certification/reports/${reportId}/certify`, {
    certified_by: certifiedBy,
    notes: notes || ''
  }).then(res => res.data);

export const exportCertificationReport = (reportId: number, format: string = 'json') =>
  api.get(`/external-certification/reports/${reportId}/export?format=${format}`).then(res => res.data);

export const resolveDiscrepancy = (reportId: number, discrepancyId: number, resolutionNotes: string, resolvedBy: string) =>
  api.post(`/external-certification/reports/${reportId}/discrepancies/${discrepancyId}/resolve`, {
    resolution_notes: resolutionNotes,
    resolved_by: resolvedBy
  }).then(res => res.data);

export const getDiscrepancyEvidence = (reportId: number, discrepancyId: number) =>
  api.get(`/external-certification/reports/${reportId}/discrepancies/${discrepancyId}/evidence`).then(res => res.data);

export const getSnapshotCertificationStatus = (snapshotId: number) =>
  api.get(`/external-certification/snapshots/${snapshotId}/certification-status`).then(res => res.data);


