import asyncio
import logging
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
    hedge_delay_seconds: float = 3.0
    total_timeout_seconds: float = 15.0
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

    async def _ainvoke_candidates(self, candidates: list[Any], input: Any, provider_indexes=None, **kwargs: Any) -> Any:
        """Race a slow primary with one backup; validate before accepting a winner.

        Keep at most two calls in flight and cancel/await every loser. A shared
        deadline prevents multiplying latency by the number of backup keys.
        """
        indexes = list(range(len(candidates))) if provider_indexes is None else provider_indexes
        queue = [(index, candidate) for index, candidate in zip(indexes, candidates, strict=True)
                 if self._blocked_until.get(index, 0.0) <= time.monotonic()]
        if not queue:
            raise RuntimeError("All LLM providers are temporarily unavailable")
        pending = {}
        last_error = None
        started = time.monotonic()
        deadline = started + self.total_timeout_seconds
        hedge_at = started + self.hedge_delay_seconds
        def launch():
            index, candidate = queue.pop(0)
            task = asyncio.create_task(candidate.ainvoke(input, **kwargs))
            pending[task] = index
        launch()
        try:
            while pending:
                now = time.monotonic()
                remaining = deadline - now
                if remaining <= 0:
                    raise TimeoutError("LLM turn exceeded its total deadline")
                may_hedge = bool(queue) and len(pending) < 2
                wait = min(remaining, max(0, hedge_at - now)) if may_hedge else remaining
                done, _ = await asyncio.wait(pending, timeout=wait, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    index = pending.pop(task)
                    try:
                        result = task.result()
                        logging.getLogger(__name__).info("llm.completed provider_index=%d elapsed_ms=%.0f", index, (time.monotonic()-started)*1000)
                        return result
                    except Exception as exc:
                        self._mark_failed(index)
                        logging.getLogger(__name__).warning("llm.failed provider_index=%d error_type=%s status=%s elapsed_ms=%.0f", index, type(exc).__name__, getattr(exc, "status_code", None), (time.monotonic()-started)*1000)
                        if hasattr(exc, "errors"):
                            logging.getLogger(__name__).warning("llm.validation_fields=%s", [(item["loc"], item["type"]) for item in exc.errors(include_input=False)][:10])
                        last_error = exc
                if queue and len(pending) < 2 and (not pending or time.monotonic() >= hedge_at):
                    launch()
                    hedge_at = time.monotonic() + self.hedge_delay_seconds
            if last_error:
                raise last_error
            raise RuntimeError("All LLM providers are temporarily unavailable")
        finally:
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

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
        return await self.owner._ainvoke_candidates(self.candidates, input, self.provider_indexes, **kwargs)

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
    openrouter_backups = providers[1:]
    providers = providers[:1]
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

    # 3. Nhà cung cấp dự phòng: DeepSeek
    deepseek_api_key = _usable_secret(getattr(settings, "deepseek_api_key", ""))
    if deepseek_api_key:
        providers.append(
            _build_openai_compatible_model(
                api_key=deepseek_api_key,
                base_url=getattr(settings, "deepseek_base_url", "https://api.deepseek.com"),
                model=getattr(settings, "deepseek_model_name", "DeepSeek-V4.1-Flash"),
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    providers.extend(openrouter_backups)

    # 4. Backward compatibility cho OPENAI_API_KEY trực tiếp
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
        hedge_delay_seconds=settings.llm_hedge_delay_seconds,
        total_timeout_seconds=settings.llm_total_timeout_seconds,
    )
