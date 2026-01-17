# Backend

The backend for semantic annotation of tabular data using large language models.

## Installation

```bash
cd backend
uv sync
```

## CLI Commands

```bash
# Start the API server
uv run saed-api

# Run batch annotation
uv run saed-batch --mode single --prompt cot

# Evaluate predictions
uv run saed-eval <run_id>
```

## Configuration

Configuration is stored in `data/config.json`. Key settings include:

- **LLM Provider**: ollama, azure_openai, or litellm (openai, azure, anthropic, google etc.)
- **Mode**: single (one agent) or edm (ensemble decision-making)
- **Prompt Type**: llm (direct answer) or cot (chain-of-thought reasoning)
