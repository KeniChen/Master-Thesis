"""Selector implementations for ontology class decisions."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Protocol

from saed.core.config.settings import Config, EDMOptions, load_config
from saed.core.llm import LLM
from saed.core.llm.parser import extract_answer, parse_class_list


class Selector(Protocol):
    """Selector interface for choosing ontology classes."""

    def select(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        current_level_ontology_classes: list[str],
    ) -> str:
        ...


class BaseSelector:
    """Base selector with shared LLM wiring."""

    def __init__(
        self,
        config: Config | None = None,
        mode: str = "single",
        prompt_type: str = "cot",
        llm_client: LLM | None = None,
    ) -> None:
        self.config = config or load_config()
        self.mode = mode
        self.prompt_type = prompt_type
        self.llm = llm_client or LLM(
            config=self.config,
            mode=mode,
            prompt_type=prompt_type,
        )


class SingleSelector(BaseSelector):
    """Single-shot selector using one LLM call."""

    def __init__(
        self,
        config: Config | None = None,
        prompt_type: str = "cot",
        llm_client: LLM | None = None,
    ) -> None:
        super().__init__(config=config, mode="single", prompt_type=prompt_type, llm_client=llm_client)

    def select(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        current_level_ontology_classes: list[str],
    ) -> str:
        data = {
            "table_name": table_name,
            "table_in_markdown": table_in_markdown,
            "column_name": column_name,
            "current_level_ontology_classes": ", ".join(current_level_ontology_classes),
        }
        result = self.llm.generate(data)
        answer = extract_answer(result)

        if answer is None or answer == "-":
            return "-"

        predicted_classes = parse_class_list(answer)
        selected_classes = [
            cls for cls in predicted_classes
            if cls in current_level_ontology_classes
        ]

        if selected_classes:
            return ", ".join(selected_classes)
        return "-"


class EnsembleSelector(BaseSelector):
    """Ensemble decision-making selector using multiple LLM votes."""

    def __init__(
        self,
        config: Config | None = None,
        prompt_type: str = "cot",
        edm_options: EDMOptions | None = None,
        llm_client: LLM | None = None,
    ) -> None:
        config = config or load_config()
        super().__init__(config=config, mode="edm", prompt_type=prompt_type, llm_client=llm_client)
        self.edm_options = edm_options or config.defaults.edm_options

    def select(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        current_level_ontology_classes: list[str],
    ) -> str:
        classes = current_level_ontology_classes
        if not classes:
            return "-"

        avg_classes_per_agent = self.edm_options.classes_per_agent
        avg_agents_per_class = self.edm_options.agents_per_class
        consensus_threshold_ratio = self.edm_options.consensus_threshold

        num_classes = len(classes)
        num_agents = max(
            avg_agents_per_class,
            (num_classes * avg_agents_per_class) // avg_classes_per_agent + 1,
        )

        agents_assignments = self._assign_classes_to_agents(
            classes, num_agents, avg_agents_per_class
        )

        agents_that_saw_class = defaultdict(int)
        for class_ in classes:
            agents_that_saw_class[class_] = sum(
                1 for agent_c in agents_assignments if class_ in agent_c
            )

        votes_per_class = self._collect_votes(
            agents_assignments, table_name, table_in_markdown, column_name
        )

        selected_classes = []
        for class_ in classes:
            if agents_that_saw_class[class_] > 0:
                ratio = votes_per_class[class_] / agents_that_saw_class[class_]
                if ratio >= consensus_threshold_ratio and votes_per_class[class_] > 0:
                    selected_classes.append(class_)

        if not selected_classes:
            return "-"
        return ", ".join(selected_classes)

    def _assign_classes_to_agents(
        self,
        classes: list[str],
        num_agents: int,
        avg_agents_per_class: int,
    ) -> list[list[str]]:
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

    def _collect_votes(
        self,
        agents_assignments: list[list[str]],
        table_name: str,
        table_in_markdown: str,
        column_name: str,
    ) -> dict[str, int]:
        votes_per_class: dict[str, int] = defaultdict(int)

        for agent_classes in agents_assignments:
            assigned_classes_str = ", ".join(agent_classes)
            data = {
                "table_name": table_name,
                "table_in_markdown": table_in_markdown,
                "column_name": column_name,
                "current_level_ontology_classes": assigned_classes_str,
            }
            result = self.llm.generate(data)
            answer = extract_answer(result)

            if answer and answer != "-":
                chosen_classes = parse_class_list(answer)
                for cc in chosen_classes:
                    if cc in agent_classes:
                        votes_per_class[cc] += 1

        return votes_per_class


class DecisionMaker:
    """Backward-compatible wrapper that delegates to selector implementations."""

    def __init__(
        self,
        config: Config | None = None,
        mode: str = "single",
        prompt_type: str = "cot",
        edm_options: EDMOptions | None = None,
    ) -> None:
        self.mode = mode
        self.selector: Selector
        if mode == "single":
            self.selector = SingleSelector(config=config, prompt_type=prompt_type)
        elif mode == "edm":
            self.selector = EnsembleSelector(
                config=config,
                prompt_type=prompt_type,
                edm_options=edm_options,
            )
        else:
            raise ValueError(f"Unsupported mode: {mode}")

    def select(
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        current_level_ontology_classes: list[str],
    ) -> str:
        return self.selector.select(
            table_name=table_name,
            table_in_markdown=table_in_markdown,
            column_name=column_name,
            current_level_ontology_classes=current_level_ontology_classes,
        )

    def decision_making(  # pragma: no cover - compatibility alias
        self,
        table_name: str,
        table_in_markdown: str,
        column_name: str,
        current_level_ontology_classes: list[str],
    ) -> str:
        return self.select(
            table_name=table_name,
            table_in_markdown=table_in_markdown,
            column_name=column_name,
            current_level_ontology_classes=current_level_ontology_classes,
        )


__all__ = [
    "BaseSelector",
    "DecisionMaker",
    "EnsembleSelector",
    "Selector",
    "SingleSelector",
]
