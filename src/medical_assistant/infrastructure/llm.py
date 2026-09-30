from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI

from src.medical_assistant.config import get_settings


@dataclass(frozen=True)
class FailoverChatModel:
    """OpenAI-compatible primary model with multiple transparent backup providers/keys."""

    primary: ChatOpenAI
    fallbacks: list[ChatOpenAI]

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        primary = self.primary.with_structured_output(schema, **kwargs)
        backup_structured = [fb.with_structured_output(schema, **kwargs) for fb in self.fallbacks]
        return primary.with_fallbacks(backup_structured)

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        return await self.primary.with_fallbacks(self.fallbacks).ainvoke(input, **kwargs)

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        return self.primary.with_fallbacks(self.fallbacks).invoke(input, **kwargs)


def _build_openai_compatible_model(
    *, api_key: str, base_url: str, model: str, temperature: float, timeout: float
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        timeout=timeout,
        max_tokens=1500,
        max_retries=0,
    )


def get_llm() -> ChatOpenAI | FailoverChatModel:
    settings = get_settings()
    providers: list[ChatOpenAI] = []

    # 1. Thu thập tất cả key OpenRouter (Key chính + các Key backup)
    openrouter_keys: list[str] = []
    if settings.openrouter_api_key:
        openrouter_keys.append(settings.openrouter_api_key)

    backup_keys_raw = getattr(settings, "openrouter_backup_keys", "") or ""
    if backup_keys_raw:
        for k in backup_keys_raw.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in openrouter_keys:
                openrouter_keys.append(k_clean)

    for key in openrouter_keys:
        providers.append(
            _build_openai_compatible_model(
                api_key=key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # 2. Nhà cung cấp dự phòng tiếp theo: Google AI Gemini
    if settings.google_ai_api_key:
        providers.append(
            _build_openai_compatible_model(
                api_key=settings.google_ai_api_key,
                base_url=settings.google_ai_base_url,
                model=settings.google_ai_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # 3. Backward compatibility cho OPENAI_API_KEY trực tiếp
    if not providers and settings.openai_api_key:
        providers.append(
            ChatOpenAI(
                model=settings.model_name,
                api_key=settings.openai_api_key,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
                max_retries=0,
            )
        )

    if not providers:
        raise RuntimeError("No LLM provider is configured")
    if len(providers) == 1:
        return providers[0]
    return FailoverChatModel(primary=providers[0], fallbacks=providers[1:])
