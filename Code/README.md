# Semantic annotation for energy data using ensemble decision-making with LLMs.

## Project layout
- `backend/`: API and CLI services.
- `frontend/`: Next.js web UI.
- `data/`: ontologies, tables, configs, and experiment outputs.

## Prereqs
- `uv`
- Node.js 24 and `pnpm`

## Quick start

1. Configure your LLM provider in `data/config.json` (copied from `data/config.example.json` during setup):

```json
{
  "llm": {
    "active_provider": "ollama",
    "providers": {
      "ollama": {
        "base_url": "http://localhost:11434",
        "models": ["llama3.1:8b"],
        "default_model": "llama3.1:8b"
      },
      "openai": {
        "api_key": "your-api-key",
        "models": ["gpt-4o-mini"],
        "default_model": "gpt-4o-mini"
      }
    }
  }
}
```

2. Start the development servers:

```bash
# Run both backend and frontend
make dev

# Or run separately in two terminals:
make dev-api   # Backend API (http://localhost:8000)
make dev-web   # Frontend (http://localhost:3000)
```

3. Open http://localhost:3000 in your browser.

## Datasets

We use the Building Energy Ontology (BEO) and related tabular data in the energy domain.

## CLI Commands

### `saed-run` - Single Table Annotation

Run semantic annotation on a single table:

```bash
# Annotate specific columns
saed-run --table 28.csv --ontology BEO.rdf --columns "Energy" "Temperature"

# Annotate all columns
saed-run --table 28.csv --ontology BEO.rdf --all-columns

# Override provider and model
saed-run --table 28.csv --ontology BEO.rdf --all-columns --provider openai --model gpt-4o-mini

# Use EDM (Ensemble Decision-Making) mode
saed-run --table 28.csv --ontology BEO.rdf --all-columns --mode edm

# Specify output directory
saed-run --table 28.csv --ontology BEO.rdf --all-columns --output-dir experiments/exp001/
```

**Options:**
- `--table`: Table filename or registry ID (required)
- `--ontology`: Ontology filename or registry ID (required)
- `--columns`: Column names to annotate
- `--all-columns`: Annotate all columns
- `--mode`: Decision mode (`single` or `edm`)
- `--prompt`: Prompt type (`direct` or `cot`)
- `--max-depth`: Maximum BFS depth
- `--k`: Number of sample rows
- `--provider`: LLM provider (overrides config)
- `--model`: Model name (overrides config)
- `--output-dir`: Output directory
- `--quiet`: Suppress detailed output

### `saed-run-batch` - Batch Annotation

Run batch annotation on multiple tables.

#### From YAML config file

```bash
saed-run-batch config experiments/exp001/config.yaml --output-dir experiments/exp001/
```

Example config file (`config.yaml`):

```yaml
ontology: BEO.rdf
mode: single
prompt_type: cot
max_depth: 3
k: 5
tasks:
  - table: 28.csv
    columns: [Energy, Temperature]
  - table: 29.csv
    columns: all
  - table: "*.csv"
    columns: all
```

#### From command line

```bash
# Run multiple tables
saed-run-batch run --tables 28.csv 29.csv --ontology BEO.rdf --all-columns

# Run all tables in a category
saed-run-batch run --category real --ontology BEO.rdf --all-columns

# Specify output directory
saed-run-batch run --tables 28.csv --ontology BEO.rdf --all-columns --output-dir experiments/exp001/
```

## Experiments

We provide 8 pre-configured experiments comparing different LLM providers, prompt types, and decision modes:

| Experiment | Provider | Model | Prompt | Mode |
|------------|----------|-------|--------|------|
| `ollama_direct_single` | ollama | gpt-oss:20b | direct | single |
| `ollama_direct_edm` | ollama | gpt-oss:20b | direct | edm |
| `ollama_cot_single` | ollama | gpt-oss:20b | cot | single |
| `ollama_cot_edm` | ollama | gpt-oss:20b | cot | edm |
| `litellm_direct_single` | litellm | azure-gpt-4.1 | direct | single |
| `litellm_direct_edm` | litellm | azure-gpt-4.1 | direct | edm |
| `litellm_cot_single` | litellm | azure-gpt-4.1 | cot | single |
| `litellm_cot_edm` | litellm | azure-gpt-4.1 | cot | edm |

Each experiment runs on 47 tables (1-48, excluding 21) with all columns.

### Running Experiments

```bash
# Run all 8 experiments
./experiments/run.sh

# Run a specific experiment
./experiments/run.sh ollama_cot_single
./experiments/run.sh litellm_direct_edm
```

Results are saved to `experiments/<experiment_name>/`.
