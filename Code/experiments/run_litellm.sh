#!/bin/bash
# Run LiteLLM experiments
# Usage: ./experiments/run_litellm.sh [experiment_name]
# If no argument, runs all litellm experiments sequentially

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
    echo "Running all LiteLLM experiments..."
    echo ""

    run_litellm_direct_single
    run_litellm_direct_edm
    run_litellm_cot_single
    run_litellm_cot_edm

    echo "=========================================="
    echo "All LiteLLM experiments completed!"
    echo "=========================================="
else
    # Run specific experiment
    case $1 in
        litellm_direct_single) run_litellm_direct_single ;;
        litellm_direct_edm) run_litellm_direct_edm ;;
        litellm_cot_single) run_litellm_cot_single ;;
        litellm_cot_edm) run_litellm_cot_edm ;;
        *)
            echo "Unknown experiment: $1"
            echo "Available experiments:"
            echo "  litellm_direct_single"
            echo "  litellm_direct_edm"
            echo "  litellm_cot_single"
            echo "  litellm_cot_edm"
            exit 1
            ;;
    esac
fi