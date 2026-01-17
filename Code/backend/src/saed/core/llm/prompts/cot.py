"""Chain-of-thought prompts for ontology class selection."""

from saed.core.llm.prompts.base import COT_OUTPUT_INSTRUCTION, build_prompt

cot_prompt = build_prompt(
    class_description="the set of the ontology classes available at this level",
    output_instruction=COT_OUTPUT_INSTRUCTION,
)

edm_cot_prompt = build_prompt(
    class_description="a subset of the ontology classes available at this level",
    output_instruction=COT_OUTPUT_INSTRUCTION,
)

__all__ = ["cot_prompt", "edm_cot_prompt"]
