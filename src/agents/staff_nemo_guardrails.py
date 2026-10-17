"""NeMo rail adapter for the existing deterministic Staff agent policies."""

from functools import lru_cache
from pathlib import Path
from typing import Any

from src.agents.staff_guardrails import staff_input_safety_refusal, staff_output_refusal

_CONFIG_PATH = Path(__file__).with_name("staff_guardrails_config")


def _input_allowed(text: str) -> bool:
    return staff_input_safety_refusal(text) is None


def _output_allowed(text: str) -> bool:
    return staff_output_refusal(text) is None


@lru_cache(maxsize=1)
def _get_rails() -> Any:
    from nemoguardrails import LLMRails, RailsConfig

    rails = LLMRails(RailsConfig.from_path(str(_CONFIG_PATH)))
    rails.register_action(_input_allowed, name="staff_input_allowed")
    rails.register_action(_output_allowed, name="staff_output_allowed")
    return rails


async def _is_allowed(role: str, message: str) -> bool:
    result = await _get_rails().check_async([{"role": role, "content": message}])
    status = getattr(result.status, "value", result.status)
    return str(status).lower() == "passed"


async def staff_input_allowed(message: str) -> bool:
    return await _is_allowed("user", message)


async def staff_output_allowed(message: str) -> bool:
    return await _is_allowed("assistant", message)
