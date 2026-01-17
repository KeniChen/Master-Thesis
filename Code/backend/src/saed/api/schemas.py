"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

# ============== Table Schemas ==============


class TableInfo(BaseModel):
    """Table metadata."""

    id: str
    name: str
    filename: str | None = None
    columns: list[str]
    row_count: int
    column_count: int | None = None
    category: str | None = None


class TablePreview(BaseModel):
    """Table preview data."""

    id: str
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int


class TableListResponse(BaseModel):
    """Response for table list endpoint."""

    tables: list[TableInfo]


# ============== Ontology Schemas ==============


class OntologyInfo(BaseModel):
    """Ontology metadata."""

    id: str
    class_count: int
    max_depth: int = 0
    filename: str | None = None


class OntologyClass(BaseModel):
    """Ontology class information."""

    url: str
    name: str
    label: str | None = None
    comment: str | None = None


class OntologyNode(BaseModel):
    """Ontology node with children."""

    url: str
    name: str
    label: str | None = None
    comment: str | None = None
    children: list[str] = []
    depth: int = 0
    has_more: bool = False  # Indicates node has unloaded children (lazy loading)


class OntologyTree(BaseModel):
    """Ontology tree structure."""

    root: str
    nodes: dict[str, OntologyNode]
    truncated: bool = False  # True if tree was limited by depth param
    total_nodes: int = 0  # Total nodes in full tree


class OntologyListResponse(BaseModel):
    """Response for ontology list endpoint."""

    ontologies: list[OntologyInfo]


# ============== Run Schemas ==============


class RunConfig(BaseModel):
    """Run configuration."""

    table_id: str
    ontology_id: str
    columns: list[str]
    mode: str = "single"  # single or edm
    prompt_type: str = "cot"  # direct or cot
    max_depth: int = 3
    k: int = 5
    edm_options: dict[str, Any] | None = None


# ============== LLM Request/Response Schemas ==============


class LLMRequest(BaseModel):
    """LLM request details for traceability."""

    prompt: str  # Complete prompt sent to LLM
    model: str  # Model used (e.g., "gpt-4o-mini")
    timestamp: datetime | None = None  # When the request was made


class LLMResponse(BaseModel):
    """LLM response details."""

    raw: str  # Raw response from LLM
    reasoning: str | None = None  # Extracted reasoning (CoT mode only)
    answer: str  # Extracted answer
    latency_ms: int | None = None  # Response latency in milliseconds
    input_tokens: int | None = None  # Input tokens used
    output_tokens: int | None = None  # Output tokens generated
    total_tokens: int | None = None  # Total tokens used


# ============== EDM (Ensemble Decision Making) Schemas ==============


class VoteSummary(BaseModel):
    """Vote summary for a single ontology class."""

    class_name: str
    vote_count: int
    total_agents: int
    percentage: float  # vote_count / total_agents
    selected: bool  # Whether this class reached consensus threshold


class AgentResult(BaseModel):
    """Complete information for a single EDM agent."""

    agent_id: int  # Agent number (1, 2, 3, ...)
    assigned_classes: list[str]  # Classes this agent saw (subset)
    llm_request: LLMRequest | None = None
    llm_response: LLMResponse | None = None  # Contains reasoning for CoT mode
    voted_classes: list[str]  # Classes this agent voted for
    status: str = "success"  # "success" | "failed"
    error: str | None = None


class EDMResult(BaseModel):
    """Complete EDM result including all agent details."""

    consensus_threshold: float  # e.g., 0.8 for 80%
    total_agents: int
    votes_summary: list[VoteSummary]  # Summary for each class that got votes
    agents: list[AgentResult]  # Detailed info for each agent


# ============== BFS Step Schemas ==============


class BFSStep(BaseModel):
    """A single BFS step in the annotation process."""

    level: int  # Ontology level (0, 1, 2, ...)
    parent: str  # Parent class name
    candidates: list[str]  # Candidate classes at this level
    selected: list[str]  # Selected classes
    status: str = "completed"  # "completed" | "failed" | "terminated"
    error: str | None = None  # Error description if failed

    # Single mode - direct LLM interaction
    llm_request: LLMRequest | None = None
    llm_response: LLMResponse | None = None

    # EDM mode - ensemble voting
    edm_result: EDMResult | None = None


class ColumnResult(BaseModel):
    """Annotation result for a single column."""

    column_name: str
    status: str  # "completed" | "failed" | "partial"
    steps: list[BFSStep]
    final_paths: list[list[str]]
    error: str | None = None  # Error description if failed


class RunSummary(BaseModel):
    """Summary statistics for a run."""

    total_columns: int
    completed_columns: int
    failed_columns: int
    partial_columns: int  # Columns with some paths successful


class EvaluationMetrics(BaseModel):
    """Evaluation metrics."""

    has_ground_truth: bool = False
    path_f1: float | None = None
    path_precision: float | None = None
    path_recall: float | None = None
    node_f1: float | None = None


class RunResult(BaseModel):
    """Complete run result."""

    run_id: str
    created_at: datetime
    completed_at: datetime | None = None
    status: str  # "pending" | "running" | "completed" | "failed" | "partial"
    config: RunConfig
    columns: list[ColumnResult] = []
    summary: RunSummary | None = None
    evaluation: EvaluationMetrics | None = None
    error: str | None = None  # Global error if run failed


class RunListItem(BaseModel):
    """Summary item for run list."""

    run_id: str
    table_id: str
    table_name: str
    mode: str
    prompt_type: str
    column_count: int
    status: str
    created_at: datetime
    evaluation: EvaluationMetrics | None = None


class RunListResponse(BaseModel):
    """Response for run list endpoint."""

    runs: list[RunListItem]


class CreateRunRequest(BaseModel):
    """Request to create a new run."""

    table_id: str
    ontology_id: str
    columns: list[str]
    mode: str = "single"
    prompt_type: str = "cot"
    max_depth: int = 3
    k: int = 5
    edm_options: dict[str, Any] | None = None


class CreateRunResponse(BaseModel):
    """Response for create run endpoint."""

    run_id: str
    status: str


# ============== Config Schemas ==============


class ConfigResponse(BaseModel):
    """Configuration response."""

    llm: dict[str, Any]
    defaults: dict[str, Any]
    paths: dict[str, str]


# ============== Provider Schemas ==============


class ProviderInfo(BaseModel):
    """Information about a single provider."""

    configured: bool
    status: str  # connected, error, not_configured, unknown
    config: dict[str, Any]


class ProvidersResponse(BaseModel):
    """Response for providers list endpoint."""

    active_provider: str
    providers: dict[str, ProviderInfo]


class ProviderTestResponse(BaseModel):
    """Response for provider connection test."""

    success: bool
    message: str
    latency_ms: int | None = None


class UpdateProviderRequest(BaseModel):
    """Request to update a provider's configuration."""

    config: dict[str, str | list[str]]


class SetActiveProviderRequest(BaseModel):
    """Request to set the active provider."""

    provider: str


class ModelsListResponse(BaseModel):
    """Response for listing available models from a provider."""

    models: list[str]
    source: str  # "remote" or "static"


# ============== LLM Chat Schemas ==============


class ChatRequest(BaseModel):
    """Request for LLM chat endpoint."""

    message: str
    provider: str | None = None  # Optional, defaults to active_provider
    model: str | None = None  # Optional, defaults to default_model


class ChatResponse(BaseModel):
    """Response from LLM chat endpoint."""

    response: str
    provider: str
    model: str
    latency_ms: int | None = None
