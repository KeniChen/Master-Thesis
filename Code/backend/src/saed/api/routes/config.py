"""Configuration management routes."""

from fastapi import APIRouter, HTTPException

from saed.api.schemas import (
    ConfigResponse,
    ModelsListResponse,
    ProviderInfo,
    ProvidersResponse,
    ProviderTestResponse,
    SetActiveProviderRequest,
    UpdateProviderRequest,
)
from saed.core.config.settings import (
    SUPPORTED_PROVIDERS,
    DefaultsConfig,
    LLMConfig,
    get_provider_config,
    load_config,
    save_config,
)
from saed.core.llm.providers import ProviderRegistry

router = APIRouter()


@router.get("", response_model=ConfigResponse)
async def get_config():
    """Get current configuration."""
    config = load_config()
    return ConfigResponse(
        llm=config.llm.model_dump(),
        defaults=config.defaults.model_dump(),
        paths=config.paths.model_dump(),
    )


@router.put("")
async def update_config(update: dict):
    """Update configuration."""
    try:
        config = load_config()

        # Update LLM config if provided
        if "llm" in update:
            llm_data = update["llm"]
            config.llm = LLMConfig(**llm_data)

        # Update defaults if provided
        if "defaults" in update:
            config.defaults = DefaultsConfig(**update["defaults"])

        save_config(config)
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating config: {e}") from None


# ============== Provider Endpoints ==============


@router.get("/llm/providers", response_model=ProvidersResponse)
async def get_providers():
    """Get all provider configurations and statuses."""
    config = load_config()
    registry = ProviderRegistry(config)

    # Check health for all configured providers
    await registry.check_all_health()

    providers = {}
    for provider in SUPPORTED_PROVIDERS:
        info = registry.get_provider_info(provider)
        providers[provider] = ProviderInfo(
            configured=info.configured,
            status=info.status,
            config=info.config,
        )

    return ProvidersResponse(
        active_provider=config.llm.active_provider,
        providers=providers,
    )


@router.put("/llm/providers/{provider}")
async def update_provider(provider: str, request: UpdateProviderRequest):
    """Update a specific provider's configuration."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    try:
        config = load_config()

        # Get current provider config and update it
        provider_config = get_provider_config(provider, config)
        provider_dict = provider_config.model_dump()

        # Update with new values
        for key, value in request.config.items():
            if key in provider_dict:
                provider_dict[key] = value

        # Set the updated config back
        setattr(config.llm.providers, provider, type(provider_config)(**provider_dict))

        save_config(config)
        return {"message": f"Provider {provider} configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating provider: {e}") from None


@router.post("/llm/providers/{provider}/test", response_model=ProviderTestResponse)
async def test_provider(provider: str):
    """Test connection to a specific provider."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    config = load_config()
    registry = ProviderRegistry(config)

    result = await registry.check_health(provider)

    return ProviderTestResponse(
        success=result.success,
        message=result.message,
        latency_ms=result.latency_ms,
    )


@router.get("/llm/providers/{provider}/models", response_model=ModelsListResponse)
async def list_provider_models(provider: str):
    """List available models for a specific provider."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    config = load_config()
    registry = ProviderRegistry(config)

    try:
        models, source = await registry.list_models(provider)
        return ModelsListResponse(models=models, source=source)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching models: {e}",
        ) from None


@router.put("/llm/active")
async def set_active_provider(request: SetActiveProviderRequest):
    """Set the active LLM provider."""
    provider = request.provider

    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    try:
        config = load_config()

        # Check if provider is configured
        registry = ProviderRegistry(config)
        if not registry.is_configured(provider):
            raise HTTPException(
                status_code=400,
                detail=f"Provider {provider} is not configured. Please configure it first.",
            )

        config.llm.active_provider = provider
        save_config(config)

        return {"message": f"Active provider set to {provider}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error setting active provider: {e}") from None


# Backward compatibility - keep old test endpoint
@router.post("/test", response_model=ProviderTestResponse)
async def test_connection():
    """Test active LLM provider connection."""
    config = load_config()
    return await test_provider(config.llm.active_provider)
