#!/bin/bash
# Run all 8 experiments
# Usage: ./experiments/run.sh [experiment_name]
# If no argument, runs all experiments sequentially

set -e

# Change to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# Activate backend virtual environment
cd backend
source .venv/bin/activate
cd "$PROJECT_ROOT"

run_experiment() {
    local name=$1
    local provider=$2
    local model=$3

    echo "=========================================="
    echo "Running experiment: $name"
    echo "Provider: $provider | Model: $model"
    echo "=========================================="

    saed-run-batch config "experiments/${name}/config.yaml" \
        --provider "$provider" \
        --model "$model" \
        --output-dir "experiments/${name}/"

    echo "Completed: $name"
    echo ""
}

# Experiment definitions
run_ollama_direct_single() {
    run_experiment "ollama_direct_single" "ollama" "gpt-oss:20b"
}

run_ollama_direct_edm() {
    run_experiment "ollama_direct_edm" "ollama" "gpt-oss:20b"
}

run_ollama_cot_single() {
    run_experiment "ollama_cot_single" "ollama" "gpt-oss:20b"
}

run_ollama_cot_edm() {
    run_experiment "ollama_cot_edm" "ollama" "gpt-oss:20b"
}

run_litellm_direct_single() {
    run_experiment "litellm_direct_single" "litellm" "azure-gpt-4.1"
}

run_litellm_direct_edm() {
    run_experiment "litellm_direct_edm" "litellm" "azure-gpt-4.1"
}

run_litellm_cot_single() {
    run_experiment "litellm_cot_single" "litellm" "azure-gpt-4.1"
}

run_litellm_cot_edm() {
    run_experiment "litellm_cot_edm" "litellm" "azure-gpt-4.1"
}

# Main
if [ $# -eq 0 ]; then
    echo "Running all 8 experiments..."
    echo ""

    # Ollama experiments
    run_ollama_direct_single
    run_ollama_direct_edm
    run_ollama_cot_single
    run_ollama_cot_edm

    # LiteLLM experiments
    run_litellm_direct_single
    run_litellm_direct_edm
    run_litellm_cot_single
    run_litellm_cot_edm

    echo "=========================================="
    echo "All experiments completed!"
    echo "=========================================="
else
    # Run specific experiment
    case $1 in
        ollama_direct_single) run_ollama_direct_single ;;
        ollama_direct_edm) run_ollama_direct_edm ;;
        ollama_cot_single) run_ollama_cot_single ;;
        ollama_cot_edm) run_ollama_cot_edm ;;
        litellm_direct_single) run_litellm_direct_single ;;
        litellm_direct_edm) run_litellm_direct_edm ;;
        litellm_cot_single) run_litellm_cot_single ;;
        litellm_cot_edm) run_litellm_cot_edm ;;
        *)
            echo "Unknown experiment: $1"
            echo "Available experiments:"
            echo "  ollama_direct_single"
            echo "  ollama_direct_edm"
            echo "  ollama_cot_single"
            echo "  ollama_cot_edm"
            echo "  litellm_direct_single"
            echo "  litellm_direct_edm"
            echo "  litellm_cot_single"
            echo "  litellm_cot_edm"
            exit 1
            ;;
    esac
fi
