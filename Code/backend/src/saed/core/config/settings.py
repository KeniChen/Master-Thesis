"""Configuration management for SAED."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


def get_project_root() -> Path:
    """Return the project root (where backend/, frontend/, data/ live)."""
    current = Path(__file__).resolve()
    # settings.py -> config -> core -> saed -> src -> backend -> repo root
    return current.parent.parent.parent.parent.parent.parent


# Provider name type
ProviderName = Literal["ollama", "azure_openai", "openai", "anthropic", "google", "litellm"]

# All supported providers
SUPPORTED_PROVIDERS: list[ProviderName] = [
    "ollama",
    "azure_openai",
    "openai",
    "anthropic",
    "google",
    "litellm",
]


class OllamaConfig(BaseModel):
    """Ollama LLM configuration."""

    base_url: str = "http://localhost:11434"
    models: list[str] = Field(default_factory=list)
    default_model: str = ""


class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI configuration."""

    endpoint: str = ""
    api_key: str = ""
    models: list[str] = Field(default_factory=list)
    default_model: str = ""


class OpenAIConfig(BaseModel):
    """OpenAI configuration."""

    api_key: str = ""
    models: list[str] = Field(default_factory=list)
    default_model: str = ""


class AnthropicConfig(BaseModel):
    """Anthropic configuration."""

    api_key: str = ""
    models: list[str] = Field(default_factory=list)
    default_model: str = ""


class GoogleConfig(BaseModel):
    """Google Gemini configuration."""

    api_key: str = ""
    models: list[str] = Field(default_factory=list)
    default_model: str = ""


class LiteLLMConfig(BaseModel):
    """LiteLLM configuration."""

    api_key: str = ""
    api_base: str = ""
    models: list[str] = Field(default_factory=list)
    default_model: str = ""


class ProvidersConfig(BaseModel):
    """All provider configurations."""

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    azure_openai: AzureOpenAIConfig = Field(default_factory=AzureOpenAIConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    google: GoogleConfig = Field(default_factory=GoogleConfig)
    litellm: LiteLLMConfig = Field(default_factory=LiteLLMConfig)


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    active_provider: ProviderName = "ollama"
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)


class EDMOptions(BaseModel):
    """EDM (Ensemble Decision Making) options."""

    classes_per_agent: int = 30
    agents_per_class: int = 3
    consensus_threshold: float = 0.8


class DefaultsConfig(BaseModel):
    """Default run configuration."""

    mode: str = "single"  # single or edm
    prompt_type: str = "cot"  # direct or cot
    max_depth: int = 3
    k: int = 5
    edm_options: EDMOptions = Field(default_factory=EDMOptions)


class PathsConfig(BaseModel):
    """Data paths configuration."""

    tables: str = "data/tables"
    ontologies: str = "data/ontologies"
    runs: str = "data/runs"
    labels: str = "data/labels"
    batches: str = "data/batches"


class Config(BaseModel):
    """Main application configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_project_root() / "data" / "config.json"


def _migrate_provider_model(provider_config: dict) -> dict:
    """Migrate single model to models list format.

    Old: {"model": "gpt-4", ...}
    New: {"models": ["gpt-4"], "default_model": "gpt-4", ...}
    """
    if "model" in provider_config and "models" not in provider_config:
        model = provider_config.pop("model")
        if model:
            provider_config["models"] = [model]
            provider_config["default_model"] = model
        else:
            provider_config["models"] = []
            provider_config["default_model"] = ""
    return provider_config


def _migrate_old_config(data: dict) -> dict:
    """Migrate old config format to new format.

    Old format:
    {
        "llm": {
            "provider": "ollama",
            "ollama": {...},
            "azure_openai": {...}
        }
    }

    New format:
    {
        "llm": {
            "active_provider": "ollama",
            "providers": {
                "ollama": {...},
                "azure_openai": {...},
                ...
            }
        }
    }
    """
    if "llm" not in data:
        return data

    llm_data = data["llm"]

    # Check if already in new format
    if "active_provider" in llm_data and "providers" in llm_data:
        # Migrate google_gemini -> google
        if "google_gemini" in llm_data["providers"] and "google" not in llm_data["providers"]:
            llm_data["providers"]["google"] = llm_data["providers"].pop("google_gemini")
        if llm_data.get("active_provider") == "google_gemini":
            llm_data["active_provider"] = "google"

        # Still need to migrate model -> models for each provider
        for provider in SUPPORTED_PROVIDERS:
            if provider in llm_data["providers"]:
                llm_data["providers"][provider] = _migrate_provider_model(
                    llm_data["providers"][provider]
                )
        return data

    # Migrate from old format
    if "provider" in llm_data:
        new_llm = {
            "active_provider": llm_data.get("provider", "ollama"),
            "providers": {}
        }

        # Copy existing provider configs
        for provider in SUPPORTED_PROVIDERS:
            if provider in llm_data:
                new_llm["providers"][provider] = _migrate_provider_model(
                    llm_data[provider]
                )

        data["llm"] = new_llm

    # Normalize prompt_type naming (llm -> direct)
    defaults = data.get("defaults", {})
    if defaults.get("prompt_type") == "llm":
        defaults["prompt_type"] = "direct"
        data["defaults"] = defaults

    return data


def load_config() -> Config:
    """Load configuration from JSON file."""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
        # Migrate old format if needed
        data = _migrate_old_config(data)
        return Config(**data)
    return Config()


def save_config(config: Config) -> None:
    """Save configuration to JSON file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


def get_absolute_path(relative_path: str) -> Path:
    """Convert a relative path to absolute path from project root."""
    return get_project_root() / relative_path


def get_provider_config(provider: ProviderName, config: Config | None = None) -> BaseModel:
    """Get configuration for a specific provider."""
    if config is None:
        config = load_config()
    return getattr(config.llm.providers, provider)


def get_provider_model(provider: ProviderName, config: Config | None = None) -> str:
    """Get the current model for a provider (default_model or first from models list)."""
    provider_config = get_provider_config(provider, config)
    default_model = getattr(provider_config, "default_model", "")
    if default_model:
        return default_model
    models = getattr(provider_config, "models", [])
    return models[0] if models else ""


def is_provider_configured(provider: ProviderName, config: Config | None = None) -> bool:
    """Check if a provider has required parameters configured."""
    if config is None:
        config = load_config()

    provider_config = get_provider_config(provider, config)

    # Define required fields for each provider
    required_fields: dict[ProviderName, list[str]] = {
        "ollama": ["base_url"],
        "azure_openai": ["endpoint", "api_key"],
        "openai": ["api_key"],
        "anthropic": ["api_key"],
        "google": ["api_key"],
        "litellm": [],
    }

    for field in required_fields.get(provider, []):
        value = getattr(provider_config, field, "")
        if not value:
            return False

    # Must have at least one model configured
    models = getattr(provider_config, "models", [])
    default_model = getattr(provider_config, "default_model", "")
    return not (not models and not default_model)
