"""Run executor for semantic annotation tasks with detailed tracing."""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from saed.core.config.settings import Config, EDMOptions, load_config
from saed.core.llm import LLM
from saed.core.llm.parser import extract_answer, extract_reasoning, parse_class_list


@dataclass
class LLMRequestDetail:
    """Detailed LLM request information."""

    prompt: str
    model: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LLMResponseDetail:
    """Detailed LLM response information."""

    raw: str
    reasoning: str | None = None
    answer: str = ""
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class AgentResultDetail:
    """Result from a single EDM agent."""

    agent_id: int
    assigned_classes: list[str]
    llm_request: LLMRequestDetail | None = None
    llm_response: LLMResponseDetail | None = None
    voted_classes: list[str] = field(default_factory=list)
    status: str = "success"
    error: str | None = None


@dataclass
class VoteSummaryDetail:
    """Vote summary for a single class."""

    class_name: str
    vote_count: int
    total_agents: int
    percentage: float
    selected: bool


@dataclass
class EDMResultDetail:
    """Complete EDM result with all agent details."""

    consensus_threshold: float
    total_agents: int
    votes_summary: list[VoteSummaryDetail] = field(default_factory=list)
    agents: list[AgentResultDetail] = field(default_factory=list)


@dataclass
class SelectionResult:
    """Result from a selection operation with full details."""

    selected: list[str]
    status: str = "completed"  # completed, failed, terminated
    error: str | None = None

    # Single mode fields
    llm_request: LLMRequestDetail | None = None
    llm_response: LLMResponseDetail | None = None

    # EDM mode fields
    edm_result: EDMResultDetail | None = None


@dataclass
class BFSStepDetail:
    """Detailed BFS step information."""

    level: int
    parent: str
    candidates: list[str]
    selected: list[str]
    status: str = "completed"
    error: str | None = None
    llm_request: LLMRequestDetail | None = None
    llm_response: LLMResponseDetail | None = None
    edm_result: EDMResultDetail | None = None


@dataclass
class ColumnResultDetail:
    """Detailed result for a single column."""

    column_name: str
    status: str = "completed"
    steps: list[BFSStepDetail] = field(default_factory=list)
    final_paths: list[list[str]] = field(default_factory=list)
    error: str | None = None


class DetailedSelector:
    """Selector that returns detailed information about LLM interactions."""

    def __init__(
        self,
        config: Config | None = None,
        mode: str = "single",
        prompt_type: str = "cot",
        edm_options: EDMOptions | None = None,
        max_retries: int = 3,
    ) -> None:
        self.config = config or load_config()
        self.mode = mode
        self.prompt_type = prompt_type
        self.max_retries = max_retries

        # EDM options
        if edm_options:
            self.edm_options = edm_options
        else:
            self.edm_options = self.config.defaults.edm_options

        # Initialize LLM
        self.llm = LLM(
            config=self.config,
            mode=mode,
            prompt_type=prompt_type,
        )

        # Get model name for tracing
        from saed.core.config.settings import get_provider_model

        self.model_name = get_provider_model(
            self.config.llm.active_provider, self.config
        )

    def _build_prompt(self, data: dict[str, Any]) -> str:
        """Build the complete prompt string for tracing."""
        # This is a simplified version - the actual prompt comes from the chain
        return (
            f"Table: {data['table_name']}\n"
            f"Column: {data['column_name']}\n"
            f"Table Preview:\n{data['table_in_markdown']}\n"
            f"Candidates: {data['current_level_ontology_classes']}"
        )

    def _call_llm_with_retry(
        self, data: dict[str, Any]
    ) -> tuple[LLMRequestDetail, LLMResponseDetail]:
        """Call LLM with retry logic and return detailed request/response."""
        prompt = self._build_prompt(data)
        request = LLMRequestDetail(
            prompt=prompt,
            model=self.model_name,
            timestamp=datetime.now(),
        )

        last_error = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                llm_result = self.llm.generate(data)
                latency_ms = int((time.time() - start_time) * 1000)

                raw_response = llm_result.content
                answer = extract_answer(raw_response) or ""
                reasoning = None
                if self.prompt_type == "cot":
                    reasoning = extract_reasoning(raw_response)

                response = LLMResponseDetail(
                    raw=raw_response,
                    reasoning=reasoning,
                    answer=answer,
                    latency_ms=latency_ms,
                    input_tokens=llm_result.input_tokens,
                    output_tokens=llm_result.output_tokens,
                    total_tokens=llm_result.total_tokens,
                )
                return request, response

            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    time.sleep(2**attempt)

        # All retries failed
        response = LLMResponseDetail(
            raw=f"Error after {self.max_retries} retries: {last_error}",
            answer="",
            latency_ms=0,
        )
        return request, response

    async def _call_llm_with_retry_async(
        self, data: dict[str, Any]
    ) -> tuple[LLMRequestDetail, LLMResponseDetail]:
        """Async version: Call LLM with retry logic and return detailed request/response."""
        prompt = self._build_prompt(data)
        request = LLMRequestDetail(
            prompt=prompt,
            model=self.model_name,
            timestamp=datetime.now(),
        )

        last_error = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                llm_result = await self.llm.agenerate(data)
                latency_ms = int((time.time() - start_time) * 1000)

                raw_response = llm_result.content
                answer = extract_answer(raw_response) or ""
                reasoning = None
                if self.prompt_type == "cot":
                    reasoning = extract_reasoning(raw_response)

                response = LLMResponseDetail(
                    raw=raw_response,
                    reasoning=reasoning,
                    answer=answer,
                    latency_ms=latency_ms,
                    input_tokens=llm_result.input_tokens,
                    output_tokens=llm_result.output_tokens,
                    total_tokens=llm_result.total_tokens,
                )
                return request, response

            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(2**attempt)

        # All retries failed
        response = LLMResponseDetail(
            raw=f"Error after {self.max_retries} retries: {last_error}",
            answer="",
            latency_ms=0,
        )
        return request, response

    def select_single(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        candidates: list[str],
    ) -> SelectionResult:
        """Single-shot selection with detailed tracing."""
        if not candidates:
            return SelectionResult(selected=[], status="completed")

        data = {
            "table_name": table_name,
            "table_in_markdown": table_in_markdown,
            "column_name": column_name,
            "current_level_ontology_classes": ", ".join(candidates),
        }

        try:
            request, response = self._call_llm_with_retry(data)

            if not response.answer or response.answer == "-":
                return SelectionResult(
                    selected=[],
                    status="completed",
                    llm_request=request,
                    llm_response=response,
                )

            predicted = parse_class_list(response.answer)
            selected = [cls for cls in predicted if cls in candidates]

            return SelectionResult(
                selected=selected,
                status="completed",
                llm_request=request,
                llm_response=response,
            )

        except Exception as e:
            return SelectionResult(
                selected=[],
                status="failed",
                error=str(e),
            )

    async def select_single_async(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        candidates: list[str],
    ) -> SelectionResult:
        """Async version: Single-shot selection with detailed tracing."""
        if not candidates:
            return SelectionResult(selected=[], status="completed")

        data = {
            "table_name": table_name,
            "table_in_markdown": table_in_markdown,
            "column_name": column_name,
            "current_level_ontology_classes": ", ".join(candidates),
        }

        try:
            request, response = await self._call_llm_with_retry_async(data)

            if not response.answer or response.answer == "-":
                return SelectionResult(
                    selected=[],
                    status="completed",
                    llm_request=request,
                    llm_response=response,
                )

            predicted = parse_class_list(response.answer)
            selected = [cls for cls in predicted if cls in candidates]

            return SelectionResult(
                selected=selected,
                status="completed",
                llm_request=request,
                llm_response=response,
            )

        except Exception as e:
            return SelectionResult(
                selected=[],
                status="failed",
                error=str(e),
            )

    def select_edm(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        candidates: list[str],
    ) -> SelectionResult:
        """Ensemble decision making with detailed tracing."""
        if not candidates:
            return SelectionResult(selected=[], status="completed")

        # Calculate number of agents
        avg_classes_per_agent = self.edm_options.classes_per_agent
        avg_agents_per_class = self.edm_options.agents_per_class
        consensus_threshold = self.edm_options.consensus_threshold

        num_classes = len(candidates)
        num_agents = max(
            avg_agents_per_class,
            (num_classes * avg_agents_per_class) // avg_classes_per_agent + 1,
        )

        # Assign classes to agents
        agents_assignments = self._assign_classes_to_agents(
            candidates, num_agents, avg_agents_per_class
        )

        # Count how many agents saw each class
        agents_that_saw_class: dict[str, int] = defaultdict(int)
        for class_ in candidates:
            agents_that_saw_class[class_] = sum(
                1 for agent_classes in agents_assignments if class_ in agent_classes
            )

        # Collect votes from each agent
        agent_results: list[AgentResultDetail] = []
        votes_per_class: dict[str, int] = defaultdict(int)
        failed_agents = 0

        for agent_id, agent_classes in enumerate(agents_assignments, start=1):
            agent_result = AgentResultDetail(
                agent_id=agent_id,
                assigned_classes=agent_classes,
            )

            if not agent_classes:
                agent_result.status = "success"
                agent_result.voted_classes = []
                agent_results.append(agent_result)
                continue

            data = {
                "table_name": table_name,
                "table_in_markdown": table_in_markdown,
                "column_name": column_name,
                "current_level_ontology_classes": ", ".join(agent_classes),
            }

            try:
                request, response = self._call_llm_with_retry(data)
                agent_result.llm_request = request
                agent_result.llm_response = response

                if response.answer and response.answer != "-":
                    chosen = parse_class_list(response.answer)
                    valid_votes = [c for c in chosen if c in agent_classes]
                    agent_result.voted_classes = valid_votes
                    for cls in valid_votes:
                        votes_per_class[cls] += 1
                    agent_result.status = "success"
                else:
                    agent_result.status = "success"
                    agent_result.voted_classes = []

            except Exception as e:
                agent_result.status = "failed"
                agent_result.error = str(e)
                failed_agents += 1

            agent_results.append(agent_result)

        # Build vote summaries
        votes_summary: list[VoteSummaryDetail] = []
        selected_classes: list[str] = []

        for class_ in candidates:
            seen_by = agents_that_saw_class[class_]
            if seen_by > 0:
                votes = votes_per_class[class_]
                percentage = votes / seen_by
                is_selected = percentage >= consensus_threshold and votes > 0

                votes_summary.append(
                    VoteSummaryDetail(
                        class_name=class_,
                        vote_count=votes,
                        total_agents=seen_by,
                        percentage=percentage,
                        selected=is_selected,
                    )
                )

                if is_selected:
                    selected_classes.append(class_)

        # Sort by vote count descending
        votes_summary.sort(key=lambda x: x.vote_count, reverse=True)

        edm_result = EDMResultDetail(
            consensus_threshold=consensus_threshold,
            total_agents=len(agents_assignments),
            votes_summary=votes_summary,
            agents=agent_results,
        )

        # Determine status
        status = "completed"
        error = None
        if failed_agents > len(agents_assignments) * 0.5:
            status = "failed"
            error = f"{failed_agents}/{len(agents_assignments)} agents failed"

        return SelectionResult(
            selected=selected_classes,
            status=status,
            error=error,
            edm_result=edm_result,
        )

    async def select_edm_async(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        candidates: list[str],
    ) -> SelectionResult:
        """Async version: Ensemble decision making with detailed tracing."""
        if not candidates:
            return SelectionResult(selected=[], status="completed")

        # Calculate number of agents
        avg_classes_per_agent = self.edm_options.classes_per_agent
        avg_agents_per_class = self.edm_options.agents_per_class
        consensus_threshold = self.edm_options.consensus_threshold

        num_classes = len(candidates)
        num_agents = max(
            avg_agents_per_class,
            (num_classes * avg_agents_per_class) // avg_classes_per_agent + 1,
        )

        # Assign classes to agents
        agents_assignments = self._assign_classes_to_agents(
            candidates, num_agents, avg_agents_per_class
        )

        # Count how many agents saw each class
        agents_that_saw_class: dict[str, int] = defaultdict(int)
        for class_ in candidates:
            agents_that_saw_class[class_] = sum(
                1 for agent_classes in agents_assignments if class_ in agent_classes
            )

        # Collect votes from each agent (async)
        agent_results: list[AgentResultDetail] = []
        votes_per_class: dict[str, int] = defaultdict(int)
        failed_agents = 0

        for agent_id, agent_classes in enumerate(agents_assignments, start=1):
            agent_result = AgentResultDetail(
                agent_id=agent_id,
                assigned_classes=agent_classes,
            )

            if not agent_classes:
                agent_result.status = "success"
                agent_result.voted_classes = []
                agent_results.append(agent_result)
                continue

            data = {
                "table_name": table_name,
                "table_in_markdown": table_in_markdown,
                "column_name": column_name,
                "current_level_ontology_classes": ", ".join(agent_classes),
            }

            try:
                request, response = await self._call_llm_with_retry_async(data)
                agent_result.llm_request = request
                agent_result.llm_response = response

                if response.answer and response.answer != "-":
                    chosen = parse_class_list(response.answer)
                    valid_votes = [c for c in chosen if c in agent_classes]
                    agent_result.voted_classes = valid_votes
                    for cls in valid_votes:
                        votes_per_class[cls] += 1
                    agent_result.status = "success"
                else:
                    agent_result.status = "success"
                    agent_result.voted_classes = []

            except Exception as e:
                agent_result.status = "failed"
                agent_result.error = str(e)
                failed_agents += 1

            agent_results.append(agent_result)

        # Build vote summaries
        votes_summary: list[VoteSummaryDetail] = []
        selected_classes: list[str] = []

        for class_ in candidates:
            seen_by = agents_that_saw_class[class_]
            if seen_by > 0:
                votes = votes_per_class[class_]
                percentage = votes / seen_by
                is_selected = percentage >= consensus_threshold and votes > 0

                votes_summary.append(
                    VoteSummaryDetail(
                        class_name=class_,
                        vote_count=votes,
                        total_agents=seen_by,
                        percentage=percentage,
                        selected=is_selected,
                    )
                )

                if is_selected:
                    selected_classes.append(class_)

        # Sort by vote count descending
        votes_summary.sort(key=lambda x: x.vote_count, reverse=True)

        edm_result = EDMResultDetail(
            consensus_threshold=consensus_threshold,
            total_agents=len(agents_assignments),
            votes_summary=votes_summary,
            agents=agent_results,
        )

        # Determine status
        status = "completed"
        error = None
        if failed_agents > len(agents_assignments) * 0.5:
            status = "failed"
            error = f"{failed_agents}/{len(agents_assignments)} agents failed"

        return SelectionResult(
            selected=selected_classes,
            status=status,
            error=error,
            edm_result=edm_result,
        )

    def _assign_classes_to_agents(
        self,
        classes: list[str],
        num_agents: int,
        avg_agents_per_class: int,
    ) -> list[list[str]]:
        """Assign classes to agents for EDM."""
        agents_assignments: list[list[str]] = [[] for _ in range(num_agents)]

        for class_ in classes:
            if num_agents < avg_agents_per_class:
                assigned_agents = range(num_agents)
            else:
                assigned_agents = random.sample(range(num_agents), avg_agents_per_class)
            for agent in assigned_agents:
                agents_assignments[agent].append(class_)

        if not agents_assignments:
            agents_assignments = [classes]

        return agents_assignments

    def select(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        candidates: list[str],
    ) -> SelectionResult:
        """Select ontology classes with detailed tracing."""
        if self.mode == "edm":
            return self.select_edm(
                table_name, table_in_markdown, column_name, candidates
            )
        else:
            return self.select_single(
                table_name, table_in_markdown, column_name, candidates
            )

    async def select_async(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        candidates: list[str],
    ) -> SelectionResult:
        """Async version: Select ontology classes with detailed tracing."""
        if self.mode == "edm":
            return await self.select_edm_async(
                table_name, table_in_markdown, column_name, candidates
            )
        else:
            return await self.select_single_async(
                table_name, table_in_markdown, column_name, candidates
            )


# Type for SSE callback (sync and async)
SSECallback = Callable[[str, dict[str, Any]], None]
AsyncSSECallback = Callable[[str, dict[str, Any]], Any]  # Returns coroutine


class RunExecutor:
    """Executor for running semantic annotation tasks."""

    def __init__(
        self,
        config: Config | None = None,
        mode: str = "single",
        prompt_type: str = "cot",
        edm_options: EDMOptions | None = None,
        max_depth: int = 3,
        k: int = 5,
        sse_callback: SSECallback | None = None,
        async_sse_callback: AsyncSSECallback | None = None,
    ) -> None:
        self.config = config or load_config()
        self.mode = mode
        self.prompt_type = prompt_type
        self.edm_options = edm_options
        self.max_depth = max_depth
        self.k = k
        self.sse_callback = sse_callback
        self.async_sse_callback = async_sse_callback

        self.selector = DetailedSelector(
            config=self.config,
            mode=mode,
            prompt_type=prompt_type,
            edm_options=edm_options,
        )

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an SSE event if callback is registered."""
        if self.sse_callback:
            self.sse_callback(event_type, data)

    async def _emit_event_async(self, event_type: str, data: dict[str, Any]) -> None:
        """Async version: Emit an SSE event if callback is registered."""
        if self.async_sse_callback:
            await self.async_sse_callback(event_type, data)

    def execute_column(
        self,
        table_name: str,
        table_markdown: str,
        column_name: str,
        ontology_dag: Any,  # OntologyDAG type
        run_id: str = "",
    ) -> ColumnResultDetail:
        """Execute BFS annotation for a single column."""
        from collections import deque

        steps: list[BFSStepDetail] = []
        final_paths: list[list[str]] = []
        selection_cache: dict[str, SelectionResult] = {}  # parent_url → SelectionResult

        # BFS queue: (level, parent_url, path_so_far)
        queue = deque([(0, ontology_dag.root, [])])

        while queue:
            level, parent_url, current_path = queue.popleft()

            # Get parent name
            parent_node = ontology_dag.nodes.get(parent_url)
            parent_name = parent_node.name if parent_node else parent_url

            # Get children at this level (edges_subclassof = parent → children)
            children_urls = ontology_dag.edges_subclassof.get(parent_url, [])
            if not children_urls or level >= self.max_depth:
                if current_path:
                    final_paths.append(current_path)
                continue

            # Get candidate class names
            candidates = []
            for url in children_urls:
                node = ontology_dag.nodes.get(url)
                if node:
                    candidates.append(node.name)

            if not candidates:
                if current_path:
                    final_paths.append(current_path)
                continue

            # Make selection (with caching)
            if parent_url in selection_cache:
                result = selection_cache[parent_url]
            else:
                result = self.selector.select(
                    table_name=table_name,
                    table_in_markdown=table_markdown,
                    column_name=column_name,
                    candidates=candidates,
                )
                selection_cache[parent_url] = result

            # Build step detail
            step = BFSStepDetail(
                level=level,
                parent=parent_name,
                candidates=candidates,
                selected=result.selected,
                status=result.status,
                error=result.error,
                llm_request=result.llm_request,
                llm_response=result.llm_response,
                edm_result=result.edm_result,
            )
            steps.append(step)

            # Emit step event
            self._emit_event(
                "step",
                {
                    "run_id": run_id,
                    "column_name": column_name,
                    "step": self._step_to_dict(step),
                    "current_path": current_path,
                    "status": "in_progress",
                },
            )

            # Handle selection result
            if result.status == "failed":
                # Terminate this branch but continue others
                final_paths.append(current_path + ["[terminated]"])
                continue

            if not result.selected:
                # No selection, path ends here
                if current_path:
                    final_paths.append(current_path)
                continue

            # Continue BFS for selected classes
            for selected_name in result.selected:
                # Find URL for selected class
                selected_url = None
                for url in children_urls:
                    node = ontology_dag.nodes.get(url)
                    if node and node.name == selected_name:
                        selected_url = url
                        break

                if selected_url:
                    new_path = current_path + [selected_name]
                    queue.append((level + 1, selected_url, new_path))

        # If no paths collected, add empty path
        if not final_paths:
            final_paths = [[]]

        # Determine overall status
        status = "completed"
        error = None
        if all(step.status == "failed" for step in steps):
            status = "failed"
            error = "All steps failed"
        elif any(step.status == "failed" for step in steps):
            status = "partial"

        return ColumnResultDetail(
            column_name=column_name,
            status=status,
            steps=steps,
            final_paths=final_paths,
            error=error,
        )

    async def execute_column_async(
        self,
        table_name: str,
        table_markdown: str,
        column_name: str,
        ontology_dag: Any,  # OntologyDAG type
        run_id: str = "",
    ) -> ColumnResultDetail:
        """Async version: Execute BFS annotation for a single column."""
        from collections import deque

        steps: list[BFSStepDetail] = []
        final_paths: list[list[str]] = []
        selection_cache: dict[str, SelectionResult] = {}  # parent_url → SelectionResult

        # BFS queue: (level, parent_url, path_so_far)
        queue = deque([(0, ontology_dag.root, [])])

        while queue:
            level, parent_url, current_path = queue.popleft()

            # Get parent name
            parent_node = ontology_dag.nodes.get(parent_url)
            parent_name = parent_node.name if parent_node else parent_url

            # Get children at this level (edges_subclassof = parent → children)
            children_urls = ontology_dag.edges_subclassof.get(parent_url, [])
            if not children_urls or level >= self.max_depth:
                if current_path:
                    final_paths.append(current_path)
                continue

            # Get candidate class names
            candidates = []
            for url in children_urls:
                node = ontology_dag.nodes.get(url)
                if node:
                    candidates.append(node.name)

            if not candidates:
                if current_path:
                    final_paths.append(current_path)
                continue

            # Make selection (async, with caching)
            if parent_url in selection_cache:
                result = selection_cache[parent_url]
            else:
                result = await self.selector.select_async(
                    table_name=table_name,
                    table_in_markdown=table_markdown,
                    column_name=column_name,
                    candidates=candidates,
                )
                selection_cache[parent_url] = result

            # Build step detail
            step = BFSStepDetail(
                level=level,
                parent=parent_name,
                candidates=candidates,
                selected=result.selected,
                status=result.status,
                error=result.error,
                llm_request=result.llm_request,
                llm_response=result.llm_response,
                edm_result=result.edm_result,
            )
            steps.append(step)

            # Emit step event (async)
            await self._emit_event_async(
                "step",
                {
                    "run_id": run_id,
                    "column_name": column_name,
                    "step": self._step_to_dict(step),
                    "current_path": current_path,
                    "status": "in_progress",
                },
            )

            # Handle selection result
            if result.status == "failed":
                # Terminate this branch but continue others
                final_paths.append(current_path + ["[terminated]"])
                continue

            if not result.selected:
                # No selection, path ends here
                if current_path:
                    final_paths.append(current_path)
                continue

            # Continue BFS for selected classes
            for selected_name in result.selected:
                # Find URL for selected class
                selected_url = None
                for url in children_urls:
                    node = ontology_dag.nodes.get(url)
                    if node and node.name == selected_name:
                        selected_url = url
                        break

                if selected_url:
                    new_path = current_path + [selected_name]
                    queue.append((level + 1, selected_url, new_path))

        # If no paths collected, add empty path
        if not final_paths:
            final_paths = [[]]

        # Determine overall status
        status = "completed"
        error = None
        if all(step.status == "failed" for step in steps):
            status = "failed"
            error = "All steps failed"
        elif any(step.status == "failed" for step in steps):
            status = "partial"

        return ColumnResultDetail(
            column_name=column_name,
            status=status,
            steps=steps,
            final_paths=final_paths,
            error=error,
        )

    def _step_to_dict(self, step: BFSStepDetail) -> dict[str, Any]:
        """Convert BFSStepDetail to dictionary for SSE."""
        result: dict[str, Any] = {
            "level": step.level,
            "parent": step.parent,
            "candidates": step.candidates,
            "selected": step.selected,
            "status": step.status,
            "error": step.error,
        }

        if step.llm_request:
            result["llm_request"] = {
                "prompt": step.llm_request.prompt,
                "model": step.llm_request.model,
                "timestamp": step.llm_request.timestamp.isoformat(),
            }

        if step.llm_response:
            result["llm_response"] = {
                "raw": step.llm_response.raw,
                "reasoning": step.llm_response.reasoning,
                "answer": step.llm_response.answer,
                "latency_ms": step.llm_response.latency_ms,
                "input_tokens": step.llm_response.input_tokens,
                "output_tokens": step.llm_response.output_tokens,
                "total_tokens": step.llm_response.total_tokens,
            }

        if step.edm_result:
            result["edm_result"] = {
                "consensus_threshold": step.edm_result.consensus_threshold,
                "total_agents": step.edm_result.total_agents,
                "votes_summary": [
                    {
                        "class_name": v.class_name,
                        "vote_count": v.vote_count,
                        "total_agents": v.total_agents,
                        "percentage": v.percentage,
                        "selected": v.selected,
                    }
                    for v in step.edm_result.votes_summary
                ],
                "agents": [
                    {
                        "agent_id": a.agent_id,
                        "assigned_classes": a.assigned_classes,
                        "voted_classes": a.voted_classes,
                        "status": a.status,
                        "error": a.error,
                        "llm_request": (
                            {
                                "prompt": a.llm_request.prompt,
                                "model": a.llm_request.model,
                            }
                            if a.llm_request
                            else None
                        ),
                        "llm_response": (
                            {
                                "raw": a.llm_response.raw,
                                "reasoning": a.llm_response.reasoning,
                                "answer": a.llm_response.answer,
                                "latency_ms": a.llm_response.latency_ms,
                                "input_tokens": a.llm_response.input_tokens,
                                "output_tokens": a.llm_response.output_tokens,
                                "total_tokens": a.llm_response.total_tokens,
                            }
                            if a.llm_response
                            else None
                        ),
                    }
                    for a in step.edm_result.agents
                ],
            }

        return result


__all__ = [
    "RunExecutor",
    "DetailedSelector",
    "SelectionResult",
    "BFSStepDetail",
    "ColumnResultDetail",
    "LLMRequestDetail",
    "LLMResponseDetail",
    "EDMResultDetail",
    "AgentResultDetail",
    "VoteSummaryDetail",
]
