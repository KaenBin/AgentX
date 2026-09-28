"""Real loopback HTTP regression tests for authenticated gateway redirects."""

import json
import threading
import traceback
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Running this module alone must not read the developer's real .env.
with patch("dotenv.load_dotenv"):
    from src.agents.worker import GatewayError, GatewayWorker
    from src.core.config import Settings


FAKE_TOKEN = "fictional-redirect-test-token"
PRIVATE_DETAIL = "fictional-private-upstream-detail"


@contextmanager
def local_server(status, body, *, location=None):
    calls = []
    errors = []

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(2)
            super().setup()

        def log_message(self, *args):
            pass

        def respond(self):
            try:
                payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                calls.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "headers": {key.lower(): value for key, value in self.headers.items()},
                        "body": payload,
                    }
                )
                # Include private data in the upstream error, not just its body.
                self.send_response(status, PRIVATE_DETAIL)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                if location is not None:
                    self.send_header("Location", location)
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # The client may close as soon as it rejects the redirect headers.
                pass
            except Exception as exc:
                errors.append(exc)

        do_POST = respond
        do_GET = respond

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.block_on_close = False
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    try:
        yield SimpleNamespace(
            url=f"http://127.0.0.1:{server.server_port}", calls=calls
        )
    finally:
        # Bound teardown even if the server loop unexpectedly stops responding.
        shutdown = threading.Thread(target=server.shutdown, daemon=True)
        shutdown.start()
        shutdown.join(timeout=2)
        server.server_close()
        thread.join(timeout=2)
        assert not shutdown.is_alive(), "Loopback server shutdown timed out"
        assert not thread.is_alive(), "Loopback server thread did not stop"
        assert not errors, "Loopback fixture failed while handling an HTTP request"


@pytest.mark.parametrize("protocol", ["ollama", "openclaw"])
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_gateway_never_follows_authenticated_redirects(
    protocol, status, monkeypatch, tmp_path, capsys
):
    # Disable proxy discovery only; exercise the real worker opener and HTTP stack.
    # On Windows this also prevents fallback to proxy settings in the registry.
    monkeypatch.setattr("urllib.request.getproxies", lambda: {})
    message = {"content": "Redirects must never reach this successful response"}
    receiver_body = json.dumps(
        {"message": message, "choices": [{"message": message, "finish_reason": "stop"}]}
    ).encode()

    with local_server(200, receiver_body) as receiver:
        destination = receiver.url + "/redirected/" + FAKE_TOKEN
        error_body = json.dumps({"error": PRIVATE_DETAIL, "token": FAKE_TOKEN}).encode()
        with local_server(status, error_body, location=destination) as origin:
            settings = Settings(
                mode="gateway",
                gateway_protocol=protocol,
                gateway_url=origin.url,
                gateway_api_key=FAKE_TOKEN,
                model="openclaw/agentx-training" if protocol == "openclaw" else "sonnet",
                database_path=tmp_path / "unused-settings.db",
            )
            with pytest.raises(GatewayError, match="usable response") as caught:
                GatewayWorker(settings).chat(
                    [{"role": "user", "content": "Synthetic local redirect probe"}]
                )

            assert len(origin.calls) == 1
            request = origin.calls[0]
            assert request["method"] == "POST"
            assert request["path"] == (
                "/v1/chat/completions" if protocol == "openclaw" else "/api/chat"
            )
            assert request["headers"].get("authorization") == (
                "Bearer " + FAKE_TOKEN if protocol == "openclaw" else None
            )
            assert request["headers"].get("x-api-key") == (
                FAKE_TOKEN if protocol == "ollama" else None
            )
            assert receiver.calls == [], "A redirect forwarded a request to another port"

            formatted_error = "".join(traceback.format_exception(caught.value))
            for sensitive_value in (FAKE_TOKEN, PRIVATE_DETAIL, origin.url, destination):
                assert sensitive_value not in str(caught.value)
                assert sensitive_value not in formatted_error
            assert caught.value.__cause__ is None
            assert caught.value.__suppress_context__ is True

    output = capsys.readouterr()
    assert output.out == output.err == ""
