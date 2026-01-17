"""Shared prompt building blocks for LLM calls."""

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_MESSAGE = (
    "You are a knowledgeable assistant who helps map tabular data columns to "
    "ontology classes. You have expert knowledge in semantic table annotation, "
    "i.e., table column-to-ontology class mappings. Your goal is to determine "
    "the most semantically appropriate ontology class (or set of classes) for "
    "a given column, based on the provided table name, table header, example "
    "data, column name, and the ontology classes at current level."
)

HUMAN_MESSAGE_TEMPLATE = """
We have a table named '{table_name}' which has several columns. Below is the table in Markdown format, including column headers and a few example rows:

{table_in_markdown}

We are currently focusing on ontology classes at the given level. Below are {class_description}:
{current_level_ontology_classes}

We want to determine the best fitting ontology class (or class path if multiple levels are considered) for the following column: '{column_name}'.

Instructions:
1. Review the column name and the example data.
2. Based on the ontology classes provided, select the most suitable ontology class or classes (or ancestor class or classes) of the corresponding class that best describe the semantic meaning of this column.
3. {output_instruction}
Note: The provided set of ontology classes might not be complete. If you think none of the given classes are suitable, you can indicate that accordingly.
"""

DEFAULT_OUTPUT_INSTRUCTION = (
    "Output the final answer enclosed in <answer></answer> tags, \n"
    "    3.1 If multiple ontology classes are required to describe the column, "
    "split the classes with a comma, for example, "
    "<answer>ontology_class1, ontology_class2, ..., ontology_classN</answer>\n"
    "    3.2 If no suitable class is found, respond with <answer>-</answer>."
)

COT_OUTPUT_INSTRUCTION = (
    "First, output your reasoning enclosed in <reasoning></reasoning> tags. "
    "Then output the final answer enclosed in <answer></answer> tags, \n"
    "    3.1 If multiple ontology classes are required to describe the column, "
    "split the classes with a comma, for example, "
    "<answer>ontology_class1, ontology_class2, ..., ontology_classN</answer>\n"
    "    3.2 If no suitable class is found, respond with <answer>-</answer>."
)


def build_prompt(class_description: str, output_instruction: str) -> ChatPromptTemplate:
    """Create a prompt template with provided descriptions and instructions."""
    human_message = HUMAN_MESSAGE_TEMPLATE.format(
        table_name="{table_name}",
        table_in_markdown="{table_in_markdown}",
        class_description=class_description,
        current_level_ontology_classes="{current_level_ontology_classes}",
        column_name="{column_name}",
        output_instruction=output_instruction,
    )
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_MESSAGE),
        ("human", human_message),
    ])


__all__ = [
    "COT_OUTPUT_INSTRUCTION",
    "DEFAULT_OUTPUT_INSTRUCTION",
    "HUMAN_MESSAGE_TEMPLATE",
    "SYSTEM_MESSAGE",
    "build_prompt",
]
