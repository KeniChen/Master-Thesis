"""LLM Provider Registry and Health Check."""

from dataclasses import dataclass
from typing import Literal

import httpx

from saed.core.config.settings import (
    SUPPORTED_PROVIDERS,
    Config,
    ProviderName,
    get_provider_config,
    is_provider_configured,
    load_config,
)

ProviderStatus = Literal["connected", "error", "not_configured", "unknown"]


@dataclass
class HealthCheckResult:
    """Result of a provider health check."""

    success: bool
    message: str
    latency_ms: int | None = None


@dataclass
class ProviderInfo:
    """Information about a provider's configuration and status."""

    name: ProviderName
    configured: bool
    status: ProviderStatus
    config: dict
    error_message: str | None = None


class ProviderRegistry:
    """Registry for managing LLM providers."""

    def __init__(self, config: Config | None = None):
        """Initialize the provider registry."""
        self.config = config or load_config()
        self._status_cache: dict[ProviderName, ProviderStatus] = {}

    def get_active_provider(self) -> ProviderName:
        """Get the currently active provider."""
        return self.config.llm.active_provider

    def get_all_providers(self) -> list[ProviderName]:
        """Get list of all supported providers."""
        return list(SUPPORTED_PROVIDERS)

    def is_configured(self, provider: ProviderName) -> bool:
        """Check if a provider is configured."""
        return is_provider_configured(provider, self.config)

    def get_provider_config(self, provider: ProviderName) -> dict:
        """Get configuration for a provider (with masked secrets)."""
        config = get_provider_config(provider, self.config)
        config_dict = config.model_dump()

        # Mask sensitive fields (preserve length)
        sensitive_fields = ["api_key"]
        for field in sensitive_fields:
            if field in config_dict and config_dict[field]:
                config_dict[field] = "•" * len(config_dict[field])

        return config_dict

    def get_provider_config_raw(self, provider: ProviderName) -> dict:
        """Get raw configuration for a provider (including secrets)."""
        config = get_provider_config(provider, self.config)
        return config.model_dump()

    def get_provider_status(self, provider: ProviderName) -> ProviderStatus:
        """Get cached status for a provider."""
        if not self.is_configured(provider):
            return "not_configured"
        return self._status_cache.get(provider, "unknown")

    def get_provider_info(self, provider: ProviderName) -> ProviderInfo:
        """Get full information about a provider."""
        return ProviderInfo(
            name=provider,
            configured=self.is_configured(provider),
            status=self.get_provider_status(provider),
            config=self.get_provider_config(provider),
        )

    def get_all_providers_info(self) -> dict[ProviderName, ProviderInfo]:
        """Get information about all providers."""
        return {
            provider: self.get_provider_info(provider)
            for provider in SUPPORTED_PROVIDERS
        }

    async def check_health(self, provider: ProviderName) -> HealthCheckResult:
        """Check health of a specific provider."""
        if not self.is_configured(provider):
            self._status_cache[provider] = "not_configured"
            return HealthCheckResult(
                success=False,
                message=f"{provider} is not configured",
            )

        try:
            result = await self._do_health_check(provider)
            self._status_cache[provider] = "connected" if result.success else "error"
            return result
        except Exception as e:
            self._status_cache[provider] = "error"
            return HealthCheckResult(
                success=False,
                message=f"Health check failed: {str(e)}",
            )

    async def check_all_health(self) -> dict[ProviderName, HealthCheckResult]:
        """Check health of all configured providers."""
        results = {}
        for provider in SUPPORTED_PROVIDERS:
            if self.is_configured(provider):
                results[provider] = await self.check_health(provider)
            else:
                results[provider] = HealthCheckResult(
                    success=False,
                    message=f"{provider} is not configured",
                )
                self._status_cache[provider] = "not_configured"
        return results

    async def _do_health_check(self, provider: ProviderName) -> HealthCheckResult:
        """Perform the actual health check for a provider."""
        config = get_provider_config(provider, self.config)

        if provider == "ollama":
            return await self._check_ollama(config)
        elif provider == "azure_openai":
            return await self._check_azure_openai(config)
        elif provider == "openai":
            return await self._check_openai(config)
        elif provider == "anthropic":
            return await self._check_anthropic(config)
        elif provider == "google":
            return await self._check_google(config)
        elif provider == "litellm":
            return await self._check_litellm(config)
        else:
            return HealthCheckResult(
                success=False,
                message=f"Unknown provider: {provider}",
            )

    async def _check_ollama(self, config) -> HealthCheckResult:
        """Check Ollama health by listing models."""
        base_url = config.base_url.rstrip("/")
        async with httpx.AsyncClient() as client:
            import time
            start = time.time()
            response = await client.get(f"{base_url}/api/tags", timeout=5.0)
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                return HealthCheckResult(
                    success=True,
                    message=f"Connected to Ollama at {base_url}",
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    success=False,
                    message=f"Ollama returned status {response.status_code}",
                    latency_ms=latency,
                )

    async def _check_azure_openai(self, config) -> HealthCheckResult:
        """Check Azure OpenAI health."""
        endpoint = config.endpoint.rstrip("/")
        api_key = config.api_key

        async with httpx.AsyncClient() as client:
            import time
            start = time.time()
            # Use models endpoint to verify connection
            response = await client.get(
                f"{endpoint}/openai/models?api-version=2024-02-01",
                headers={"api-key": api_key},
                timeout=10.0,
            )
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                return HealthCheckResult(
                    success=True,
                    message=f"Connected to Azure OpenAI at {endpoint}",
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    success=False,
                    message=f"Azure OpenAI returned status {response.status_code}",
                    latency_ms=latency,
                )

    async def _check_openai(self, config) -> HealthCheckResult:
        """Check OpenAI health by listing models."""
        base_url = (config.base_url or "https://api.openai.com").rstrip("/")
        api_key = config.api_key

        async with httpx.AsyncClient() as client:
            import time
            start = time.time()
            response = await client.get(
                f"{base_url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                return HealthCheckResult(
                    success=True,
                    message="Connected to OpenAI",
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    success=False,
                    message=f"OpenAI returned status {response.status_code}",
                    latency_ms=latency,
                )

    async def _check_anthropic(self, config) -> HealthCheckResult:
        """Check Anthropic health."""
        api_key = config.api_key
        model = config.default_model or (config.models[0] if config.models else "claude-3-sonnet-20240229")

        # Anthropic doesn't have a models list endpoint, use a minimal message
        async with httpx.AsyncClient() as client:
            import time
            start = time.time()
            # Use the messages endpoint with a minimal request
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                timeout=15.0,
            )
            latency = int((time.time() - start) * 1000)

            # 200 means success, 401 means invalid key
            if response.status_code == 200:
                return HealthCheckResult(
                    success=True,
                    message="Connected to Anthropic",
                    latency_ms=latency,
                )
            elif response.status_code == 401:
                return HealthCheckResult(
                    success=False,
                    message="Invalid Anthropic API key",
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    success=False,
                    message=f"Anthropic returned status {response.status_code}",
                    latency_ms=latency,
                )

    async def _check_google(self, config) -> HealthCheckResult:
        """Check Google Gemini health by listing models."""
        api_key = config.api_key

        async with httpx.AsyncClient() as client:
            import time
            start = time.time()
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                timeout=10.0,
            )
            latency = int((time.time() - start) * 1000)

            if response.status_code == 200:
                return HealthCheckResult(
                    success=True,
                    message="Connected to Google Gemini",
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    success=False,
                    message=f"Google Gemini returned status {response.status_code}",
                    latency_ms=latency,
                )

    async def _check_litellm(self, config) -> HealthCheckResult:
        """Check LiteLLM health.

        LiteLLM is a proxy, so health depends on the underlying provider.
        If api_base is set, check that endpoint. Otherwise, assume configured.
        """
        if config.api_base:
            api_base = config.api_base.rstrip("/")
            api_key = config.api_key
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

            async with httpx.AsyncClient() as client:
                import time
                start = time.time()
                try:
                    # Try models endpoint with auth
                    response = await client.get(
                        f"{api_base}/v1/models",
                        headers=headers,
                        timeout=5.0,
                    )
                    latency = int((time.time() - start) * 1000)

                    if response.status_code == 200:
                        return HealthCheckResult(
                            success=True,
                            message=f"Connected to LiteLLM at {api_base}",
                            latency_ms=latency,
                        )
                    else:
                        return HealthCheckResult(
                            success=False,
                            message=f"LiteLLM returned status {response.status_code}",
                            latency_ms=latency,
                        )
                except Exception as e:
                    return HealthCheckResult(
                        success=False,
                        message=f"Cannot connect to LiteLLM at {api_base}: {e}",
                    )
        else:
            # No api_base, assume LiteLLM will use environment variables
            return HealthCheckResult(
                success=True,
                message="LiteLLM configured (using environment variables)",
            )

    # ========== Model Discovery ==========

    async def list_models(self, provider: ProviderName) -> tuple[list[str], str]:
        """Fetch available models from provider.

        Returns:
            Tuple of (models list, source) where source is "remote" or "static"
        """
        config = get_provider_config(provider, self.config)

        if provider == "ollama":
            return await self._list_ollama_models(config), "remote"
        elif provider == "azure_openai":
            return await self._list_azure_openai_models(config), "remote"
        elif provider == "openai":
            return await self._list_openai_models(config), "remote"
        elif provider == "anthropic":
            return self._get_anthropic_static_models(), "static"
        elif provider == "google":
            return await self._list_google_models(config), "remote"
        elif provider == "litellm":
            return await self._list_litellm_models(config), "remote"
        else:
            return [], "static"

    async def _list_ollama_models(self, config) -> list[str]:
        """List models from Ollama server."""
        base_url = config.base_url.rstrip("/")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            return []

    async def _list_azure_openai_models(self, config) -> list[str]:
        """List models from Azure OpenAI."""
        endpoint = config.endpoint.rstrip("/")
        api_key = config.api_key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{endpoint}/openai/models?api-version=2024-02-01",
                headers={"api-key": api_key},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
            return []

    async def _list_openai_models(self, config) -> list[str]:
        """List models from OpenAI."""
        base_url = (getattr(config, "base_url", None) or "https://api.openai.com").rstrip("/")
        api_key = config.api_key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                # Filter to only GPT models for cleaner list
                models = [m["id"] for m in data.get("data", [])]
                return sorted([m for m in models if "gpt" in m.lower()])
            return []

    def _get_anthropic_static_models(self) -> list[str]:
        """Return static list of Anthropic models (no discovery API)."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    async def _list_google_models(self, config) -> list[str]:
        """List models from Google Gemini."""
        api_key = config.api_key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                # Filter to generative models
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    if name.startswith("models/"):
                        name = name[7:]  # Remove "models/" prefix
                    if "gemini" in name.lower():
                        models.append(name)
                return sorted(models)
            return []

    async def _list_litellm_models(self, config) -> list[str]:
        """List models from LiteLLM proxy."""
        if not config.api_base:
            return []

        api_base = config.api_base.rstrip("/")
        api_key = config.api_key
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{api_base}/v1/models",
                    headers=headers,
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return [m["id"] for m in data.get("data", [])]
            except Exception:
                pass
            return []


# Convenience function
async def get_all_providers_status(config: Config | None = None) -> dict:
    """Get status of all providers."""
    registry = ProviderRegistry(config)
    await registry.check_all_health()

    return {
        "active_provider": registry.get_active_provider(),
        "providers": {
            name: {
                "configured": info.configured,
                "status": info.status,
                "config": info.config,
            }
            for name, info in registry.get_all_providers_info().items()
        },
    }
