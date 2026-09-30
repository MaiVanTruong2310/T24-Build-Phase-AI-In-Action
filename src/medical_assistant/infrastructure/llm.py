import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI

from src.medical_assistant.config import get_settings


@dataclass
class FailoverChatModel:
    """OpenAI-compatible providers with a small failure circuit breaker."""

    primary: ChatOpenAI
    fallbacks: list[ChatOpenAI]
    cooldown_seconds: float = 30.0
    _blocked_until: dict[int, float] = field(default_factory=dict, init=False, repr=False)

    @property
    def providers(self) -> list[Any]:
        return [self.primary, *self.fallbacks]

    def _available(self) -> list[tuple[int, Any]]:
        now = time.monotonic()
        return [
            (index, provider)
            for index, provider in enumerate(self.providers)
            if self._blocked_until.get(index, 0.0) <= now
        ]

    def _mark_failed(self, index: int) -> None:
        self._blocked_until[index] = time.monotonic() + self.cooldown_seconds

    async def _ainvoke_candidates(self, candidates: list[Any], input: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for index, candidate in enumerate(candidates):
            if self._blocked_until.get(index, 0.0) > time.monotonic():
                continue
            try:
                return await candidate.ainvoke(input, **kwargs)
            except Exception as exc:
                self._mark_failed(index)
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("All LLM providers are temporarily unavailable")

    def _invoke_candidates(self, candidates: list[Any], input: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for index, candidate in enumerate(candidates):
            if self._blocked_until.get(index, 0.0) > time.monotonic():
                continue
            try:
                return candidate.invoke(input, **kwargs)
            except Exception as exc:
                self._mark_failed(index)
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("All LLM providers are temporarily unavailable")

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        structured: list[Any] = []
        provider_indexes: list[int] = []
        for index, provider in enumerate(self.providers):
            try:
                structured.append(provider.with_structured_output(schema, **kwargs))
                provider_indexes.append(index)
            except Exception:
                self._mark_failed(index)
        if not structured:
            raise RuntimeError("No LLM provider supports the requested structured output")
        return _StructuredFailover(self, structured, provider_indexes)

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        return await self._ainvoke_candidates(self.providers, input, **kwargs)

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        return self._invoke_candidates(self.providers, input, **kwargs)


@dataclass
class _StructuredFailover:
    owner: FailoverChatModel
    candidates: list[Any]
    provider_indexes: list[int]

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for candidate, provider_index in zip(self.candidates, self.provider_indexes, strict=True):
            if self.owner._blocked_until.get(provider_index, 0.0) > time.monotonic():
                continue
            try:
                return await candidate.ainvoke(input, **kwargs)
            except Exception as exc:
                self.owner._mark_failed(provider_index)
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("All LLM providers are temporarily unavailable")

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for candidate, provider_index in zip(self.candidates, self.provider_indexes, strict=True):
            if self.owner._blocked_until.get(provider_index, 0.0) > time.monotonic():
                continue
            try:
                return candidate.invoke(input, **kwargs)
            except Exception as exc:
                self.owner._mark_failed(provider_index)
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("All LLM providers are temporarily unavailable")


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


def _usable_secret(value: str) -> str:
    candidate = value.strip()
    lowered = candidate.lower()
    if not candidate or any(marker in lowered for marker in ("your-key", "replace-with", "<get-your")):
        return ""
    return candidate


@lru_cache(maxsize=1)
def get_llm() -> FailoverChatModel:
    settings = get_settings()
    providers: list[ChatOpenAI] = []

    # 1. Thu thập tất cả key OpenRouter (Key chính + các Key backup)
    openrouter_keys: list[str] = []
    primary_openrouter_key = _usable_secret(settings.openrouter_api_key)
    if primary_openrouter_key:
        openrouter_keys.append(primary_openrouter_key)

    backup_keys_raw = getattr(settings, "openrouter_backup_keys", "") or ""
    if backup_keys_raw:
        for k in backup_keys_raw.split(","):
            k_clean = _usable_secret(k)
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
    google_ai_api_key = _usable_secret(settings.google_ai_api_key)
    if google_ai_api_key:
        providers.append(
            _build_openai_compatible_model(
                api_key=google_ai_api_key,
                base_url=settings.google_ai_base_url,
                model=settings.google_ai_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # 3. Backward compatibility cho OPENAI_API_KEY trực tiếp
    openai_api_key = _usable_secret(settings.openai_api_key)
    if not providers and openai_api_key:
        providers.append(
            ChatOpenAI(
                model=settings.model_name,
                api_key=openai_api_key,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
                max_retries=0,
            )
        )

    if not providers:
        raise RuntimeError("No LLM provider is configured")
    return FailoverChatModel(
        primary=providers[0],
        fallbacks=providers[1:],
        cooldown_seconds=settings.llm_failure_cooldown_seconds,
    )
