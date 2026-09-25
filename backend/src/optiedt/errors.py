"""Application errors.

Services raise these; the API turns them into RFC 9457 problem responses. Messages are written
for the person using the application, never containing internal details.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class FieldError:
    field: str
    message: str


@dataclass
class AppError(Exception):
    message: str
    code: str = "error"
    status: int = 400
    errors: list[FieldError] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class NotFound(AppError):
    def __init__(self, entity: str, identifier: object | None = None) -> None:
        text = f"{entity} not found" if identifier is None else f"{entity} {identifier} not found"
        super().__init__(text, code="not_found", status=404)


class Conflict(AppError):
    def __init__(self, message: str, code: str = "conflict", **details: object) -> None:
        super().__init__(message, code=code, status=409, details=dict(details))


class StaleVersion(Conflict):
    def __init__(self, entity: str) -> None:
        super().__init__(
            f"This {entity} was changed by someone else. Reload it and apply your change again.",
            code="stale_version",
        )


class InvalidInput(AppError):
    def __init__(
        self, message: str, errors: list[FieldError] | None = None, code: str = "invalid_input"
    ) -> None:
        super().__init__(message, code=code, status=422, errors=errors or [])


class Unauthenticated(AppError):
    def __init__(self, message: str = "Sign in to continue.") -> None:
        super().__init__(message, code="unauthenticated", status=401)


class PermissionDenied(AppError):
    def __init__(self, message: str = "You do not have permission to do this.") -> None:
        super().__init__(message, code="forbidden", status=403)


class TooManyRequests(AppError):
    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(
            message,
            code="too_many_requests",
            status=429,
            details={"retry_after_seconds": retry_after_seconds},
        )
