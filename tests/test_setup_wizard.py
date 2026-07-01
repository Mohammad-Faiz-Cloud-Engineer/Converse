import json
from pathlib import Path

import pytest

from converse.models import Config, LLMConfig, Provider


class TestSaveConfig:
    def test_saves_to_home_config_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from converse.setup_wizard import _save_config

        config = Config(
            llm=LLMConfig(
                provider=Provider.OLLAMA,
                model="llama3",
                base_url="http://localhost:11434/v1",
            ),
        )
        result = _save_config(config)

        expected_path = tmp_path / ".config" / "converse" / "config.json"
        assert result == expected_path
        assert expected_path.exists()

        with open(expected_path) as f:
            data = json.load(f)

        assert data["llm"]["provider"] == "ollama"
        assert data["llm"]["model"] == "llama3"
        assert data["llm"]["base_url"] == "http://localhost:11434/v1"
        assert data["safety"]["require_confirmation"] == ["high", "critical"]
        assert data["safety"]["blocked_commands"] == []
        assert data["auto_confirm"] is False

    def test_saves_openai_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from converse.setup_wizard import _save_config

        config = Config(
            llm=LLMConfig(
                provider=Provider.OPENAI,
                model="gpt-4o",
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            ),
            auto_confirm=True,
        )
        result = _save_config(config)

        with open(result) as f:
            data = json.load(f)

        assert data["llm"]["provider"] == "openai"
        assert data["llm"]["api_key"] == "sk-test"
        assert data["auto_confirm"] is True

    def test_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from converse.setup_wizard import _save_config

        config = Config()
        result = _save_config(config)

        assert result.parent.exists()
        assert result.exists()


class TestNumberedSelect:
    def test_selects_by_number(self, monkeypatch):
        from converse.setup_wizard import _numbered_select

        monkeypatch.setattr("builtins.input", lambda _: "2")
        result = _numbered_select(["opt1", "opt2", "opt3"])
        assert result == "opt2"

    def test_retries_on_invalid_input(self, monkeypatch):
        from converse.setup_wizard import _numbered_select

        inputs = iter(["abc", "0", "99", "1"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        result = _numbered_select(["first", "second"])
        assert result == "first"

    def test_raises_on_eof(self, monkeypatch):
        from converse.setup_wizard import _numbered_select

        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError()))
        with pytest.raises(EOFError):
            _numbered_select(["a", "b"])

    def test_raises_on_keyboard_interrupt(self, monkeypatch):
        from converse.setup_wizard import _numbered_select

        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
        with pytest.raises(KeyboardInterrupt):
            _numbered_select(["a", "b"])


class TestInteractiveSelect:
    def test_fallback_to_numbered_on_no_termios(self, monkeypatch):
        from converse.setup_wizard import _interactive_select, _numbered_select

        original_has = False
        monkeypatch.setattr("converse.setup_wizard.HAS_TERMIOS", False)
        monkeypatch.setattr("converse.setup_wizard._numbered_select", lambda opts, prompt="": "fallback_ok")

        result = _interactive_select(["a", "b"], prompt="Pick:")
        assert result == "fallback_ok"

    def test_empty_options(self):
        from converse.setup_wizard import _interactive_select

        assert _interactive_select([], "prompt") == ""

    def test_single_option(self, capsys):
        from converse.setup_wizard import _interactive_select

        result = _interactive_select(["only"], "Pick:")
        assert result == "only"
        captured = capsys.readouterr()
        assert "only" in captured.out


class TestPrompt:
    def test_prompt_with_default(self, monkeypatch):
        from converse.setup_wizard import _prompt

        monkeypatch.setattr("builtins.input", lambda _: "")
        result = _prompt("Enter value", default="default_val")
        assert result == "default_val"

    def test_prompt_without_default(self, monkeypatch):
        from converse.setup_wizard import _prompt

        monkeypatch.setattr("builtins.input", lambda _: "user_input")
        result = _prompt("Enter value")
        assert result == "user_input"

    def test_prompt_overrides_default(self, monkeypatch):
        from converse.setup_wizard import _prompt

        monkeypatch.setattr("builtins.input", lambda _: "custom")
        result = _prompt("Enter value", default="default_val")
        assert result == "custom"


class TestRunSetupWizard:
    def test_runs_full_wizard_openai(self, monkeypatch, tmp_path):
        from converse.setup_wizard import run_setup_wizard

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr("converse.setup_wizard.HAS_TERMIOS", False)

        inputs = iter([
            "4",
            "http://localhost:8080/v1",
            "sk-test-123",
            "gpt-4o",
            "1",
        ])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        config = run_setup_wizard()

        assert config.llm.provider == Provider.CUSTOM
        assert config.llm.base_url == "http://localhost:8080/v1"
        assert config.llm.api_key == "sk-test-123"
        assert config.llm.model == "gpt-4o"
        assert config.auto_confirm is False

    def test_runs_full_wizard_ollama(self, monkeypatch, tmp_path):
        from converse.setup_wizard import run_setup_wizard

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setattr("converse.setup_wizard.HAS_TERMIOS", False)

        inputs = iter([
            "1",
            "",
            "",
            "2",
        ])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        config = run_setup_wizard()

        assert config.llm.provider == Provider.OLLAMA
        assert config.llm.base_url == "http://localhost:11434/v1"
        assert config.llm.model == "llama3"
        assert config.auto_confirm is True
