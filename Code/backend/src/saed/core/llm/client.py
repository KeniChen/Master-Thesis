"""LLM client for semantic annotation."""

import os
import warnings
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResult:
    """Result from an LLM call with token usage information."""

    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

from langchain_ollama.llms import OllamaLLM
from langchain_openai import AzureChatOpenAI, ChatOpenAI

try:
    from langchain_litellm import ChatLiteLLM  # type: ignore
except ImportError:  # pragma: no cover - fallback for environments without langchain-lintellm
    from langchain_community.chat_models import ChatLiteLLM  # type: ignore
    try:
        from langchain_core._api.deprecation import LangChainDeprecationWarning
    except Exception:
        LangChainDeprecationWarning = DeprecationWarning  # type: ignore[assignment]
    warnings.filterwarnings(
        "ignore",
        category=LangChainDeprecationWarning,
        message=r".*ChatLiteLLM.*deprecated.*",
    )

from saed.core.config.settings import (
    Config,
    ProviderName,
    get_provider_config,
    get_provider_model,
    load_config,
)
from saed.core.llm.prompts import cot_prompt, direct_prompt, edm_cot_prompt, edm_prompt

# Suppress pydantic v1 warnings on Python 3.14+
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3.14",
)


def create_llm(
    provider: ProviderName,
    model: str,
    config: Config,
    temperature: float = 0.0,
):
    """Create a LangChain LLM instance.

    Args:
        provider: LLM provider name
        model: Model name
        config: Configuration object
        temperature: Temperature for generation (default 0.0)

    Returns:
        LangChain LLM instance

    Raises:
        ValueError: If an invalid provider is specified.
    """
    provider_config = get_provider_config(provider, config)

    if provider == "ollama":
        return OllamaLLM(
            base_url=provider_config.base_url,
            model=model,
            temperature=temperature,
        )

    elif provider == "azure_openai":
        return AzureChatOpenAI(
            azure_endpoint=provider_config.endpoint,
            azure_deployment=model,  # Azure 中通常叫 Deployment Name
            api_key=provider_config.api_key,
            temperature=temperature,
            # 【关键修改】必须指定 API 版本
            api_version=getattr(provider_config, "api_version", "2024-02-15-preview"),
        )

    elif provider == "openai":
        kwargs = {
            "api_key": provider_config.api_key,
            "model": model,
            "temperature": temperature,
        }
        if provider_config.base_url:
            kwargs["base_url"] = provider_config.base_url
        return ChatOpenAI(**kwargs)

    elif provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                api_key=provider_config.api_key,
                model=model,
                temperature=temperature,
            )
        except ImportError:
            os.environ["ANTHROPIC_API_KEY"] = provider_config.api_key
            return ChatLiteLLM(
                model=f"anthropic/{model}",
                temperature=temperature,
            )

    elif provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                google_api_key=provider_config.api_key,
                model=model,
                temperature=temperature,
            )
        except ImportError:
            os.environ["GEMINI_API_KEY"] = provider_config.api_key
            return ChatLiteLLM(
                model=f"gemini/{model}",
                temperature=temperature,
            )

    elif provider == "litellm":
        # gpt-5 family only allows temperature=1; force safe value
        if "gpt-5" in model and temperature != 1:
            temperature = 1.0

        if not provider_config.api_base and "/" not in model:
            if model.startswith("azure-"):
                model = f"azure/{model.removeprefix('azure-')}"
            elif model.startswith("gpt-"):
                model = f"openai/{model}"

        kwargs = {
            "model": model,  # "azure-gpt-4.1"
            "temperature": temperature,
        }

        if provider_config.api_base:
            kwargs["api_base"] = provider_config.api_base
            kwargs["custom_llm_provider"] = "openai"

        if provider_config.api_key:
            kwargs["api_key"] = provider_config.api_key

        return ChatLiteLLM(**kwargs)

    else:
        raise ValueError(
            f"Invalid LLM provider: {provider}. "
            f"Supported: ollama, azure_openai, openai, anthropic, google, litellm"
        )


class SemanticAnnotationClient:
    """A class to represent LLM clients for semantic annotation."""

    def __init__(
        self,
        config: Config | None = None,
        provider: ProviderName | None = None,
        mode: str = "single",
        prompt_type: str = "cot",
    ):
        """Initialize the LLM client.

        Args:
            config: Optional configuration. If not provided, loads from file.
            provider: Optional provider override. If not provided, uses active_provider.
            mode: Decision mode ("single" or "edm").
        prompt_type: Prompt type ("direct" or "cot").

        Raises:
            ValueError: If an invalid provider or prompt type is provided.
        """
        if config is None:
            config = load_config()
        self.config = config
        self.provider = provider or config.llm.active_provider
        self.mode = mode
        self.prompt_type = prompt_type
        self._init_llm()
        self._init_prompt()
        self.chain = self.prompt | self.llm

    def _init_llm(self) -> None:
        """Initialize the LLM backend based on configuration."""
        model = get_provider_model(self.provider, self.config)
        self.llm = create_llm(self.provider, model, self.config, temperature=0.0)

    def _init_prompt(self) -> None:
        """Initialize the prompt based on experiment mode and prompt type."""
        if self.mode == "edm":
            if self.prompt_type == "cot":
                self.prompt = edm_cot_prompt
            elif self.prompt_type == "direct":
                self.prompt = edm_prompt
            else:
                raise ValueError("Invalid prompt type: expected direct or cot")
        else:
            if self.prompt_type == "direct":
                self.prompt = direct_prompt
            elif self.prompt_type == "cot":
                self.prompt = cot_prompt
            else:
                raise ValueError("Invalid prompt type: expected direct or cot")

    def _extract_token_usage(self, result: Any) -> tuple[int | None, int | None, int | None]:
        """Extract token usage from LangChain response metadata."""
        if self.provider == "ollama":
            # Ollama doesn't return token usage in the same way
            return None, None, None

        # Chat models return AIMessage with response_metadata
        metadata = getattr(result, "response_metadata", {}) or {}
        usage = metadata.get("usage", {}) or metadata.get("token_usage", {}) or {}

        # Different providers use different keys
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        # Calculate total if not provided
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens

        return input_tokens, output_tokens, total_tokens

    def generate(self, data: dict[str, Any]) -> LLMResult:
        """Generate a response from the LLM.

        Args:
            data: Dictionary containing:
                - table_name: Name of the table
                - table_in_markdown: Table data in markdown format
                - column_name: Name of the column to annotate
                - current_level_ontology_classes: Available ontology classes

        Returns:
            LLMResult with content and token usage information.
        """
        result = self.chain.invoke({
            "table_name": data["table_name"],
            "table_in_markdown": data["table_in_markdown"],
            "column_name": data["column_name"],
            "current_level_ontology_classes": data["current_level_ontology_classes"],
        })

        # Extract token usage
        input_tokens, output_tokens, total_tokens = self._extract_token_usage(result)

        # Handle different LLM response formats
        if self.provider == "ollama":
            content = result
        else:
            # Chat models return AIMessage with content attribute
            content = result.content

        return LLMResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    async def agenerate(self, data: dict[str, Any]) -> LLMResult:
        """Async version of generate for non-blocking LLM calls.

        Args:
            data: Dictionary containing:
                - table_name: Name of the table
                - table_in_markdown: Table data in markdown format
                - column_name: Name of the column to annotate
                - current_level_ontology_classes: Available ontology classes

        Returns:
            LLMResult with content and token usage information.
        """
        result = await self.chain.ainvoke({
            "table_name": data["table_name"],
            "table_in_markdown": data["table_in_markdown"],
            "column_name": data["column_name"],
            "current_level_ontology_classes": data["current_level_ontology_classes"],
        })

        # Extract token usage
        input_tokens, output_tokens, total_tokens = self._extract_token_usage(result)

        # Handle different LLM response formats
        if self.provider == "ollama":
            content = result
        else:
            # Chat models return AIMessage with content attribute
            content = result.content

        return LLMResult(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


# Backward compatibility aliases
LLM = SemanticAnnotationClient
LLMClient = SemanticAnnotationClient
