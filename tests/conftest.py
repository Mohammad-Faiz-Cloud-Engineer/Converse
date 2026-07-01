import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest

from converse.models import Config, LLMConfig


MOCK_LS_RESPONSE = json.dumps({
    "command": "ls -la",
    "explanation": "List all files including hidden ones",
    "risk_level": "low",
    "requires_confirmation": False,
    "error": None,
})

MOCK_HIGH_RESPONSE = json.dumps({
    "command": "rm -rf /tmp/x",
    "explanation": "Permanently delete /tmp/x",
    "risk_level": "high",
    "requires_confirmation": True,
    "error": None,
})

MOCK_AMBIGUOUS_RESPONSE = json.dumps({
    "command": "",
    "explanation": "",
    "risk_level": "low",
    "requires_confirmation": False,
    "error": "Ambiguous request. Please specify a target.",
})


class MockLLMHandler(BaseHTTPRequestHandler):
    """HTTP handler that simulates an OpenAI-compatible LLM API."""

    response_data = MOCK_LS_RESPONSE

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body)
        is_stream = data.get("stream", False)

        if is_stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for char in self.response_data:
                chunk = json.dumps({"choices": [{"delta": {"content": char}}]})
                self.wfile.write(f"data: {chunk}\n\n".encode())
                self.wfile.flush()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = json.dumps({"choices": [{"message": {"content": self.response_data}}]})
            self.wfile.write(resp.encode())

    def log_message(self, format, *args):
        pass


class MockHighHandler(MockLLMHandler):
    response_data = MOCK_HIGH_RESPONSE


class MockAmbiguousHandler(MockLLMHandler):
    response_data = MOCK_AMBIGUOUS_RESPONSE


class MockServer:
    """Context manager for a mock LLM API server."""

    def __init__(self, handler_class=MockLLMHandler, port=0):
        self.server = HTTPServer(("127.0.0.1", port), handler_class)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.thread.join(timeout=2)


@pytest.fixture
def mock_server():
    with MockServer() as server:
        yield server


@pytest.fixture
def mock_high_server():
    with MockServer(MockHighHandler) as server:
        yield server


@pytest.fixture
def mock_ambiguous_server():
    with MockServer(MockAmbiguousHandler) as server:
        yield server


@pytest.fixture
def config(mock_server):
    return Config(
        llm=LLMConfig(
            base_url=f"http://127.0.0.1:{mock_server.port}/v1",
            model="mock-model",
        ),
        dry_run=False,
        auto_confirm=True,
        no_stream=True,
    )


@pytest.fixture
def safe_config(config):
    config.dry_run = True
    return config
