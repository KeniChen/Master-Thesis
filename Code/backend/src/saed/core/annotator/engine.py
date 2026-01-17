"""BFS annotator for ontology traversal."""

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saed.core.ontology.dag import OntologyDAG
    from saed.core.selector import DecisionMaker


def bfs_search(
    table_name: str,
    table_in_markdown: str,
    column_name: str,
    ontology_dag: "OntologyDAG",
    decision_maker: "DecisionMaker",
    max_depth: int,
) -> list[list[str]]:
    """Perform BFS search through the ontology DAG to find matching classes.

    This function traverses the ontology hierarchy using breadth-first search,
    using the decision maker to select appropriate classes at each level.

    Args:
        table_name: Name of the table being annotated.
        table_in_markdown: Table data in markdown format for LLM processing.
        column_name: Name of the column to annotate.
        ontology_dag: The ontology DAG to search through.
        decision_maker: The decision maker to use for class selection.
        max_depth: Maximum depth to search in the ontology hierarchy.

    Returns:
        A list of paths, where each path is a list of ontology class URLs.
    """
    queue: deque[tuple[int, str, list[str]]] = deque()
    queue.append((0, ontology_dag.root, []))
    possible_paths: list[list[str]] = []

    while queue:
        # Get current position: level, parent class, and path so far
        level, parent_level_ontology_class, search_path = queue.popleft()

        # Check termination conditions
        if level >= max_depth:
            possible_paths.append(search_path)
            continue

        if len(ontology_dag.edges[parent_level_ontology_class]) == 0:
            possible_paths.append(search_path)
            continue

        # Get current level ontology classes
        current_level_ontology_classes = [
            ontology_dag.nodes[o].name
            for o in ontology_dag.edges[parent_level_ontology_class]
        ]
        current_level_ontology_classes_url_dict = {
            ontology_dag.nodes[o].name: o
            for o in ontology_dag.edges[parent_level_ontology_class]
        }

        # Call decision maker
        result = decision_maker.select(
            table_name, table_in_markdown, column_name, current_level_ontology_classes
        )

        if result == "-" or result is None:
            print("\tNone")
            possible_paths.append(search_path)
            continue

        # Process selected classes and continue search
        selected_ontology_classes = result.split(", ")
        for selected_ontology_class in selected_ontology_classes:
            if selected_ontology_class in current_level_ontology_classes:
                print(f"\t{selected_ontology_class}")
                new_url = current_level_ontology_classes_url_dict[selected_ontology_class]
                queue.append((
                    level + 1,
                    new_url,
                    search_path + [new_url],
                ))
            else:
                print(f"Error: {selected_ontology_class} is not in current level ontology classes.")

    return possible_paths
