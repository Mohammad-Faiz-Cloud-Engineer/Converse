import json
import pytest

from converse.models import LLMConfig, Provider


class TestLLMClient:
    def test_headers_with_api_key(self):
        from converse.llm import _build_headers
        config = LLMConfig(api_key="sk-test")
        headers = _build_headers(config)
        assert headers["Authorization"] == "Bearer sk-test"
        assert headers["Content-Type"] == "application/json"

    def test_headers_without_api_key(self):
        from converse.llm import _build_headers
        config = LLMConfig(api_key="")
        headers = _build_headers(config)
        assert "Authorization" not in headers

    def test_payload_structure(self):
        from converse.llm import _build_payload
        messages = [{"role": "user", "content": "hello"}]
        config = LLMConfig(model="gpt-4o", temperature=0.5, max_tokens=200)
        payload = _build_payload(config, messages, stream=True)

        assert payload["model"] == "gpt-4o"
        assert payload["messages"] == messages
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 200
        assert payload["stream"] is True

    def test_payload_default_stream(self):
        from converse.llm import _build_payload
        config = LLMConfig()
        payload = _build_payload(config, [{"role": "user", "content": "hi"}], stream=False)
        assert payload["stream"] is False

    def test_complete_success(self, mock_server, config):
        from converse.llm import complete
        config.llm.base_url = f"http://127.0.0.1:{mock_server.port}/v1"
        response = complete(config.llm, [
            {"role": "user", "content": "list files"}
        ])
        parsed = json.loads(response)
        assert parsed["command"] == "ls -la"
        assert parsed["risk_level"] == "low"

    def test_complete_connection_error(self):
        from converse.llm import complete
        config = LLMConfig(base_url="http://127.0.0.1:1/v1", timeout=5)
        response = complete(config, [{"role": "user", "content": "test"}])
        assert "Error:" in response

    def test_stream_completion_success(self, mock_server, config):
        from converse.llm import stream_completion
        config.llm.base_url = f"http://127.0.0.1:{mock_server.port}/v1"
        tokens = list(stream_completion(config.llm, [
            {"role": "user", "content": "list files"}
        ]))
        full = "".join(tokens)
        parsed = json.loads(full)
        assert parsed["command"] == "ls -la"

    def test_stream_completion_connection_error(self):
        from converse.llm import stream_completion
        config = LLMConfig(base_url="http://127.0.0.1:1/v1", timeout=5)
        tokens = list(stream_completion(config, [
            {"role": "user", "content": "test"}
        ]))
        assert any("Error:" in t for t in tokens)
