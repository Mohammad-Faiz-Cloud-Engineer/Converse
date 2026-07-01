import pytest

from converse.models import (
    Config,
    LLMConfig,
    SafetyConfig,
    LLMResponse,
    RiskLevel,
    Provider,
)


class TestRiskLevel:
    def test_values(self):
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"
        assert len(set(RiskLevel)) == 4

    def test_all_defined(self):
        assert len(set(RiskLevel)) == 4


class TestProvider:
    def test_values(self):
        assert Provider.OLLAMA.value == "ollama"
        assert Provider.LMSTUDIO.value == "lmstudio"
        assert Provider.OPENAI.value == "openai"
        assert Provider.CUSTOM.value == "custom"
        assert len(set(Provider)) == 4


class TestLLMResponse:
    def test_from_json_valid(self):
        r = LLMResponse.from_json(
            '{"command": "ls", "explanation": "List files", '
            '"risk_level": "low", "requires_confirmation": false}'
        )
        assert r.command == "ls"
        assert r.explanation == "List files"
        assert r.risk_level == RiskLevel.LOW
        assert r.requires_confirmation is False
        assert r.error is None

    def test_from_json_with_error(self):
        r = LLMResponse.from_json(
            '{"command": "", "risk_level": "low", "error": "Ambiguous"}'
        )
        assert r.error == "Ambiguous"
        assert r.command == ""

    def test_from_json_invalid_json(self):
        r = LLMResponse.from_json("not valid json at all")
        assert r.error is not None
        assert "Failed to parse" in r.error

    def test_from_json_empty(self):
        r = LLMResponse.from_json("")
        assert r.error is not None

    def test_from_json_defaults(self):
        r = LLMResponse.from_json("{}")
        assert r.command == ""
        assert r.risk_level == RiskLevel.LOW
        assert r.requires_confirmation is False
        assert r.error is None

    def test_from_json_invalid_risk_level(self):
        r = LLMResponse.from_json(
            '{"command": "ls", "risk_level": "ultra"}'
        )
        assert r.risk_level == RiskLevel.LOW

    def test_from_json_missing_fields(self):
        r = LLMResponse.from_json(
            '{"command": "ls"}'
        )
        assert r.command == "ls"
        assert r.explanation == ""
        assert r.risk_level == RiskLevel.LOW
        assert r.requires_confirmation is False

    def test_from_json_requires_confirmation_coercion(self):
        r = LLMResponse.from_json(
            '{"command": "rm -rf /", "requires_confirmation": 1}'
        )
        assert r.requires_confirmation is True


class TestLLMConfig:
    def test_defaults(self):
        c = LLMConfig()
        assert c.provider == Provider.OLLAMA
        assert c.model == "llama3"
        assert c.base_url == "http://localhost:11434/v1"
        assert c.api_key == ""
        assert c.temperature == 0.1
        assert c.max_tokens == 500
        assert c.timeout == 30

    def test_custom_values(self):
        c = LLMConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            temperature=0.5,
            max_tokens=1000,
            timeout=60,
        )
        assert c.provider == Provider.OPENAI
        assert c.model == "gpt-4o"
        assert c.api_key == "sk-test"
        assert c.temperature == 0.5

    def test_empty_api_key(self):
        c = LLMConfig(api_key="")
        assert c.api_key == ""


class TestSafetyConfig:
    def test_defaults(self):
        s = SafetyConfig()
        assert s.require_confirmation == [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert s.blocked_commands == []
        assert not hasattr(s, "auto_confirm_low")

    def test_custom_confirmation_levels(self):
        s = SafetyConfig(
            require_confirmation=[RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        assert RiskLevel.LOW not in s.require_confirmation
        assert RiskLevel.MEDIUM in s.require_confirmation

    def test_blocked_commands(self):
        s = SafetyConfig(blocked_commands=["rm", "reboot"])
        assert "rm" in s.blocked_commands
        assert len(s.blocked_commands) == 2


class TestConfig:
    def test_defaults(self):
        c = Config()
        assert isinstance(c.llm, LLMConfig)
        assert isinstance(c.safety, SafetyConfig)
        assert c.dry_run is False
        assert c.auto_confirm is False
        assert c.no_stream is False

    def test_custom_values(self):
        c = Config(
            dry_run=True,
            auto_confirm=True,
            no_stream=True,
        )
        assert c.dry_run is True
        assert c.auto_confirm is True
        assert c.no_stream is True
