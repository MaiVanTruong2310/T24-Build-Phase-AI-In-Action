import asyncio
import logging
import threading
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
    _permanently_failed: set[int] = field(default_factory=set, init=False, repr=False)
    _last_winner: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _thread_local: Any = field(default_factory=threading.local, init=False, repr=False)

    def _set_last_winner(self, winner_meta: dict[str, Any]) -> None:
        self._last_winner = winner_meta
        try:
            self._thread_local.last_winner = winner_meta
        except Exception:
            pass

    @property
    def providers(self) -> list[Any]:
        return [self.primary, *self.fallbacks]

    def _available(self) -> list[tuple[int, Any]]:
        now = time.monotonic()
        return [
            (index, provider)
            for index, provider in enumerate(self.providers)
            if index not in self._permanently_failed and self._blocked_until.get(index, 0.0) <= now
        ]

    def _mark_failed(self, index: int, exc: Exception | None = None) -> None:
        status_code = getattr(exc, "status_code", None)
        err_msg = str(exc or "").lower()
        # Lỗi 402 (Payment Required/Insufficient credits) hoặc 401 (Unauthorized) là lỗi tài khoản
        # Cần block dài hạn để không gây hedge delay và lãng phí độ trễ 3-6s mỗi lượt
        if status_code in (401, 402) or "credits" in err_msg or "quota" in err_msg:
            self._permanently_failed.add(index)
            self._blocked_until[index] = time.monotonic() + 86400.0 * 365.0
            logging.getLogger(__name__).warning(
                "llm.permanently_blocked provider_index=%d status=%s reason=credit_or_auth_exhausted",
                index,
                status_code,
            )
        else:
            self._blocked_until[index] = time.monotonic() + self.cooldown_seconds

    async def _ainvoke_candidates(self, candidates: list[Any], input: Any, provider_indexes=None, **kwargs: Any) -> Any:
        """Race a slow primary with one backup; validate before accepting a winner.

        Keep at most two calls in flight and cancel/await every loser. A shared
        deadline prevents multiplying latency by the number of backup keys.
        """
        indexes = list(range(len(candidates))) if provider_indexes is None else provider_indexes
        queue = [
            (index, candidate)
            for index, candidate in zip(indexes, candidates, strict=True)
            if index not in self._permanently_failed and self._blocked_until.get(index, 0.0) <= time.monotonic()
        ]
        if not queue:
            raise RuntimeError("All LLM providers are temporarily unavailable")
        pending = {}
        last_error = None
        started = time.monotonic()
        deadline = started + self.total_timeout_seconds
        hedge_at = started + self.hedge_delay_seconds
        attempted_indexes: set[int] = set()

        def launch():
            index, candidate = queue.pop(0)
            attempted_indexes.add(index)
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
                        provider_obj = self.providers[index]
                        prov_model = getattr(provider_obj, "model_name", "unknown")
                        winner_meta = {
                            "provider_index": index,
                            "model": prov_model,
                            "model_name": prov_model,
                            "providers_attempted": len(attempted_indexes),
                            "is_primary": (index == 0),
                        }
                        self._set_last_winner(winner_meta)
                        if hasattr(result, "response_metadata") and isinstance(result.response_metadata, dict):
                            result.response_metadata.update(winner_meta)
                        logging.getLogger(__name__).info("llm.completed provider_index=%d model=%s elapsed_ms=%.0f", index, prov_model, (time.monotonic()-started)*1000)
                        return result
                    except Exception as exc:
                        self._mark_failed(index, exc)
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
        attempted_indexes: set[int] = set()
        for index, candidate in enumerate(candidates):
            if index in self._permanently_failed or self._blocked_until.get(index, 0.0) > time.monotonic():
                continue
            attempted_indexes.add(index)
            try:
                result = candidate.invoke(input, **kwargs)
                prov_model = getattr(candidate, "model_name", "unknown")
                winner_meta = {
                    "provider_index": index,
                    "model": prov_model,
                    "model_name": prov_model,
                    "providers_attempted": len(attempted_indexes),
                    "is_primary": (index == 0),
                }
                self._set_last_winner(winner_meta)
                if hasattr(result, "response_metadata") and isinstance(result.response_metadata, dict):
                    result.response_metadata.update(winner_meta)
                return result
            except Exception as exc:
                self._mark_failed(index, exc)
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("All LLM providers are temporarily unavailable")

    def get_last_winner(self) -> dict[str, Any]:
        """Trả về metadata của provider đã chiến thắng lượt gọi gần nhất."""
        try:
            val = getattr(self._thread_local, "last_winner", None)
            if val is not None and isinstance(val, dict):
                return dict(val)
        except Exception:
            pass
        return dict(self._last_winner or {})

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        structured: list[Any] = []
        provider_indexes: list[int] = []
        for index, provider in enumerate(self.providers):
            try:
                base_url = str(getattr(provider, "openai_api_base", "") or "")
                call_kwargs = dict(kwargs)
                # DeepSeek API không hỗ trợ response_format={'type': 'json_schema'}
                # Bắt buộc dùng method='function_calling'
                model_name = str(getattr(provider, "model_name", "") or "").lower()
                if ("deepseek" in base_url or "deepseek" in model_name) and "method" not in call_kwargs:
                    call_kwargs["method"] = "function_calling"

                structured.append(provider.with_structured_output(schema, **call_kwargs))
                provider_indexes.append(index)
            except Exception as exc:
                self._mark_failed(index, exc)
        if not structured:
            raise RuntimeError("No LLM provider supports the requested structured output")
        return _StructuredFailover(self, structured, provider_indexes)

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> Any:
        bound: list[Any] = []
        provider_indexes: list[int] = []
        for index, provider in enumerate(self.providers):
            try:
                bound.append(provider.bind_tools(tools, **kwargs))
                provider_indexes.append(index)
            except Exception as exc:
                self._mark_failed(index, exc)
        if not bound:
            raise RuntimeError("No LLM provider supports the requested tool binding")
        return _StructuredFailover(self, bound, provider_indexes)

    def check_health(self) -> dict[int, dict[str, Any]]:
        """Health-check nhanh các provider và loại bỏ provider hết credit hoặc sai auth."""
        results: dict[int, dict[str, Any]] = {}
        for index, provider in enumerate(self.providers):
            model = getattr(provider, "model_name", "unknown")
            base_url = getattr(provider, "openai_api_base", "unknown")
            try:
                # Gửi prompt siêu nhẹ để thăm dò
                provider.invoke("hi", max_tokens=5)
                results[index] = {"status": "healthy", "model": model, "base_url": base_url}
            except Exception as exc:
                self._mark_failed(index, exc)
                status_code = getattr(exc, "status_code", None)
                results[index] = {
                    "status": "unhealthy",
                    "model": model,
                    "base_url": base_url,
                    "error": str(exc),
                    "status_code": status_code,
                    "permanently_blocked": index in self._permanently_failed,
                }
        return results

    async def acheck_health(self) -> dict[int, dict[str, Any]]:
        """Health-check song song bất đồng bộ các provider, loại bỏ ngay provider 401/402 hoặc cạn quota."""
        results: dict[int, dict[str, Any]] = {}

        async def _ping_provider(index: int, provider: Any) -> None:
            model = getattr(provider, "model_name", "unknown")
            base_url = getattr(provider, "openai_api_base", "unknown")
            try:
                await provider.ainvoke("hi", max_tokens=5)
                results[index] = {"status": "healthy", "model": model, "base_url": base_url}
            except Exception as exc:
                self._mark_failed(index, exc)
                status_code = getattr(exc, "status_code", None)
                results[index] = {
                    "status": "unhealthy",
                    "model": model,
                    "base_url": base_url,
                    "error": str(exc),
                    "status_code": status_code,
                    "permanently_blocked": index in self._permanently_failed,
                }

        await asyncio.gather(*[_ping_provider(idx, p) for idx, p in enumerate(self.providers)], return_exceptions=True)
        return results

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
            if provider_index in self.owner._permanently_failed or self.owner._blocked_until.get(provider_index, 0.0) > time.monotonic():
                continue
            try:
                return candidate.invoke(input, **kwargs)
            except Exception as exc:
                self.owner._mark_failed(provider_index, exc)
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("All LLM providers are temporarily unavailable")

    def get_last_winner(self) -> dict[str, Any]:
        return self.owner.get_last_winner()


def _build_openai_compatible_model(
    *, api_key: str, base_url: str, model: str, temperature: float, timeout: float, max_tokens: int = 800
) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        timeout=timeout,
        max_tokens=max_tokens,
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
    provider_route = getattr(settings, "llm_provider", "deepseek").lower()

    # =========================================================================
    # 1. NHÀ CUNG CẤP CHÍNH (PRIMARY LLM): DEEPSEEK
    # =========================================================================
    # Toàn bộ hệ thống chạy mặc định trên DeepSeek (deepseek-chat).
    # Model này hỗ trợ đầy đủ Chat, ReAct Tool Calling và Function Calling / Structured Output.
    deepseek_providers: list[ChatOpenAI] = []
    deepseek_api_key = _usable_secret(getattr(settings, "deepseek_api_key", ""))
    if deepseek_api_key:
        ds_model = getattr(settings, "deepseek_model_name", "deepseek-chat")
        # Chuẩn hóa: các tên alias như flash hay version 4 map về deepseek-chat để tương thích 100%
        if not ds_model or "flash" in ds_model.lower() or "v4" in ds_model.lower() or "reasoner" in ds_model.lower():
            ds_model = "deepseek-chat"
        deepseek_providers.append(
            _build_openai_compatible_model(
                api_key=deepseek_api_key,
                base_url=getattr(settings, "deepseek_base_url", "https://api.deepseek.com"),
                model=ds_model,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # =========================================================================
    # 2. ĐIỀU HƯỚNG CÁC NHÀ CUNG CẤP KHÁC (OPENROUTER, GEMINI, OPENAI)
    # =========================================================================
    # Để điều hướng người dùng sang LLM khác:
    # Thiết lập LLM_PROVIDER=openrouter | gemini | openai trong .env
    # hoặc bật cờ ENABLE_LLM_FALLBACKS=true để dùng làm fallback khi DeepSeek gặp sự cố.

    # 2.1 Google AI Gemini (Tùy chọn điều hướng / dự phòng)
    google_providers: list[ChatOpenAI] = []
    google_ai_api_key = _usable_secret(getattr(settings, "google_ai_api_key", ""))
    if google_ai_api_key:
        google_providers.append(
            _build_openai_compatible_model(
                api_key=google_ai_api_key,
                base_url=settings.google_ai_base_url,
                model=settings.google_ai_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # 2.2 OpenRouter (Tùy chọn điều hướng / dự phòng)
    openrouter_providers: list[ChatOpenAI] = []
    openrouter_keys: list[str] = []
    primary_openrouter_key = _usable_secret(getattr(settings, "openrouter_api_key", ""))
    if primary_openrouter_key:
        openrouter_keys.append(primary_openrouter_key)
    backup_keys_raw = getattr(settings, "openrouter_backup_keys", "") or ""
    if backup_keys_raw:
        for k in backup_keys_raw.split(","):
            k_clean = _usable_secret(k)
            if k_clean and k_clean not in openrouter_keys:
                openrouter_keys.append(k_clean)

    for key in openrouter_keys:
        openrouter_providers.append(
            _build_openai_compatible_model(
                api_key=key,
                base_url=settings.openrouter_base_url,
                model=settings.openrouter_model_name,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # 2.3 OpenAI trực tiếp (Tùy chọn điều hướng / dự phòng)
    openai_providers: list[ChatOpenAI] = []
    openai_api_key = _usable_secret(getattr(settings, "openai_api_key", ""))
    if openai_api_key:
        oai_model = getattr(settings, "openai_model_name", None) or getattr(settings, "model_name", "gpt-4o-mini")
        if "deepseek" in oai_model.lower():
            oai_model = "gpt-4o-mini"
        openai_providers.append(
            _build_openai_compatible_model(
                api_key=openai_api_key,
                base_url=getattr(settings, "openai_base_url", "https://api.openai.com/v1"),
                model=oai_model,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
            )
        )

    # =========================================================================
    # 3. TẬP HỢP DANH SÁCH PROVIDERS THEO ĐIỀU HƯỚNG
    # =========================================================================
    providers: list[ChatOpenAI] = []
    enable_fallbacks = getattr(settings, "enable_llm_fallbacks", False)

    if provider_route == "openrouter" and openrouter_providers:
        # Điều hướng người dùng muốn dùng OpenRouter làm chính
        providers = [*openrouter_providers, *deepseek_providers, *google_providers]
    elif provider_route in ("google", "gemini") and google_providers:
        # Điều hướng người dùng muốn dùng Google Gemini làm chính
        providers = [*google_providers, *deepseek_providers, *openrouter_providers]
    elif provider_route == "openai" and openai_providers:
        # Điều hướng người dùng muốn dùng OpenAI làm chính
        providers = [*openai_providers, *deepseek_providers]
    else:
        # MẶC ĐỊNH: DeepSeek là Provider #1 (Primary)
        providers.extend(deepseek_providers)
        if enable_fallbacks:
            providers.extend(google_providers)
            providers.extend(openrouter_providers)
            providers.extend(openai_providers)

    if not providers:
        # Fallback an toàn nếu chưa cấu hình provider nào
        if deepseek_providers:
            providers = deepseek_providers
        elif openrouter_providers:
            providers = openrouter_providers
        elif google_providers:
            providers = google_providers
        elif openai_providers:
            providers = openai_providers

    if not providers:
        raise RuntimeError("No LLM provider is configured. Vui lòng cung cấp DEEPSEEK_API_KEY trong file .env")

    return FailoverChatModel(
        primary=providers[0],
        fallbacks=providers[1:],
        cooldown_seconds=settings.llm_failure_cooldown_seconds,
        hedge_delay_seconds=settings.llm_hedge_delay_seconds,
        total_timeout_seconds=settings.llm_total_timeout_seconds,
    )
