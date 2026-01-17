"""Evaluation metrics for semantic annotation."""

from typing import Any


def flatten_list_to_set(paths: list[list[Any]]) -> set:
    """Flatten a list of paths into a set of unique nodes.

    Args:
        paths: A list of paths, where each path is a list of nodes.

    Returns:
        A set containing all unique nodes from all paths.

    Examples:
        >>> flatten_list_to_set([['A', 'B'], ['A', 'C']])
        {'A', 'B', 'C'}
    """
    all_nodes = []
    for p in paths:
        all_nodes.extend(p)
    return set(all_nodes)


def path_level_f1_precision_recall(
    data: list[dict],
) -> tuple[float, float, float, float, float, float]:
    """Calculate micro and macro precision, recall, and F1 at path level.

    Args:
        data: List of dicts with 'gt_paths' and 'pred_paths' keys.

    Returns:
        Tuple of (macro_precision, macro_recall, macro_f1,
                  micro_precision, micro_recall, micro_f1)
    """
    precisions = []
    recalls = []
    f1s = []
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for row in data:
        gt_set = {tuple(p) for p in row["gt_paths"]}
        pred_set = {tuple(p) for p in row["pred_paths"]}

        tp = len(pred_set.intersection(gt_set))
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    macro_precision = sum(precisions) / len(precisions) if precisions else 0.0
    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0

    micro_precision = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    )
    micro_recall = (
        total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    )
    micro_f1 = (
        2 * (micro_precision * micro_recall) / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0
        else 0.0
    )

    return macro_precision, macro_recall, macro_f1, micro_precision, micro_recall, micro_f1


def node_level_f1_precision_recall(
    data: list[dict],
) -> tuple[float, float, float, float, float, float]:
    """Calculate micro and macro precision, recall, and F1 at node level.

    Args:
        data: List of dicts with 'gt_paths' and 'pred_paths' keys.

    Returns:
        Tuple of (macro_precision, macro_recall, macro_f1,
                  micro_precision, micro_recall, micro_f1)
    """
    precisions = []
    recalls = []
    f1s = []
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for row in data:
        gt_set = flatten_list_to_set(row["gt_paths"])
        pred_set = flatten_list_to_set(row["pred_paths"])

        tp = len(pred_set.intersection(gt_set))
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    macro_precision = sum(precisions) / len(precisions) if precisions else 0.0
    macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0

    micro_precision = (
        total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    )
    micro_recall = (
        total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    )
    micro_f1 = (
        2 * (micro_precision * micro_recall) / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0
        else 0.0
    )

    return macro_precision, macro_recall, macro_f1, micro_precision, micro_recall, micro_f1
