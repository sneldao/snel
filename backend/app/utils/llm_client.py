"""
LLM Client Factory - Returns Venice AI or OpenAI based on availability.
Venice AI is the primary provider with OpenAI as fallback.
"""
import logging
from typing import Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Venice AI Configuration
VENICE_API_URL = "https://api.venice.ai/api/v1"
VENICE_DEFAULT_MODEL = "mistral-31-24b"


def get_llm_client(
    venice_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    venice_model: str = VENICE_DEFAULT_MODEL,
    openai_model: str = "gpt-4o",
) -> tuple[AsyncOpenAI, str, str]:
    """
    Get LLM client (Venice AI primary, OpenAI fallback).
    
    Returns:
        tuple: (client, model_id, provider_name)
        
    Raises:
        ValueError: If no API keys are provided
    """
    # Try Venice AI first (primary provider)
    if venice_api_key:
        logger.info(f"Using Venice AI as primary LLM provider (model: {venice_model})")
        client = AsyncOpenAI(
            api_key=venice_api_key,
            base_url=VENICE_API_URL,
        )
        return client, venice_model, "venice"
    
    # Fall back to OpenAI
    if openai_api_key:
        logger.info(f"Using OpenAI as LLM provider (model: {openai_model})")
        client = AsyncOpenAI(api_key=openai_api_key)
        return client, openai_model, "openai"
    
    # No valid configuration
    logger.error("No LLM API keys configured (VENICE_API_KEY or OPENAI_API_KEY)")
    raise ValueError(
        "No LLM provider configured. Please set VENICE_API_KEY or OPENAI_API_KEY"
    )


def get_llm_client_from_settings(settings) -> tuple[AsyncOpenAI, str, str]:
    """
    Get LLM client using settings object.
    
    Args:
        settings: Settings object with external_services
        
    Returns:
        tuple: (client, model_id, provider_name)
    """
    return get_llm_client(
        venice_api_key=settings.external_services.venice_api_key,
        openai_api_key=settings.external_services.openai_api_key,
        venice_model=settings.external_services.venice_model,
        openai_model=settings.external_services.openai_model,
    )
