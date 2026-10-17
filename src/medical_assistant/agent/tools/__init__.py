"""Read-only tools package for medical assistant agent."""

from src.medical_assistant.agent.tools.base import ToolExecutionError
from src.medical_assistant.agent.tools.department_tools import get_department_info
from src.medical_assistant.agent.tools.disease_tools import search_disease_knowledge
from src.medical_assistant.agent.tools.doctor_tools import (
    get_doctor_detail,
    get_doctor_slots,
    search_doctors,
)
from src.medical_assistant.agent.tools.facility_tools import list_facilities

ALL_TOOLS = [
    search_doctors,
    get_doctor_detail,
    get_doctor_slots,
    get_department_info,
    search_disease_knowledge,
    list_facilities,
]

__all__ = [
    "ToolExecutionError",
    "search_doctors",
    "get_doctor_detail",
    "get_doctor_slots",
    "get_department_info",
    "search_disease_knowledge",
    "list_facilities",
    "ALL_TOOLS",
]
