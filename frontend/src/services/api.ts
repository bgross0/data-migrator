import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Datasets API
export const datasetsApi = {
  list: async () => {
    const response = await api.get('/datasets')
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get(`/datasets/${id}`)
    return response.data
  },

  upload: async (file: File, name?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (name) {
      formData.append('name', name)
    }

    const response = await api.post('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  delete: async (id: number) => {
    const response = await api.delete(`/datasets/${id}`)
    return response.data
  },
}

// Mappings API
export const mappingsApi = {
  list: async (datasetId: number) => {
    const response = await api.get(`/datasets/${datasetId}/mappings`)
    return response.data
  },

  generate: async (datasetId: number) => {
    const response = await api.post(`/datasets/${datasetId}/mappings/generate`)
    return response.data
  },

  update: async (mappingId: number, data: Record<string, unknown>) => {
    const response = await api.put(`/mappings/${mappingId}`, data)
    return response.data
  },

  delete: async (mappingId: number) => {
    const response = await api.delete(`/mappings/${mappingId}`)
    return response.data
  },

  createLambda: async (datasetId: number, sheetId: number, lambdaData: any) => {
    const response = await api.post(`/datasets/${datasetId}/lambda-mappings`, {
      sheet_id: sheetId,
      ...lambdaData
    })
    return response.data
  },
}

// Modules API
export const modulesApi = {
  list: async () => {
    const response = await api.get('/modules')
    return response.data
  },

  setDatasetModules: async (datasetId: number, modules: string[]) => {
    const response = await api.post(`/datasets/${datasetId}/modules`, modules)
    return response.data
  },

  getDatasetModules: async (datasetId: number) => {
    const response = await api.get(`/datasets/${datasetId}/modules`)
    return response.data
  },

  suggestModules: async (datasetId: number) => {
    const response = await api.post(`/datasets/${datasetId}/suggest-modules`)
    return response.data
  },
}

// Sheets API
export const sheetsApi = {
  getProfiles: async (sheetId: number) => {
    const response = await api.get(`/sheets/${sheetId}/profiles`)
    return response.data
  },

  download: async (sheetId: number) => {
    const response = await api.get(`/sheets/${sheetId}/download`)
    return response.data
  },

  previewSplit: async (sheetId: number) => {
    const response = await api.get(`/sheets/${sheetId}/preview-split`)
    return response.data
  },

  executeSplit: async (sheetId: number, data: { models: string[]; delete_original?: boolean }) => {
    const response = await api.post(`/sheets/${sheetId}/split`, data)
    return response.data
  },
}

// Operations API
export const operationsApi = {
  getStatus: async (operationId: string) => {
    const response = await api.get(`/operations/${operationId}/status`)
    return response.data
  },
}

// Runs API
export const runsApi = {
  list: async () => {
    const response = await api.get('/runs')
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get(`/runs/${id}`)
    return response.data
  },

  create: async (datasetId: number, data: { graph_id?: number; dry_run?: boolean }) => {
    const response = await api.post(`/datasets/${datasetId}/runs`, data)
    return response.data
  },

  rollback: async (id: number) => {
    const response = await api.post(`/runs/${id}/rollback`)
    return response.data
  },
}

// Health API
export const healthApi = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },
}

export default api
