"""Request context, access logging, security headers and upload size limits."""

from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from optiedt.api.metrics import observe_request
from optiedt.context import client_ip_var, request_id_var, user_id_var

logger = logging.getLogger("optiedt.access")

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
]
API_CSP = (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'")


class RequestContextMiddleware:
    """Pure ASGI middleware (no response buffering, so file downloads stream)."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        incoming = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        client = scope.get("client")
        request_tokens = [
            request_id_var.set(request_id),
            client_ip_var.set(client[0] if client else None),
            user_id_var.set(None),
        ]

        declared_length = headers.get(b"content-length")
        if declared_length is not None and int(declared_length) > self.max_body_bytes:
            await _reject_too_large(send, request_id)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _BodyTooLarge()
            return message

        status_holder = {"status": 500}
        started = time.perf_counter()

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                response_headers = list(message.get("headers", []))
                names = {name.lower() for name, _ in response_headers}
                for name, value in SECURITY_HEADERS:
                    if name not in names:
                        response_headers.append((name, value))
                if scope["path"].startswith("/api/") and b"content-security-policy" not in names:
                    response_headers.append(API_CSP)
                if b"cache-control" not in names and scope["path"].startswith("/api/"):
                    response_headers.append((b"cache-control", b"no-store"))
                response_headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, limited_receive, send_with_headers)
        except _BodyTooLarge:
            await _reject_too_large(send, request_id)
            status_holder["status"] = 413
        finally:
            elapsed = time.perf_counter() - started
            route = scope.get("route")
            template = getattr(route, "path", None) or "unmatched"
            observe_request(scope["method"], template, status_holder["status"], elapsed)
            logger.info(
                "%s %s %s %.1fms",
                scope["method"],
                scope["path"],
                status_holder["status"],
                elapsed * 1000,
                extra={
                    "http_method": scope["method"],
                    "path": scope["path"],
                    "status": status_holder["status"],
                    "duration_ms": round(elapsed * 1000, 1),
                },
            )
            for var, token in zip(
                (request_id_var, client_ip_var, user_id_var), request_tokens, strict=True
            ):
                var.reset(token)


class _BodyTooLarge(Exception):
    pass


async def _reject_too_large(send: Send, request_id: str) -> None:
    body = (
        b'{"type":"https://docs.optiedt.app/problems/payload_too_large","title":"Payload too '
        b'large","status":413,"detail":"The request body is larger than allowed.",'
        b'"code":"payload_too_large","request_id":"' + request_id.encode("latin-1") + b'"}'
    )
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/problem+json"),
                (b"content-length", str(len(body)).encode()),
                *SECURITY_HEADERS,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
