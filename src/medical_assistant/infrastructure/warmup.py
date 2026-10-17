"""Khởi tạo sẵn các dịch vụ nặng khi app khởi động, để người dùng đầu tiên không phải chờ.

Các dịch vụ này đều là singleton khởi tạo lười (lazy): nếu không làm nóng, request chat đầu tiên sau mỗi lần
khởi động phải gánh toàn bộ chi phí (đo được: import Presidio/spaCy ~3,9s trong node respond, dựng
ClinicalTriageService + nạp bảng disease_triage từ Supabase ~1,6-2,8s ở before_turn).
Mọi bước đều bọc try/except: warmup lỗi chỉ ghi log, không bao giờ chặn app khởi động.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def _triage() -> None:
    from src.medical_assistant.domain.triage_service import get_triage_service

    # Chạy thật một lần để biên dịch/nạp cache regex, không chỉ dựng đối tượng.
    get_triage_service().evaluate_symptoms("xin chào", language="vi")


def _presidio() -> None:
    from src.medical_assistant.domain.security.presidio_dlp_service import get_presidio_dlp_service

    get_presidio_dlp_service().sanitize("xin chào")


def _dlp() -> None:
    from src.medical_assistant.domain.security.dlp_service import get_dlp_service

    get_dlp_service().sanitize("xin chào")


def _validators() -> None:
    from src.medical_assistant.domain.security.guardrail_validators import MedicalSafetyValidators

    MedicalSafetyValidators.validate_no_prescription("xin chào")
    MedicalSafetyValidators.validate_no_definitive_diagnosis("xin chào")


def _cache_service() -> None:
    from src.medical_assistant.domain.cache_service import get_cache_service

    get_cache_service().check_cache("xin chào", language="vi")


def _token_counter() -> None:
    from src.medical_assistant.domain.token_counter import get_token_counter

    get_token_counter().count_tokens("xin chào")


def _guardrail() -> None:
    from src.medical_assistant.domain.guardrail_service import get_guardrail_service

    get_guardrail_service()


def _singletons() -> None:
    from src.medical_assistant.domain.care_pipeline_service import get_care_pipeline_service
    from src.medical_assistant.domain.clinical_negation_service import get_clinical_negation_service
    from src.medical_assistant.domain.compaction_service import get_compaction_service
    from src.medical_assistant.domain.middleware_pipeline import get_middleware_pipeline
    from src.medical_assistant.domain.probing_service import get_probing_service
    from src.medical_assistant.domain.specialty_router import get_specialty_router

    for getter in (
        get_care_pipeline_service,
        get_clinical_negation_service,
        get_compaction_service,
        get_middleware_pipeline,
        get_probing_service,
        get_specialty_router,
    ):
        getter()


_STEPS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("triage_service", _triage),
    ("presidio_dlp", _presidio),
    ("dlp", _dlp),
    ("validators", _validators),
    ("cache_service", _cache_service),
    ("token_counter", _token_counter),
    ("guardrail", _guardrail),
    ("singletons", _singletons),
)


def warmup_sync() -> dict[str, float]:
    """Chạy tuần tự các bước làm nóng (blocking). Gọi qua asyncio.to_thread từ lifespan."""
    timings: dict[str, float] = {}
    for name, step in _STEPS:
        started = time.perf_counter()
        try:
            step()
        except Exception as exc:
            logger.warning("warmup step %s failed: %s", name, exc)
        timings[name] = round((time.perf_counter() - started) * 1000, 1)
    logger.info("warmup done: %s", timings)
    return timings
