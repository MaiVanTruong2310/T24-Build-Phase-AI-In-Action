"""
Security & Guardrails Domain Package.
Provides multi-layer defense-in-depth:
- Pre-ingestion de-obfuscation & normalization (Morse, Hex, Binary, Base64, Leet, Unicode)
- Adversarial attack defense (Prompt Injection, Jailbreak, System Prompt Exfiltration)
- Data Loss Prevention (DLP - Secret Keys, Tokens, Passwords, Patient PII/PHI)
- Multi-tenant patient context isolation
"""

from src.medical_assistant.domain.security.deobfuscator import (
    Deobfuscator,
    get_deobfuscator,
)
from src.medical_assistant.domain.security.security_guardrail_service import (
    SecurityGuardrailService,
    get_security_guardrail_service,
)
from src.medical_assistant.domain.security.dlp_service import (
    DLPService,
    get_dlp_service,
)

__all__ = [
    "Deobfuscator",
    "get_deobfuscator",
    "SecurityGuardrailService",
    "get_security_guardrail_service",
    "DLPService",
    "get_dlp_service",
]
