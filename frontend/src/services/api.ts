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

  getCleaningReport: async (id: number) => {
    const response = await api.get(`/datasets/${id}/cleaning-report`)
    return response.data
  },

  getCleanedDataPreview: async (id: number, limit = 100) => {
    const response = await api.get(`/datasets/${id}/cleaned-data`, {
      params: { limit },
    })
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

// Transforms API
export const transformsApi = {
  available: async () => {
    const response = await api.get('/transforms/available')
    return response.data
  },

  list: async (mappingId: number) => {
    const response = await api.get(`/mappings/${mappingId}/transforms`)
    return response.data
  },

  create: async (
    mappingId: number,
    data: { fn: string; params?: Record<string, unknown> | null }
  ) => {
    const response = await api.post(`/mappings/${mappingId}/transforms`, data)
    return response.data
  },

  update: async (
    transformId: number,
    data: { fn?: string; order?: number; params?: Record<string, unknown> | null }
  ) => {
    const response = await api.put(`/transforms/${transformId}`, data)
    return response.data
  },

  remove: async (transformId: number) => {
    const response = await api.delete(`/transforms/${transformId}`)
    return response.data
  },

  reorder: async (transformId: number, newOrder: number) => {
    const response = await api.post(
      `/transforms/${transformId}/reorder`,
      null,
      { params: { new_order: newOrder } }
    )
    return response.data
  },

  test: async (data: { fn: string; params?: Record<string, unknown> | null; sample_value: unknown }) => {
    const response = await api.post('/transforms/test', data)
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

// Graphs API
export const graphsApi = {
  create: async (graphData: any) => {
    const response = await api.post('/graphs', graphData)
    return response.data
  },

  get: async (graphId: string) => {
    const response = await api.get(`/graphs/${graphId}`)
    return response.data
  },

  list: async (limit = 100, offset = 0) => {
    const response = await api.get('/graphs', {
      params: { limit, offset }
    })
    return response.data
  },

  update: async (graphId: string, graphData: any) => {
    const response = await api.put(`/graphs/${graphId}`, graphData)
    return response.data
  },

  delete: async (graphId: string) => {
    const response = await api.delete(`/graphs/${graphId}`)
    return response.data
  },

  validate: async (graphId: string) => {
    const response = await api.post(`/graphs/${graphId}/validate`)
    return response.data
  },

  run: async (graphId: string, datasetId?: number) => {
    const config = datasetId !== undefined ? { params: { dataset_id: datasetId } } : {}
    const response = await api.post(`/graphs/${graphId}/run`, null, config)
    return response.data
  },

  getRuns: async (graphId: string) => {
    const response = await api.get(`/graphs/${graphId}/runs`)
    return response.data
  },

  getRunStatus: async (runId: string) => {
    const response = await api.get(`/runs/${runId}`)
    return response.data
  },
}

// Templates API
export const templatesApi = {
  list: async (category?: string) => {
    const response = await api.get('/templates', {
      params: category ? { category } : {}
    })
    return response.data
  },

  get: async (templateId: string) => {
    const response = await api.get(`/templates/${templateId}`)
    return response.data
  },

  getCategories: async () => {
    const response = await api.get('/templates/categories')
    return response.data
  },

  getProgress: async (templateId: string) => {
    const response = await api.get(`/templates/${templateId}/progress`)
    return response.data
  },

  instantiate: async (templateId: string, datasetId?: number, customName?: string) => {
    const response = await api.post(`/templates/${templateId}/instantiate`, {
      datasetId,
      customName
    })
    return response.data
  },
}

// Assistant API
export const assistantApi = {
  chat: async (message: string, context?: Record<string, unknown>) => {
    const response = await api.post('/assistant/chat', {
      message,
      context
    })
    return response.data
  },

  getSuggestions: async (page: string, datasetId?: number) => {
    const response = await api.get('/assistant/suggestions', {
      params: {
        page,
        dataset_id: datasetId
      }
    })
    return response.data
  },
}

export default api
