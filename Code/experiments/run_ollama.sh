#!/bin/bash
# Run Ollama experiments
# Usage: ./experiments/run_ollama.sh [experiment_name]
# If no argument, runs all ollama experiments sequentially

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

# Main
if [ $# -eq 0 ]; then
    echo "Running all Ollama experiments..."
    echo ""

    run_ollama_direct_single
    run_ollama_direct_edm
    run_ollama_cot_single
    run_ollama_cot_edm

    echo "=========================================="
    echo "All Ollama experiments completed!"
    echo "=========================================="
else
    # Run specific experiment
    case $1 in
        ollama_direct_single) run_ollama_direct_single ;;
        ollama_direct_edm) run_ollama_direct_edm ;;
        ollama_cot_single) run_ollama_cot_single ;;
        ollama_cot_edm) run_ollama_cot_edm ;;
        *)
            echo "Unknown experiment: $1"
            echo "Available experiments:"
            echo "  ollama_direct_single"
            echo "  ollama_direct_edm"
            echo "  ollama_cot_single"
            echo "  ollama_cot_edm"
            exit 1
            ;;
    esac
fi