"""Request-scoped values included in structured application logs."""

from contextvars import ContextVar


trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")
session_id_var: ContextVar[str] = ContextVar("session_id", default="-")
turn_id_var: ContextVar[str] = ContextVar("turn_id", default="-")
