import type {
  OntologyDAG,
  OntologyInfo,
  TableInfo,
  TablePreview,
  RunResult,
  RunListItem,
  AppConfig,
  BFSStepEvent,
  DecisionMode,
  PromptType,
  EDMOptions,
  ProviderName,
  ProvidersResponse,
  ProviderTestResponse,
  ModelsListResponse,
  ChatResponse,
  LabelsInfo,
  LabelsPreview,
  BatchInfo,
  BatchPreview,
  EvaluationResult,
  EvaluationComparison,
  EvaluationCSV,
} from "./types"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.text()
    throw new ApiError(response.status, error)
  }

  return response.json()
}

// Tables API
export const tablesApi = {
  list: () => fetchApi<{ tables: TableInfo[] }>("/tables").then(res => res.tables),

  get: (tableId: string, limit: number = 10) =>
    fetchApi<TablePreview>(`/tables/${encodeURIComponent(tableId)}?limit=${limit}`),

  preview: (tableId: string, rows: number = 10) =>
    fetchApi<TablePreview>(`/tables/${encodeURIComponent(tableId)}/preview?rows=${rows}`),

  upload: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${API_BASE_URL}/tables`, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new ApiError(response.status, error)
    }

    return response.json() as Promise<TableInfo>
  },

  update: (tableId: string, data: Record<string, unknown>[]) =>
    fetchApi<TableInfo>(`/tables/${encodeURIComponent(tableId)}`, {
      method: "PUT",
      body: JSON.stringify({ data }),
    }),

  delete: (tableId: string) =>
    fetchApi<{ message: string }>(`/tables/${encodeURIComponent(tableId)}`, {
      method: "DELETE",
    }),
}

// Ontologies API
export const ontologiesApi = {
  list: () => fetchApi<{ ontologies: OntologyInfo[] }>("/ontologies").then(res => res.ontologies),

  get: (ontologyId: string) =>
    fetchApi<OntologyInfo & { root: string }>(`/ontologies/${encodeURIComponent(ontologyId)}`),

  getTree: (ontologyId: string, options?: { depth?: number; root?: string }) => {
    const params = new URLSearchParams()
    if (options?.depth !== undefined) params.set("depth", String(options.depth))
    if (options?.root) params.set("root", options.root)
    const query = params.toString()
    return fetchApi<OntologyDAG>(
      `/ontologies/${encodeURIComponent(ontologyId)}/tree${query ? `?${query}` : ""}`
    )
  },

  getClasses: (ontologyId: string, search: string = "") =>
    fetchApi<{ classes: { url: string; name: string; label: string | null; comment: string | null }[]; total: number }>(
      `/ontologies/${encodeURIComponent(ontologyId)}/classes?search=${encodeURIComponent(search)}`
    ),

  upload: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${API_BASE_URL}/ontologies`, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new ApiError(response.status, error)
    }

    return response.json() as Promise<OntologyInfo>
  },

  delete: (ontologyId: string) =>
    fetchApi<{ message: string }>(`/ontologies/${encodeURIComponent(ontologyId)}`, {
      method: "DELETE",
    }),
}

// Runs API
export const runsApi = {
  list: () => fetchApi<{ runs: RunListItem[] }>("/runs").then(res => res.runs),

  get: (runId: string) => fetchApi<RunResult>(`/runs/${runId}`),

  create: (params: {
    table_id: string
    ontology_id: string
    columns: string[]
    mode: DecisionMode
    prompt_type: PromptType
    max_depth: number
    k: number
    edm_options?: EDMOptions
  }) =>
    fetchApi<{ run_id: string; status: string }>("/runs", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  delete: (runId: string) =>
    fetchApi<{ message: string }>(`/runs/${runId}`, {
      method: "DELETE",
    }),

  // SSE stream for real-time updates
  stream: (
    runId: string,
    handlers: {
      onStep?: (data: BFSStepEvent) => void
      onColumnStart?: (data: { run_id: string; column_name: string; column_index: number; total_columns: number }) => void
      onColumnComplete?: (data: { run_id: string; column_name: string; final_paths: string[][]; status: string }) => void
      onRunComplete?: (data: { run_id: string; status: string; summary?: { total_columns: number; completed_columns: number; failed_columns: number; partial_columns: number } }) => void
      onError?: (data: { run_id: string; error: string; recoverable: boolean }) => void
      onConnected?: (data: { run_id: string }) => void
    }
  ) => {
    const eventSource = new EventSource(`${API_BASE_URL}/runs/${runId}/stream`)

    eventSource.addEventListener("connected", (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      handlers.onConnected?.(data)
    })

    eventSource.addEventListener("step", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as BFSStepEvent
      handlers.onStep?.(data)
    })

    eventSource.addEventListener("column_start", (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      handlers.onColumnStart?.(data)
    })

    eventSource.addEventListener("column_complete", (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      handlers.onColumnComplete?.(data)
    })

    eventSource.addEventListener("run_complete", (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      handlers.onRunComplete?.(data)
      eventSource.close()
    })

    eventSource.addEventListener("error", (event) => {
      if ((event as MessageEvent).data) {
        const data = JSON.parse((event as MessageEvent).data)
        handlers.onError?.(data)
      }
      eventSource.close()
    })

    eventSource.onerror = () => {
      eventSource.close()
    }

    return () => eventSource.close()
  },
}

// Config API
export const configApi = {
  get: () => fetchApi<AppConfig>("/config"),

  update: (config: Partial<AppConfig>) =>
    fetchApi<{ message: string }>("/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),

  testConnection: () =>
    fetchApi<ProviderTestResponse>("/config/test", {
      method: "POST",
    }),
}

// Providers API
export const providersApi = {
  list: () => fetchApi<ProvidersResponse>("/config/llm/providers"),

  update: (provider: ProviderName, config: Record<string, string | string[]>) =>
    fetchApi<{ message: string }>(`/config/llm/providers/${provider}`, {
      method: "PUT",
      body: JSON.stringify({ config }),
    }),

  test: (provider: ProviderName) =>
    fetchApi<ProviderTestResponse>(`/config/llm/providers/${provider}/test`, {
      method: "POST",
    }),

  setActive: (provider: ProviderName) =>
    fetchApi<{ message: string }>("/config/llm/active", {
      method: "PUT",
      body: JSON.stringify({ provider }),
    }),

  listModels: (provider: ProviderName) =>
    fetchApi<ModelsListResponse>(`/config/llm/providers/${provider}/models`),
}

// LLM API
export const llmApi = {
  chat: (message: string, provider?: ProviderName, model?: string) =>
    fetchApi<ChatResponse>("/llm/chat", {
      method: "POST",
      body: JSON.stringify({ message, provider, model }),
    }),
}

// Health check
export const healthApi = {
  check: () => fetchApi<{ status: string }>("/health"),
}

// Labels API
export const labelsApi = {
  list: () => fetchApi<{ labels: LabelsInfo[] }>("/labels").then(res => res.labels),

  get: (labelsId: string) =>
    fetchApi<LabelsInfo>(`/labels/${encodeURIComponent(labelsId)}`),

  preview: (labelsId: string, limit: number = 10) =>
    fetchApi<LabelsPreview>(`/labels/${encodeURIComponent(labelsId)}/preview?limit=${limit}`),

  upload: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${API_BASE_URL}/labels/upload`, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new ApiError(response.status, error)
    }

    return response.json() as Promise<LabelsInfo>
  },

  delete: (labelsId: string) =>
    fetchApi<{ message: string }>(`/labels/${encodeURIComponent(labelsId)}`, {
      method: "DELETE",
    }),
}

// Batches API
export const batchesApi = {
  list: () => fetchApi<{ batches: BatchInfo[] }>("/batches").then(res => res.batches),

  get: (batchId: string) =>
    fetchApi<BatchInfo>(`/batches/${encodeURIComponent(batchId)}`),

  preview: (batchId: string, limit: number = 5) =>
    fetchApi<BatchPreview>(`/batches/${encodeURIComponent(batchId)}/preview?limit=${limit}`),

  upload: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${API_BASE_URL}/batches/upload`, {
      method: "POST",
      body: formData,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new ApiError(response.status, error)
    }

    return response.json() as Promise<BatchInfo>
  },

  delete: (batchId: string) =>
    fetchApi<{ message: string }>(`/batches/${encodeURIComponent(batchId)}`, {
      method: "DELETE",
    }),
}

// Evaluations API
export const evaluationsApi = {
  run: (batchPath: string, labelsId: string) =>
    fetchApi<EvaluationResult>("/evaluations", {
      method: "POST",
      body: JSON.stringify({ batch_path: batchPath, labels_id: labelsId }),
    }),

  compare: (batchPaths: string[], labelsId: string) =>
    fetchApi<EvaluationComparison>("/evaluations/compare", {
      method: "POST",
      body: JSON.stringify({ batch_paths: batchPaths, labels_id: labelsId }),
    }),

  getCSV: (batchPath: string, labelsId: string) =>
    fetchApi<EvaluationCSV>(`/evaluations/csv?batch_path=${encodeURIComponent(batchPath)}&labels_id=${encodeURIComponent(labelsId)}`),
}

export { ApiError }
