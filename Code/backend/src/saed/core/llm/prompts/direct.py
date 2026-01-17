"""Direct prompts for ontology class selection."""

from saed.core.llm.prompts.base import DEFAULT_OUTPUT_INSTRUCTION, build_prompt

# Standard single-shot prompt (full class set)
direct_prompt = build_prompt(
    class_description="the set of the ontology classes available at this level",
    output_instruction=DEFAULT_OUTPUT_INSTRUCTION,
)

# Ensemble prompt (subset of classes)
edm_prompt = build_prompt(
    class_description="a subset of the ontology classes available at this level",
    output_instruction=DEFAULT_OUTPUT_INSTRUCTION,
)

__all__ = ["direct_prompt", "edm_prompt"]
