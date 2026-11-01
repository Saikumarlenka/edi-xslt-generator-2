import axios from 'axios';

const api = axios.create({ baseURL: '/api', timeout: 120000 });

// Health & references
export const getHealth = () => api.get('/health').then(r => r.data);
export const getReferences = (tx) => api.get(`/reference-files/${tx}`).then(r => r.data);
export const uploadReference = (tx, kind, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/reference-files/${tx}?kind=${encodeURIComponent(kind)}`, fd).then(r => r.data);
};

// Phase 1: Extract matrix (supports python deterministic and gemini models)
export const extractMatrix = (tx, file, method = 'python') => {
  const fd = new FormData();
  fd.append('transaction', tx);
  fd.append('matrix', file);
  fd.append('method', method);

  const endpoint = method === 'gemini' ? '/extract-matrix-gemini' : '/extract-matrix-python';
  return api.post(endpoint, fd, { timeout: 300000 })
    .catch(err => {
      // Fallback to /extract-matrix if backend hasn't reloaded the explicit endpoints
      if (err.response?.status === 404) {
        return api.post(`/extract-matrix?method=${encodeURIComponent(method)}`, fd, { timeout: 300000 });
      }
      throw err;
    })
    .then(r => (r.data !== undefined ? r.data : r));
};

// Phase 2: Generate XSLT from mapping
export const generateXslt = (jobId) => {
  return api.post(`/generate-xslt/${jobId}`).then(r => r.data);
};

// Legacy combined endpoint
export const startGeneration = (tx, file) => {
  const fd = new FormData();
  fd.append('transaction', tx);
  fd.append('matrix', file);
  return api.post('/generate', fd, { timeout: 120000 }).then(r => r.data);
};

// Job queries
export const getJob = (id) => api.get(`/jobs/${id}`).then(r => r.data);
export const getMapping = (id) => api.get(`/jobs/${id}/mapping`).then(r => r.data);
export const updateMapping = (id, mappings) => {
  return api.put(`/jobs/${id}/mapping`, { mappings }).then(r => r.data);
};
export const getXslt = (id) => api.get(`/jobs/${id}/xslt`).then(r => r.data);
export const getReport = (id) => api.get(`/jobs/${id}/report`).then(r => r.data);
export const getDownloadUrl = (id) => `/api/jobs/${id}/download`;
