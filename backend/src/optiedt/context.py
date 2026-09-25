"""Request- and job-scoped context shared by logging and the audit trail."""

from __future__ import annotations

from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
client_ip_var: ContextVar[str | None] = ContextVar("client_ip", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
run_id_var: ContextVar[str | None] = ContextVar("run_id", default=None)
