"""Production LLM Client Service.

Provides High Availability LLM access with Circuit Breakers,
Hedged Requests failover, and multi-provider fallback.
"""

from __future__ import annotations

import logging
from typing import Any
from langchain_openai import ChatOpenAI

from src.config import get_settings
from src.medical_assistant.infrastructure.llm import (
    FailoverChatModel,
    create_chat_model as _create_chat_model,
    get_failover_chat_model as _get_failover_chat_model,
    get_llm_chain as _get_llm_chain,
)

logger = logging.getLogger(__name__)


def get_llm(temperature: float | None = None) -> Any:
    """Create or return the primary configured chat model for agent nodes.

    Falls back to OpenRouter/Gemini/OpenAI based on environment configuration.
    """
    settings = get_settings()
    temp = temperature if temperature is not None else settings.llm_temperature
    try:
        return _create_chat_model(temperature=temp)
    except Exception as exc:
        logger.warning("Falling back to basic ChatOpenAI client: %s", exc)
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key or "sk-dummy",
            temperature=temp,
        )


def get_failover_llm(temperature: float = 0.2) -> FailoverChatModel:
    """Return the High-Availability Failover LLM Gateway.

    Features:
    - Hedged Requests (races slow primary with fast backup)
    - Circuit Breaker (30s cooldown for rate limits/failures)
    - Automatic provider cooldown & retry
    """
    return _get_failover_chat_model(temperature=temperature)


__all__ = [
    "FailoverChatModel",
    "get_llm",
    "get_failover_llm",
    "create_chat_model",
]
