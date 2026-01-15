import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

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


