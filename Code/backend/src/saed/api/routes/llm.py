"""LLM interaction routes."""

import time

from fastapi import APIRouter, HTTPException

from saed.api.schemas import ChatRequest, ChatResponse
from saed.core.config.settings import (
    SUPPORTED_PROVIDERS,
    get_provider_model,
    load_config,
)
from saed.core.llm.client import create_llm

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a test message to LLM and get a response."""
    config = load_config()

    # Determine provider and model
    provider = request.provider or config.llm.active_provider
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    model = request.model or get_provider_model(provider, config)
    if not model:
        raise HTTPException(
            status_code=400,
            detail=f"No model configured for provider {provider}",
        )

    try:
        # Create LLM and invoke
        llm = create_llm(provider, model, config, temperature=0.7)

        start_time = time.time()
        result = llm.invoke(request.message)
        latency_ms = int((time.time() - start_time) * 1000)

        # Handle different response types
        response_text = result.content if hasattr(result, "content") else str(result)

        return ChatResponse(
            response=response_text,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM error: {str(e)}",
        ) from None
