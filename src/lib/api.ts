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


