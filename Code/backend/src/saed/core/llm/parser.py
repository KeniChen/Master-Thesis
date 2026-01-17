"""LLM response parsing utilities."""

import re


def extract_answer(response: str) -> str | None:
    """Extract the answer content from an LLM response.

    Looks for content within <answer>...</answer> tags.

    Args:
        response: The raw LLM response string.

    Returns:
        The extracted answer content, or None if no answer tags found.
    """
    pattern = r"<answer>(.*?)</answer>"
    matches = re.findall(pattern, response, flags=re.DOTALL)
    if matches:
        return matches[0].strip()
    return None


def extract_reasoning(response: str) -> str | None:
    """Extract the reasoning content from a Chain-of-Thought LLM response.

    Looks for content within <reasoning>...</reasoning> tags.

    Args:
        response: The raw LLM response string.

    Returns:
        The extracted reasoning content, or None if no reasoning tags found.
    """
    pattern = r"<reasoning>(.*?)</reasoning>"
    matches = re.findall(pattern, response, flags=re.DOTALL)
    if matches:
        return matches[0].strip()
    return None


def parse_class_list(answer: str) -> list[str]:
    """Parse a comma-separated list of class names from an answer.

    Args:
        answer: A comma-separated string of class names.

    Returns:
        A list of stripped class name strings.
    """
    if not answer or answer == "-":
        return []
    return [cls.strip() for cls in answer.split(",")]
