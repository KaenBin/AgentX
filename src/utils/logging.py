"""Metadata-only HTTP diagnostics; never serialize requests or exceptions."""

from datetime import datetime, timezone
import json
import logging
import sys
import time
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def get_logger(name: str) -> logging.Logger:
    """Return a named logger without altering the application's root logging."""
    return logging.getLogger(name)


class RequestLogHandler(logging.Handler):
    """Write an explicit allowlist of request metadata as one JSON line."""

    def emit(self, record: logging.LogRecord) -> None:
        """Exclude message interpolation, exception text, bodies and headers."""
        payload = {
            "event": "http_request",
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "request_id": record.request_id,
            "method": record.method,
            "route": record.route,
            "status_code": record.status_code,
            "duration_ms": record.duration_ms,
            "error_kind": record.error_kind,
        }
        try:
            sys.stderr.write(json.dumps(payload) + "\n")
        except (OSError, ValueError):
            # Logging failure must not change a learning write or its response.
            pass


class RequestDiagnostics:
    """Attach generated IDs to HTTP responses and log only approved metadata."""

    def __init__(self, app: ASGIApp) -> None:
        """Configure a dedicated logger without duplicating handlers or root output."""
        self.app = app
        self.logger = get_logger("agentx.http")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not any(isinstance(handler, RequestLogHandler) for handler in self.logger.handlers):
            self.logger.addHandler(RequestLogHandler())

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Correlate success, handled failure and interrupted responses safely."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        started_at = time.monotonic()
        response_started = False
        status_code = 500
        error_kind = None

        async def identified_send(message):
            """Replace any response ID with the ID generated for this request."""
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = [
                    (name, value) for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                message = {**message, "headers": headers + [(b"x-request-id", request_id.encode("ascii"))]}
            await send(message)

        try:
            await self.app(scope, receive, identified_send)
        except Exception:
            if response_started:
                error_kind = "response_interrupted"
                # The original exception may contain private source or credentials.
                raise RuntimeError(f"Response interrupted; request ID {request_id}") from None
            error_kind = "unhandled_exception"
            response = JSONResponse(
                {"error": "Request failed. Retry or share the request ID.", "request_id": request_id},
                status_code=500,
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            )
            await response(scope, receive, identified_send)
        finally:
            error_kind = error_kind or state.get("diagnostic_error")
            if status_code >= 500 and not error_kind:
                error_kind = "server_response"
            method = scope.get("method", "")
            if method not in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}:
                method = "OTHER"
            self.logger.log(
                logging.ERROR if error_kind or status_code >= 500 else logging.INFO,
                "http_request",
                extra={
                    "request_id": request_id, "method": method,
                    "route": getattr(scope.get("route"), "path", "<unmatched>"),
                    "status_code": status_code,
                    "duration_ms": round((time.monotonic() - started_at) * 1000, 2),
                    "error_kind": error_kind,
                },
            )
