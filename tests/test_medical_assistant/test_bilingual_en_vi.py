"""
Bilingual English - Vietnamese (EN-VI) Comprehensive Test Suite (P-124).
Tests:
1. Language Detection (vi vs en).
2. Triage & Red Flag Safety in English (ATS 1, ATS 2, ATS 3, Outpatient).
3. Clinical Guardrails in English (Medication Refusal SAF-02, Diagnostic Refusal, Department Info).
4. Zero-Token FAQ Cache in English (Greeting, Fasting, Pricing, Operating Hours, Cancellation).
5. End-to-End English Patient Flow via LangGraph (Analyze & Respond nodes).
"""

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.cache_service import get_cache_service
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.language_service import (
    detect_language,
)
from src.medical_assistant.domain.triage_service import get_triage_service


class TestLanguageDetection:
    def test_detects_vietnamese_accented(self):
        assert detect_language("Tôi bị đau thắt ngực dữ dội") == "vi"
        assert detect_language("Bác sĩ cho hỏi uống thuốc gì") == "vi"
        assert detect_language("Xin chào bệnh viện Vinmec") == "vi"

    def test_detects_vietnamese_unaccented(self):
        assert detect_language("toi bi dau nguc sot va ho") == "vi"
        assert detect_language("dat lich kham bac si khoa than kinh") == "vi"

    def test_detects_english(self):
        assert detect_language("I have severe chest pain and dizziness") == "en"
        assert detect_language("Hello, I would like to book an appointment with a cardiologist") == "en"
        assert detect_language("What medicine should I take for fever?") == "en"
        assert detect_language("Do I need to fast before the blood test?") == "en"


class TestBilingualTriageEngine:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.triage = get_triage_service()

    def test_english_ats1_cardiac_arrest(self):
        res = self.triage.evaluate_symptoms("Patient collapsed and has stopped breathing, unresponsive")
        assert res.ats_level.value == 1
        assert res.is_emergency is True
        assert res.care_setting == "EMERGENCY_DEPT"
        assert "CRITICAL MEDICAL EMERGENCY" in res.patient_guidance
        assert "115" in res.patient_guidance

    def test_english_ats2_stemi_chest_pain(self):
        res = self.triage.evaluate_symptoms("I have severe crushing chest pain radiating to my left arm with cold sweats")
        assert res.ats_level.value == 2
        assert res.is_emergency is True
        assert res.care_setting == "EMERGENCY_DEPT"
        assert "ACUTE MEDICAL ALERT" in res.patient_guidance

    def test_english_ats2_stroke_fast(self):
        res = self.triage.evaluate_symptoms("Sudden facial droop and arm weakness, slurred speech")
        assert res.ats_level.value == 2
        assert res.is_emergency is True
        assert "Neurology" in res.suggested_specialty or "Thần kinh" in res.suggested_specialty

    def test_english_ats2_acute_dystonia(self):
        res = self.triage.evaluate_symptoms("Severe spasm of tongue and facial muscles, cannot close mouth")
        assert res.ats_level.value == 2
        assert res.is_emergency is True
        assert "ACUTE MEDICAL ALERT" in res.patient_guidance

    def test_english_outpatient_gerd(self):
        res = self.triage.evaluate_symptoms("I have burning sensation behind sternum, severe heartburn and acid reflux")
        assert res.ats_level.value == 4
        assert res.is_emergency is False
        assert res.suggested_specialty in ["Tiêu hóa - Gan mật", "Tiêu hóa"]
        assert "Gastroenterology" in res.patient_guidance

    def test_english_outpatient_respiratory(self):
        res = self.triage.evaluate_symptoms("I have persistent cough, wheezing and shortness of breath for 4 days")
        assert res.ats_level.value == 4
        assert res.is_emergency is False
        assert "hô hấp" in res.suggested_specialty.lower()
        assert "Pulmonology" in res.patient_guidance


class TestBilingualGuardrails:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.guardrail = get_guardrail_service()

    def test_english_medication_refusal(self):
        intent = self.guardrail.check_intent("What medicine should I take for this pain?")
        assert intent is not None
        assert intent["intent"] == "MEDICATION_GUARDRAIL"

        resp, quick_replies = self.guardrail.get_medication_guardrail_response(
            symptoms_summary="chest pain",
            suggested_dept="Trung tâm Tim mạch",
            language="en"
        )
        assert "Pharmaceutical Safety Warning (SAF-02)" in resp
        assert "prohibited from prescribing" in resp
        assert "Cardiology Center" in resp
        assert any("View Cardiology Center doctors" in qr for qr in quick_replies)

    def test_english_diagnosis_refusal(self):
        intent = self.guardrail.check_intent("Can you diagnose me what disease do I have?")
        assert intent is not None
        assert intent["intent"] == "DIAGNOSIS_GUARDRAIL"

        resp, quick_replies = self.guardrail.get_diagnosis_guardrail_response(
            symptoms_summary="severe headache",
            suggested_dept="Thần kinh",
            language="en"
        )
        assert "Safe clinical guidance (SAF-02)" in resp
        assert "cannot determine a specific disease" in resp
        assert "Tension-type Headache" not in resp
        assert "Migraine" not in resp
        assert "Neurology" in resp

    def test_english_department_info(self):
        intent = self.guardrail.check_intent("Please give me information about neurology department")
        assert intent is not None
        assert intent["intent"] == "DEPARTMENT_INFO"

        resp, quick_replies = self.guardrail.get_department_info_response("Thần kinh", language="en")
        assert "Department of Neurology" in resp
        assert "vinmec.com/eng/specialties/neurology" in resp


class TestBilingualZeroTokenCache:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.cache = get_cache_service()

    def test_english_greeting(self):
        cached = self.cache.check_cache("Hello, I want to book an appointment with a doctor")
        assert cached is not None
        resp, replies, key = cached
        assert key == "GREETING"
        assert "Vinmec Smart Medical Assistant" in resp
        assert any("Chest discomfort" in r for r in replies)

    def test_english_fasting(self):
        cached = self.cache.check_cache("Do I need to fast before the blood test tomorrow morning?")
        assert cached is not None
        resp, replies, key = cached
        assert key == "FASTING_PREPARATION"
        assert "fast for 6 to 8 hours" in resp

    def test_english_pricing(self):
        cached = self.cache.check_cache("How much is the consultation fee for specialist exam?")
        assert cached is not None
        resp, replies, key = cached
        assert key == "PRICING_INFO"
        assert "Vinmec Outpatient Examination Fee Schedule" in resp
        assert "690,000 VND" in resp

    def test_english_operating_hours(self):
        cached = self.cache.check_cache("What are your clinic operating hours on Saturday?")
        assert cached is not None
        resp, replies, key = cached
        assert key == "WORKING_HOURS_HOTLINE"
        assert "Operating Hours & Hospital Hotlines" in resp
        assert "24/7" in resp


@pytest.mark.asyncio
class TestEnglishAgentNodeFlow:
    async def test_english_full_conversation(self):
        # 1. User shares symptom in English
        state_1: AgentState = {
            "query": "I have been having a severe headache and feeling dizzy for two days",
            "probing_turn": 0,
            "collected_details": [],
        }
        res_analyze_1 = await analyze_node(state_1)
        assert res_analyze_1["language"] == "en"
        assert res_analyze_1["workflow_status"] == "PROBING_IN_PROGRESS"
        assert res_analyze_1["probing_turn"] == 1

        state_1.update(res_analyze_1)
        res_respond_1 = await respond_node(state_1)
        # Should contain English probing question and English disclaimer
        assert "Medical Disclaimer" in res_respond_1["disclaimer"]
        assert "headache" in res_respond_1["response"].lower() or "đau đầu" in res_respond_1["response"].lower()

        # 2. Patient provides clarification
        state_2: AgentState = {
            "query": "The pain is on one side and I feel nauseous",
            "probing_turn": 1,
            "active_probing_category": res_analyze_1["active_probing_category"],
            "collected_details": res_analyze_1["collected_details"],
            "language": "en",
        }
        res_analyze_2 = await analyze_node(state_2)
        assert res_analyze_2["language"] == "en"

        # 3. Patient reserves a slot
        state_3: AgentState = {
            "query": "Please hold slot 6749fa56 for me",
            "suggested_department_name": "Thần kinh",
            "language": "en",
        }
        res_analyze_3 = await analyze_node(state_3)
        assert res_analyze_3["workflow_status"] == "BOOKING_CONTACT_REQUIRED"
        assert res_analyze_3["metadata"]["slot_id"] == "6749fa56"

        state_3.update(res_analyze_3)
        res_respond_3 = await respond_node(state_3)
        assert "not verified" in res_respond_3["response"]
        assert "BK-6749FA" not in res_respond_3["response"]
