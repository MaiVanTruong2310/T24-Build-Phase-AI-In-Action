"""Backward-compatibility bridge for agent nodes.

This module re-exports `analyze_node` and `respond_node` which have been refactored
into their own modular files:
- `src.medical_assistant.agent.nodes.analyze_node`
- `src.medical_assistant.agent.nodes.respond_node`
"""

from src.medical_assistant.agent.nodes.analyze_node import analyze_node
from src.medical_assistant.agent.nodes.helpers import extract_facility_inquiry
from src.medical_assistant.agent.nodes.respond_node import respond_node

__all__ = ["analyze_node", "respond_node", "extract_facility_inquiry"]
