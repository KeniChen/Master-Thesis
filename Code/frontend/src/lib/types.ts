// Ontology Types
export interface OntologyClass {
  url: string
  name: string
  label: string | null
  comment: string | null
}

export interface OntologyNode extends OntologyClass {
  children: string[] // URLs of children
  depth: number
  has_more: boolean // Indicates node has unloaded children (lazy loading)
}

export interface OntologyDAG {
  root: string
  nodes: Record<string, OntologyNode>
  truncated: boolean // True if tree was limited by depth param
  total_nodes: number // Total nodes in full tree
}

export interface OntologyInfo {
  id: string
  class_count: number
  max_depth: number
  filename: string | null
}

// Table Types
export interface TableInfo {
  id: string
  name: string
  filename?: string
  columns: string[]
  row_count: number
  column_count?: number
  category?: string
}

export interface TablePreview {
  id: string
  name: string
  columns: string[]
  rows: Record<string, unknown>[]
  total_rows: number
}

export interface TableData {
  id: string
  name: string
  columns: string[]
  data: Record<string, unknown>[]
  preview_rows: number
}

export interface ColumnInfo {
  name: string
  dtype: string
  unique_count: number
  sample_values: string[]
}

// Annotation Types
export type DecisionMode = "single" | "edm"
export type PromptType = "direct" | "cot"

export interface EDMOptions {
  classes_per_agent: number
  agents_per_class: number
  consensus_threshold: number
}

export interface RunConfig {
  table_id: string
  table_registry_id?: string  // Registry hash ID for reference
  ontology_id: string
  ontology_registry_id?: string  // Registry slug ID for reference
  columns: string[]
  mode: DecisionMode
  prompt_type: PromptType
  max_depth: number
  k: number
  edm_options?: EDMOptions
}

// ============== LLM Request/Response Types ==============

export interface LLMRequest {
  prompt: string
  model: string
  timestamp?: string
}

export interface LLMResponse {
  raw: string
  reasoning?: string // Extracted reasoning (CoT mode only)
  answer: string
  latency_ms?: number
  input_tokens?: number // Input tokens used
  output_tokens?: number // Output tokens generated
  total_tokens?: number // Total tokens used
}

// ============== EDM (Ensemble Decision Making) Types ==============

export interface VoteSummary {
  class_name: string
  vote_count: number
  total_agents: number
  percentage: number // vote_count / total_agents
  selected: boolean // Whether this class reached consensus threshold
}

export interface AgentResult {
  agent_id: number // Agent number (1, 2, 3, ...)
  assigned_classes: string[] // Classes this agent saw (subset)
  llm_request?: LLMRequest
  llm_response?: LLMResponse // Contains reasoning for CoT mode
  voted_classes: string[] // Classes this agent voted for
  status: "success" | "failed"
  error?: string
}

export interface EDMResult {
  consensus_threshold: number // e.g., 0.8 for 80%
  total_agents: number
  votes_summary: VoteSummary[] // Summary for each class that got votes
  agents: AgentResult[] // Detailed info for each agent
}

// Legacy type for backwards compatibility
export interface EDMVote {
  votes: number
  seen_by: number
  ratio: number
}

// ============== BFS Step Types ==============

export type BFSStepStatus = "completed" | "failed" | "terminated"

export interface BFSStep {
  level: number // Ontology level (0, 1, 2, ...)
  parent: string // Parent class name
  candidates: string[] // Candidate classes at this level
  selected: string[] // Selected classes
  status: BFSStepStatus
  error?: string // Error description if failed

  // Single mode - direct LLM interaction
  llm_request?: LLMRequest
  llm_response?: LLMResponse

  // EDM mode - ensemble voting
  edm_result?: EDMResult

  // Legacy field for backwards compatibility
  edm_votes?: Record<string, EDMVote>
}

// ============== Column Result Types ==============

export type ColumnStatus = "completed" | "failed" | "partial"

export interface ColumnResult {
  column_name: string
  status: ColumnStatus
  steps: BFSStep[]
  final_paths: string[][]
  error?: string // Error description if failed
}

// ============== Run Types ==============

export type RunStatus = "pending" | "running" | "completed" | "failed" | "partial"

export interface RunSummary {
  total_columns: number
  completed_columns: number
  failed_columns: number
  partial_columns: number // Columns with some paths successful
}

export interface EvaluationMetrics {
  has_ground_truth: boolean
  path_f1?: number
  path_precision?: number
  path_recall?: number
  node_f1?: number
}

export interface RunResult {
  run_id: string
  created_at: string
  completed_at?: string
  status: RunStatus
  config: RunConfig
  columns: ColumnResult[]
  summary?: RunSummary
  evaluation?: EvaluationMetrics
  error?: string // Global error if run failed
}

export interface RunListItem {
  run_id: string
  table_id: string
  table_name: string
  mode: DecisionMode
  prompt_type: PromptType
  column_count: number
  status: RunStatus
  created_at: string
  evaluation?: EvaluationMetrics
}

// ============== SSE Event Types ==============

export type SSEEventType = "step" | "column_start" | "column_complete" | "run_complete" | "error"

export interface SSEStepEvent {
  run_id: string
  column_name: string
  step: BFSStep
  current_path: string[]
  status: "in_progress" | "completed" | "terminated"
}

export interface SSEColumnStartEvent {
  run_id: string
  column_name: string
  column_index: number
  total_columns: number
}

export interface SSEColumnCompleteEvent {
  run_id: string
  column_name: string
  final_paths: string[][]
  status: ColumnStatus
}

export interface SSERunCompleteEvent {
  run_id: string
  status: RunStatus
  summary?: RunSummary
}

export interface SSEErrorEvent {
  run_id: string
  column_name?: string
  error: string
  recoverable: boolean
}

export type SSEEvent =
  | { type: "step"; data: SSEStepEvent }
  | { type: "column_start"; data: SSEColumnStartEvent }
  | { type: "column_complete"; data: SSEColumnCompleteEvent }
  | { type: "run_complete"; data: SSERunCompleteEvent }
  | { type: "error"; data: SSEErrorEvent }

// Legacy type for backwards compatibility
export interface BFSStepEvent {
  run_id: string
  column_name: string
  step: BFSStep
  current_path: string[]
  status: "in_progress" | "completed" | "terminated"
}

// Config Types
export type ProviderName = "ollama" | "azure_openai" | "openai" | "anthropic" | "google" | "litellm"
export type ProviderStatus = "connected" | "error" | "not_configured" | "unknown"

export const PROVIDER_LABELS: Record<ProviderName, string> = {
  ollama: "Ollama",
  azure_openai: "Azure OpenAI",
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
  litellm: "LiteLLM",
}

export interface OllamaConfig {
  base_url: string
  models: string[]
  default_model: string
}

export interface AzureOpenAIConfig {
  endpoint: string
  api_key: string
  models: string[]
  default_model: string
}

export interface OpenAIConfig {
  api_key: string
  models: string[]
  default_model: string
}

export interface AnthropicConfig {
  api_key: string
  models: string[]
  default_model: string
}

export interface GoogleConfig {
  api_key: string
  models: string[]
  default_model: string
}

export interface LiteLLMConfig {
  api_key: string
  api_base: string
  models: string[]
  default_model: string
}

export interface ProvidersConfig {
  ollama: OllamaConfig
  azure_openai: AzureOpenAIConfig
  openai: OpenAIConfig
  anthropic: AnthropicConfig
  google: GoogleConfig
  litellm: LiteLLMConfig
}

export interface LLMConfig {
  active_provider: ProviderName
  providers: ProvidersConfig
}

export interface ProviderInfo {
  configured: boolean
  status: ProviderStatus
  config: Record<string, string | string[]>
}

export interface ProvidersResponse {
  active_provider: ProviderName
  providers: Record<ProviderName, ProviderInfo>
}

export interface ProviderTestResponse {
  success: boolean
  message: string
  latency_ms?: number
}

export interface DefaultsConfig {
  mode: DecisionMode
  prompt_type: PromptType
  max_depth: number
  k: number
  edm_options: EDMOptions
}

export interface PathsConfig {
  tables: string
  ontologies: string
  runs: string
  labels: string
}

export interface AppConfig {
  llm: LLMConfig
  defaults: DefaultsConfig
  paths: PathsConfig
}

// Model Discovery
export interface ModelsListResponse {
  models: string[]
  source: "remote" | "static"
}

// LLM Chat
export interface ChatResponse {
  response: string
  provider: ProviderName
  model: string
  latency_ms?: number
}

// ============== Labels (Ground Truth) Types ==============

export interface LabelsInfo {
  id: string
  filename: string
  name: string
  description?: string
  created_at?: string
  stats?: {
    total_tables: number
    total_columns: number
  }
}

export interface LabelsPreview {
  columns: string[]
  rows: Record<string, unknown>[]
  total_rows: number
  preview_rows: number
}

// ============== Batch Types ==============

export interface BatchConfig {
  ontology_id: string
  mode: string
  prompt_type: string
  max_depth: number
  k: number
  provider?: string
  model?: string
}

export interface BatchInfo {
  id: string
  filename: string
  name: string
  description?: string
  run_id?: string
  created_at?: string
  config: BatchConfig
  stats: {
    total_tables: number
    total_columns: number
    completed_columns: number
  }
}

export interface BatchPreview {
  run_id: string
  config: BatchConfig
  summary: {
    total_tables: number
    total_columns: number
    completed_columns: number
  }
  tables: {
    table_id: string
    table_name: string
    columns: {
      column_name: string
      status: string
      final_paths: string[][]
    }[]
    total_columns: number
  }[]
  total_tables: number
  preview_tables: number
}

// ============== Evaluation Types ==============

export interface MetricsLevel {
  macro_precision: number
  macro_recall: number
  macro_f1: number
  micro_precision: number
  micro_recall: number
  micro_f1: number
}

export interface EvaluationConfig {
  ontology_id: string
  mode: string
  prompt_type: string
  max_depth: number
  k: number
  provider?: string
  model?: string
}

export interface EvaluationSummary {
  total_tables: number
  total_columns: number
  evaluated_columns: number
  skipped_columns: number
}

export interface EvaluationPerformance {
  total_time_ms: number
  avg_time_per_column_ms: number
  total_tokens: number
}

export interface ColumnEvaluation {
  table_id: string
  table_name: string
  column_id: number
  column_name: string
  pred_paths: string[][]
  gt_paths: string[][]
  path_precision: number
  path_recall: number
  path_f1: number
  node_precision: number
  node_recall: number
  node_f1: number
}

export interface EvaluationResult {
  run_id: string
  evaluated_at: string
  labels_id: string
  config: EvaluationConfig
  summary: EvaluationSummary
  metrics: {
    path_level: MetricsLevel
    node_level: MetricsLevel
  }
  performance: EvaluationPerformance
  columns: ColumnEvaluation[]
}

export interface ComparisonResult {
  run_id: string
  batch_path: string
  config: EvaluationConfig
  summary: EvaluationSummary
  metrics: {
    path_level: MetricsLevel
    node_level: MetricsLevel
  }
  performance: EvaluationPerformance
  error?: string
}

export interface EvaluationComparison {
  compared_at: string
  labels_id: string
  total_batches: number
  successful: number
  failed: number
  best_scores: {
    path_macro_f1: number | null
    node_macro_f1: number | null
  }
  results: ComparisonResult[]
}

export interface EvaluationCSV {
  run_id: string
  headers: string[]
  rows: (string | number)[][]
}
