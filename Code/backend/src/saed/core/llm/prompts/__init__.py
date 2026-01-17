"""Prompt templates for LLM calls."""

from saed.core.llm.prompts.cot import cot_prompt, edm_cot_prompt
from saed.core.llm.prompts.direct import direct_prompt, edm_prompt

__all__ = [
    "cot_prompt",
    "direct_prompt",
    "edm_cot_prompt",
    "edm_prompt",
]
