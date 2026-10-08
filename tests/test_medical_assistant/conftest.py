import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def keep_medical_assistant_tests_offline(request):
    if (
        request.path.name
        not in {
            "test_chat_profile_memory.py",
            "test_clinical_guardrails_flow.py",
            "test_hybrid_llm_extractor_and_probing.py",
            "test_multi_symptom_routing.py",
            "test_natural_language_resilience.py",
            "test_schedule_followup_flow.py",
            "test_supplementary_gap_coverage.py",
        }
        or os.getenv("RUN_LIVE_LLM", "").lower() in ("true", "1", "yes")
        or request.node.get_closest_marker("integration")
    ):
        yield
        return

    with (
        patch(
            "src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates",
            side_effect=RuntimeError("Offline test mode - LLM network disabled"),
        ),
        patch(
            "src.medical_assistant.domain.hybrid_dialogue_service.get_llm",
            side_effect=RuntimeError("Offline test mode - LLM network disabled"),
        ),
    ):
        yield
