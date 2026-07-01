import pytest

from converse.translator import parse_response, _build_messages
from converse.models import LLMResponse, RiskLevel


class TestParseResponse:
    def test_valid_json(self):
        r = parse_response(
            '{"command": "ls -la", "explanation": "List files", '
            '"risk_level": "low", "requires_confirmation": false}'
        )
        assert r.command == "ls -la"
        assert r.risk_level == RiskLevel.LOW
        assert r.error is None

    def test_json_with_error(self):
        r = parse_response(
            '{"command": "", "risk_level": "low", "error": "Ambiguous"}'
        )
        assert r.error == "Ambiguous"

    def test_invalid_json(self):
        r = parse_response("this is not json at all")
        assert r.error is not None

    def test_json_in_code_fence_json(self):
        r = parse_response(
            '```json\n{"command": "mkdir test"}\n```'
        )
        assert r.command == "mkdir test"
        assert r.error is None

    def test_json_in_generic_code_fence(self):
        r = parse_response(
            '```\n{"command": "echo hello"}\n```'
        )
        assert r.command == "echo hello"

    def test_json_with_extra_text_before(self):
        r = parse_response(
            'Here is the command:\n{"command": "ls -la"}'
        )
        assert r.command == "ls -la"

    def test_json_with_extra_text_after(self):
        r = parse_response(
            '{"command": "pwd"}\nThis will show the current directory.'
        )
        assert r.command == "pwd"

    def test_empty_string(self):
        r = parse_response("")
        assert r.error is not None

    def test_only_brackets(self):
        r = parse_response("{}")
        assert r.command == ""

    def test_multiple_json_objects(self):
        r = parse_response(
            '{"command": "ls"}{"command": "pwd"}'
        )
        assert r.error is not None  # multiple objects is not valid JSON

    def test_code_fence_without_json_inside(self):
        r = parse_response("```\njust text\n```")
        assert r.error is not None

    def test_nested_braces(self):
        r = parse_response(
            '{"command": "echo {nested}", "explanation": "test"}'
        )
        assert r.command == "echo {nested}"


class TestBuildMessages:
    def test_contains_system_and_user_roles(self):
        messages = _build_messages("list files")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_user_message_contains_query(self):
        messages = _build_messages("list files")
        assert "list files" in messages[1]["content"]

    def test_user_message_contains_cwd(self):
        import os
        messages = _build_messages("test")
        assert os.getcwd() in messages[1]["content"]

    def test_user_message_contains_os(self):
        import platform
        messages = _build_messages("test")
        assert platform.system() in messages[1]["content"]
