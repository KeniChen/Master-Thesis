"""Data transformation utilities."""

import pandas as pd


def dataframe_to_markdown(df: pd.DataFrame, k: int = 5) -> str:
    """Convert a DataFrame to Markdown table format.

    LLMs cannot directly read Excel files or binary data. This function
    serializes table data into Markdown format that LLMs can understand.

    Args:
        df: The DataFrame to convert.
        k: Number of rows to include (default: 5).

    Returns:
        A Markdown-formatted string representation of the table.
    """
    subset = df.head(k)
    headers = "| " + " | ".join(subset.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(subset.columns)) + " |"

    rows = []
    for _, row in subset.iterrows():
        row_str = "| " + " | ".join(map(str, row.values)) + " |"
        rows.append(row_str)

    md_table = headers + "\n" + sep + "\n" + "\n".join(rows)
    return md_table
