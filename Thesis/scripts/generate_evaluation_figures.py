#!/usr/bin/env python3
"""Generate evaluation figures and summary for thesis."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import numpy as np

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
FIGURES_DIR = Path("/Users/mou/Projects/Keni_MA_Thesis/graphics/figures")

# Experiment configurations
EXPERIMENTS = {
    "litellm_direct_single": {"provider": "Azure GPT-4.1", "prompt": "Direct", "mode": "Single"},
    "litellm_direct_edm": {"provider": "Azure GPT-4.1", "prompt": "Direct", "mode": "EDM"},
    "litellm_cot_single": {"provider": "Azure GPT-4.1", "prompt": "CoT", "mode": "Single"},
    "litellm_cot_edm": {"provider": "Azure GPT-4.1", "prompt": "CoT", "mode": "EDM"},
    "ollama_direct_single": {"provider": "Ollama (GPT-OSS:20b)", "prompt": "Direct", "mode": "Single"},
    "ollama_direct_edm": {"provider": "Ollama (GPT-OSS:20b)", "prompt": "Direct", "mode": "EDM"},
    "ollama_cot_single": {"provider": "Ollama (GPT-OSS:20b)", "prompt": "CoT", "mode": "Single"},
    "ollama_cot_edm": {"provider": "Ollama (GPT-OSS:20b)", "prompt": "CoT", "mode": "EDM"},
}

def load_metrics():
    """Load all metrics files."""
    results = {}
    for exp_name, config in EXPERIMENTS.items():
        exp_dir = EXPERIMENTS_DIR / exp_name
        metrics_files = list(exp_dir.glob("*_metrics.json"))
        if metrics_files:
            with open(metrics_files[0]) as f:
                data = json.load(f)
                total_tokens = data["performance"].get("total_tokens", 0)
                results[exp_name] = {
                    **config,
                    "path_f1_micro": data["metrics"]["path_level"]["micro_f1"] * 100,
                    "path_f1_macro": data["metrics"]["path_level"]["macro_f1"] * 100,
                    "node_f1_micro": data["metrics"]["node_level"]["micro_f1"] * 100,
                    "node_f1_macro": data["metrics"]["node_level"]["macro_f1"] * 100,
                    "runtime_s": data["performance"]["total_time_ms"] / 1000,
                    "runtime_min": data["performance"]["total_time_ms"] / 1000 / 60,
                    "total_tokens": total_tokens,
                    "tokens_k": total_tokens / 1000,
                    "tokens_m": total_tokens / 1000000,
                }
    return results


def load_per_level_metrics():
    """Load evaluation files and compute per-level accuracy."""
    results = {}
    for exp_name, config in EXPERIMENTS.items():
        exp_dir = EXPERIMENTS_DIR / exp_name
        eval_files = list(exp_dir.glob("*_eval.json"))
        if eval_files:
            with open(eval_files[0]) as f:
                data = json.load(f)

            # Compute Level 1 accuracy
            level1_correct = 0
            level1_total = 0
            for col in data["columns"]:
                pred_level1 = set(p[0] for p in col["pred_paths"] if p)
                gt_level1 = set(p[0] for p in col["gt_paths"] if p)
                if pred_level1 & gt_level1:  # intersection not empty
                    level1_correct += 1
                level1_total += 1

            results[exp_name] = {
                **config,
                "level1_accuracy": level1_correct / level1_total * 100 if level1_total > 0 else 0,
                "level1_correct": level1_correct,
                "level1_total": level1_total,
            }
    return results

def generate_main_results_chart(results):
    """Generate main results comparison chart."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Prepare data - sort by provider then by prompt/mode
    litellm_exps = [k for k in results.keys() if k.startswith("litellm")]
    ollama_exps = [k for k in results.keys() if k.startswith("ollama")]
    exp_order = litellm_exps + ollama_exps

    labels = []
    for exp in exp_order:
        r = results[exp]
        labels.append(f"{r['prompt']}+{r['mode']}")

    x = np.arange(len(exp_order))
    width = 0.35

    path_f1 = [results[e]["path_f1_micro"] for e in exp_order]
    node_f1 = [results[e]["node_f1_micro"] for e in exp_order]

    bars1 = ax.bar(x - width/2, path_f1, width, label='Path F1 (Micro)', color='#2E86AB')
    bars2 = ax.bar(x + width/2, node_f1, width, label='Node F1 (Micro)', color='#A23B72')

    ax.set_ylabel('F1 Score (%)', fontsize=14)
    ax.set_xlabel('Configuration', fontsize=14)
    ax.set_title('Semantic Annotation Performance: Azure GPT-4.1 vs Ollama (GPT-OSS:20b)', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=12)
    ax.legend(loc='upper right', fontsize=12)
    ax.set_ylim(0, 60)
    ax.tick_params(axis='y', labelsize=12)

    # Add divider between providers
    ax.axvline(x=3.5, color='gray', linestyle='--', alpha=0.5)
    ax.text(1.5, 55, 'Azure GPT-4.1', ha='center', fontsize=13, fontweight='bold')
    ax.text(5.5, 55, 'Ollama (GPT-OSS:20b)', ha='center', fontsize=13, fontweight='bold')

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "results_comparison.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'results_comparison.pdf'}")

def generate_pareto_chart(results):
    """Generate cost-accuracy Pareto chart."""
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = {'Azure GPT-4.1': '#2E86AB', 'Ollama (GPT-OSS:20b)': '#E94F37'}
    markers = {'Single': 'o', 'EDM': 's'}

    for exp_name, r in results.items():
        runtime = r["runtime_min"]
        f1 = r["path_f1_micro"]
        color = colors[r["provider"]]
        marker = markers[r["mode"]]

        ax.scatter(runtime, f1, c=color, marker=marker, s=150, alpha=0.8,
                  edgecolors='black', linewidth=1)

        # Add label
        offset = (5, 5) if r["mode"] == "Single" else (5, -15)
        ax.annotate(f"{r['prompt']}+{r['mode']}", (runtime, f1),
                   xytext=offset, textcoords='offset points', fontsize=10)

    ax.set_xlabel('Runtime (minutes)', fontsize=14)
    ax.set_ylabel('Path F1 Score (Micro, %)', fontsize=14)
    ax.set_title('Cost-Accuracy Trade-off Analysis', fontsize=16)
    ax.set_xscale('log')
    ax.tick_params(axis='both', labelsize=12)

    # Custom legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#2E86AB', markersize=12, label='Azure GPT-4.1'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#E94F37', markersize=12, label='Ollama (GPT-OSS:20b)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=12, label='Single'),
        Line2D([0], [0], marker='s', color='w', markerfacecolor='gray', markersize=12, label='EDM'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=12)

    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cost_accuracy_pareto.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'cost_accuracy_pareto.pdf'}")

def generate_cot_effect_chart(results):
    """Generate CoT effect comparison chart."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Azure GPT-4.1
    ax1 = axes[0]
    modes = ['Single', 'EDM']
    direct_f1 = [results["litellm_direct_single"]["path_f1_micro"],
                 results["litellm_direct_edm"]["path_f1_micro"]]
    cot_f1 = [results["litellm_cot_single"]["path_f1_micro"],
              results["litellm_cot_edm"]["path_f1_micro"]]

    x = np.arange(len(modes))
    width = 0.35

    ax1.bar(x - width/2, direct_f1, width, label='Direct', color='#95C8D8')
    ax1.bar(x + width/2, cot_f1, width, label='CoT', color='#2E86AB')
    ax1.set_ylabel('Path F1 (Micro, %)', fontsize=12)
    ax1.set_title('Azure GPT-4.1', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(modes, fontsize=11)
    ax1.tick_params(axis='y', labelsize=11)
    ax1.legend(fontsize=11)
    ax1.set_ylim(0, 50)

    # Ollama (GPT-OSS:20b)
    ax2 = axes[1]
    direct_f1 = [results["ollama_direct_single"]["path_f1_micro"],
                 results["ollama_direct_edm"]["path_f1_micro"]]
    cot_f1 = [results["ollama_cot_single"]["path_f1_micro"],
              results["ollama_cot_edm"]["path_f1_micro"]]

    ax2.bar(x - width/2, direct_f1, width, label='Direct', color='#F7B2B2')
    ax2.bar(x + width/2, cot_f1, width, label='CoT', color='#E94F37')
    ax2.set_ylabel('Path F1 (Micro, %)', fontsize=12)
    ax2.set_title('Ollama (GPT-OSS:20b)', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(modes, fontsize=11)
    ax2.tick_params(axis='y', labelsize=11)
    ax2.legend(fontsize=11)
    ax2.set_ylim(0, 50)

    fig.suptitle('Effect of Chain-of-Thought (CoT) Prompting', fontsize=16)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "cot_effect.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'cot_effect.pdf'}")

def generate_token_usage_chart(results):
    """Generate token usage bar chart for Azure experiments."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Only litellm experiments have token data
    litellm_order = ["litellm_direct_single", "litellm_direct_edm",
                     "litellm_cot_single", "litellm_cot_edm"]
    labels = ["Direct+Single", "Direct+EDM", "CoT+Single", "CoT+EDM"]

    tokens_m = [results[e]["tokens_m"] for e in litellm_order]
    x = np.arange(len(labels))

    bars = ax.bar(x, tokens_m, color=['#95C8D8', '#2E86AB', '#95C8D8', '#2E86AB'],
                  edgecolor='black', linewidth=1)

    ax.set_ylabel('Token Usage (Millions)', fontsize=14)
    ax.set_xlabel('Configuration', fontsize=14)
    ax.set_title('Azure GPT-4.1 Token Usage by Configuration', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.tick_params(axis='y', labelsize=12)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}M',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3), textcoords="offset points",
                   ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_ylim(0, max(tokens_m) * 1.15)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "token_usage.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'token_usage.pdf'}")


def generate_token_efficiency_chart(results):
    """Generate F1 per million tokens efficiency chart."""
    fig, ax = plt.subplots(figsize=(10, 6))

    litellm_order = ["litellm_direct_single", "litellm_direct_edm",
                     "litellm_cot_single", "litellm_cot_edm"]
    labels = ["Direct+Single", "Direct+EDM", "CoT+Single", "CoT+EDM"]

    # F1 per million tokens
    efficiency = []
    for e in litellm_order:
        f1 = results[e]["path_f1_micro"]
        tokens_m = results[e]["tokens_m"]
        efficiency.append(f1 / tokens_m if tokens_m > 0 else 0)

    x = np.arange(len(labels))
    bars = ax.bar(x, efficiency, color=['#95C8D8', '#2E86AB', '#95C8D8', '#2E86AB'],
                  edgecolor='black', linewidth=1)

    ax.set_ylabel('Path F1 (%) per Million Tokens', fontsize=14)
    ax.set_xlabel('Configuration', fontsize=14)
    ax.set_title('Token Efficiency: Azure GPT-4.1', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.tick_params(axis='y', labelsize=12)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3), textcoords="offset points",
                   ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.set_ylim(0, max(efficiency) * 1.15)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "token_efficiency.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'token_efficiency.pdf'}")


def generate_level1_accuracy_chart(level_results):
    """Generate Level 1 accuracy comparison chart (EDM vs Single)."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Azure GPT-4.1
    ax1 = axes[0]
    prompts = ['Direct', 'CoT']
    single_acc = [level_results["litellm_direct_single"]["level1_accuracy"],
                  level_results["litellm_cot_single"]["level1_accuracy"]]
    edm_acc = [level_results["litellm_direct_edm"]["level1_accuracy"],
               level_results["litellm_cot_edm"]["level1_accuracy"]]

    x = np.arange(len(prompts))
    width = 0.35

    bars1 = ax1.bar(x - width/2, single_acc, width, label='Single', color='#95C8D8')
    bars2 = ax1.bar(x + width/2, edm_acc, width, label='EDM', color='#2E86AB')
    ax1.set_ylabel('Level 1 Accuracy (%)', fontsize=12)
    ax1.set_title('Azure GPT-4.1', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(prompts, fontsize=11)
    ax1.tick_params(axis='y', labelsize=11)
    ax1.legend(fontsize=11)
    ax1.set_ylim(0, 100)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)

    # Ollama (GPT-OSS:20b)
    ax2 = axes[1]
    single_acc = [level_results["ollama_direct_single"]["level1_accuracy"],
                  level_results["ollama_cot_single"]["level1_accuracy"]]
    edm_acc = [level_results["ollama_direct_edm"]["level1_accuracy"],
               level_results["ollama_cot_edm"]["level1_accuracy"]]

    bars1 = ax2.bar(x - width/2, single_acc, width, label='Single', color='#F7B2B2')
    bars2 = ax2.bar(x + width/2, edm_acc, width, label='EDM', color='#E94F37')
    ax2.set_ylabel('Level 1 Accuracy (%)', fontsize=12)
    ax2.set_title('Ollama (GPT-OSS:20b)', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(prompts, fontsize=11)
    ax2.tick_params(axis='y', labelsize=11)
    ax2.legend(fontsize=11)
    ax2.set_ylim(0, 100)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(f'{height:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)

    fig.suptitle('Level 1 (First Hierarchy Level) Accuracy: EDM vs Single', fontsize=16)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "level1_accuracy.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'level1_accuracy.pdf'}")


def generate_edm_effect_chart(results):
    """Generate EDM effect comparison chart."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Azure GPT-4.1
    ax1 = axes[0]
    prompts = ['Direct', 'CoT']
    single_f1 = [results["litellm_direct_single"]["path_f1_micro"],
                 results["litellm_cot_single"]["path_f1_micro"]]
    edm_f1 = [results["litellm_direct_edm"]["path_f1_micro"],
              results["litellm_cot_edm"]["path_f1_micro"]]

    x = np.arange(len(prompts))
    width = 0.35

    ax1.bar(x - width/2, single_f1, width, label='Single', color='#95C8D8')
    ax1.bar(x + width/2, edm_f1, width, label='EDM', color='#2E86AB')
    ax1.set_ylabel('Path F1 (Micro, %)', fontsize=12)
    ax1.set_title('Azure GPT-4.1', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(prompts, fontsize=11)
    ax1.tick_params(axis='y', labelsize=11)
    ax1.legend(fontsize=11)
    ax1.set_ylim(0, 50)

    # Ollama (GPT-OSS:20b)
    ax2 = axes[1]
    single_f1 = [results["ollama_direct_single"]["path_f1_micro"],
                 results["ollama_cot_single"]["path_f1_micro"]]
    edm_f1 = [results["ollama_direct_edm"]["path_f1_micro"],
              results["ollama_cot_edm"]["path_f1_micro"]]

    ax2.bar(x - width/2, single_f1, width, label='Single', color='#F7B2B2')
    ax2.bar(x + width/2, edm_f1, width, label='EDM', color='#E94F37')
    ax2.set_ylabel('Path F1 (Micro, %)', fontsize=12)
    ax2.set_title('Ollama (GPT-OSS:20b)', fontsize=14)
    ax2.set_xticks(x)
    ax2.set_xticklabels(prompts, fontsize=11)
    ax2.tick_params(axis='y', labelsize=11)
    ax2.legend(fontsize=11)
    ax2.set_ylim(0, 50)

    fig.suptitle('Effect of Ensemble Decision Making (EDM)', fontsize=16)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "edm_effect.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {FIGURES_DIR / 'edm_effect.pdf'}")

def print_results_table(results, level_results=None):
    """Print results table for LaTeX."""
    print("\n" + "="*100)
    print("RESULTS SUMMARY TABLE")
    print("="*100)

    # Sort: litellm first, then ollama
    order = [
        "litellm_direct_single", "litellm_direct_edm",
        "litellm_cot_single", "litellm_cot_edm",
        "ollama_direct_single", "ollama_direct_edm",
        "ollama_cot_single", "ollama_cot_edm"
    ]

    print(f"{'Configuration':<25} {'Path F1':<15} {'Node F1':<15} {'Runtime':<10} {'Tokens':<12} {'L1 Acc':<10}")
    print(f"{'':<25} {'(Micro)':<15} {'(Micro)':<15} {'(min)':<10} {'(K)':<12} {'(%)':<10}")
    print("-"*97)

    for exp_name in order:
        if exp_name not in results:
            continue
        r = results[exp_name]
        config = f"{r['provider'][:10]} {r['prompt']}+{r['mode']}"
        tokens_str = f"{r['tokens_k']:.0f}" if r['total_tokens'] > 0 else "-"
        level1_str = f"{level_results[exp_name]['level1_accuracy']:.1f}" if level_results and exp_name in level_results else "-"
        print(f"{config:<25} {r['path_f1_micro']:>6.2f}        {r['node_f1_micro']:>6.2f}        "
              f"{r['runtime_min']:>6.1f}    {tokens_str:>8}     {level1_str:>6}")

    print("\n" + "="*100)
    print("KEY FINDINGS:")
    print("="*100)

    # Find best configurations
    best_path_f1 = max(results.values(), key=lambda x: x["path_f1_micro"])
    fastest = min(results.values(), key=lambda x: x["runtime_min"])

    print(f"Best Path F1 (Micro): {best_path_f1['provider']} {best_path_f1['prompt']}+{best_path_f1['mode']} "
          f"= {best_path_f1['path_f1_micro']:.2f}%")
    print(f"Fastest: {fastest['provider']} {fastest['prompt']}+{fastest['mode']} "
          f"= {fastest['runtime_min']:.1f} min")

    # Token usage summary for litellm
    litellm_results = {k: v for k, v in results.items() if k.startswith("litellm")}
    if litellm_results:
        total_tokens = sum(r["total_tokens"] for r in litellm_results.values())
        print(f"\nAzure GPT-4.1 Total Token Usage: {total_tokens:,} ({total_tokens/1000000:.2f}M)")

        most_efficient = max(litellm_results.items(),
                            key=lambda x: x[1]["path_f1_micro"] / x[1]["tokens_m"] if x[1]["tokens_m"] > 0 else 0)
        eff = most_efficient[1]["path_f1_micro"] / most_efficient[1]["tokens_m"]
        print(f"Most Token-Efficient: {most_efficient[1]['prompt']}+{most_efficient[1]['mode']} "
              f"= {eff:.1f} F1%/M tokens")

def main():
    print("Loading metrics...")
    results = load_metrics()
    print(f"Loaded {len(results)} experiments")

    print("Loading per-level metrics...")
    level_results = load_per_level_metrics()
    print(f"Loaded {len(level_results)} level metrics")

    print("\nGenerating figures...")
    generate_main_results_chart(results)
    generate_pareto_chart(results)
    generate_cot_effect_chart(results)
    generate_edm_effect_chart(results)
    generate_token_usage_chart(results)
    generate_token_efficiency_chart(results)
    generate_level1_accuracy_chart(level_results)

    print_results_table(results, level_results)

    print("\nDone!")

if __name__ == "__main__":
    main()
