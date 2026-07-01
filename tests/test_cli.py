import sys
from argparse import Namespace

import pytest

from converse.models import Config, LLMConfig, RiskLevel, Provider


class TestLoadConfig:
    def test_default_config(self):
        from converse.cli import load_config
        args = Namespace(
            config=None, model=None, url=None, provider=None,
            api_key=None, temperature=None, max_tokens=None,
            timeout=None, dry_run=False, yes=None, no_stream=False,
        )
        config = load_config(args)
        assert isinstance(config, Config)
        assert config.llm.model == "llama3"
        assert config.llm.provider == Provider.OLLAMA
        assert config.dry_run is False
        assert config.auto_confirm is False
        assert config.no_stream is False

    def test_cli_overrides(self):
        from converse.cli import load_config
        args = Namespace(
            config=None,
            model="gpt-4o",
            url="https://api.openai.com/v1",
            provider="openai",
            api_key="sk-test",
            temperature=0.7,
            max_tokens=2000,
            timeout=60,
            dry_run=True,
            yes=True,
            no_stream=True,
        )
        config = load_config(args)
        assert config.llm.model == "gpt-4o"
        assert config.llm.base_url == "https://api.openai.com/v1"
        assert config.llm.provider == Provider.OPENAI
        assert config.llm.api_key == "sk-test"
        assert config.llm.temperature == 0.7
        assert config.llm.max_tokens == 2000
        assert config.llm.timeout == 60
        assert config.dry_run is True
        assert config.auto_confirm is True
        assert config.no_stream is True

    def test_safety_defaults(self):
        from converse.cli import load_config
        args = Namespace(
            config=None, model=None, url=None, provider=None,
            api_key=None, temperature=None, max_tokens=None,
            timeout=None, dry_run=False, yes=None, no_stream=False,
        )
        config = load_config(args)
        assert config.safety.require_confirmation == [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert config.safety.blocked_commands == []


class TestPrintFunctions:
    def test_print_info(self, capsys):
        from converse.cli import print_info
        print_info("test message")
        captured = capsys.readouterr()
        assert "INFO:" in captured.out
        assert "test message" in captured.out

    def test_print_success(self, capsys):
        from converse.cli import print_success
        print_success("done")
        captured = capsys.readouterr()
        assert "OK:" in captured.out

    def test_print_error(self, capsys):
        from converse.cli import print_error
        print_error("failed")
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out

    def test_print_warning(self, capsys):
        from converse.cli import print_warning
        print_warning("caution")
        captured = capsys.readouterr()
        assert "WARN:" in captured.out


class TestProcessQuery:
    def test_empty_query(self, capsys):
        from converse.cli import process_query
        config = Config(dry_run=True)
        process_query("", config)
        process_query("   ", config)
        captured = capsys.readouterr()
        assert captured.out.strip() == ""

    def test_llm_error_handling(self, capsys):
        from converse.cli import process_query
        config = Config(
            llm=LLMConfig(base_url="http://127.0.0.1:1/v1", timeout=5),
            dry_run=True,
        )
        process_query("list files", config)
        captured = capsys.readouterr()
        assert "Error:" in captured.out or "ERROR:" in captured.out

    def test_successful_query(self, mock_server, config, capsys):
        from converse.cli import process_query
        config.llm.base_url = f"http://127.0.0.1:{mock_server.port}/v1"
        config.dry_run = True
        process_query("list files", config)
        captured = capsys.readouterr()
        assert "ls -la" in captured.out

    def test_dry_run_skips_execution(self, mock_server, config, capsys):
        from converse.cli import process_query
        config.llm.base_url = f"http://127.0.0.1:{mock_server.port}/v1"
        config.dry_run = True
        process_query("list files", config)
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out

    def test_high_risk_shows_confirmation_label(self, mock_high_server, config, capsys):
        from converse.cli import process_query
        config.llm.base_url = f"http://127.0.0.1:{mock_high_server.port}/v1"
        config.auto_confirm = False
        config.dry_run = True
        process_query("delete temp", config)
        captured = capsys.readouterr()
        assert "requires confirmation" in captured.out
        assert "rm -rf /tmp/x" in captured.out

    def test_ambiguous_query(self, mock_ambiguous_server, config, capsys):
        from converse.cli import process_query
        config.llm.base_url = f"http://127.0.0.1:{mock_ambiguous_server.port}/v1"
        process_query("do something", config)
        captured = capsys.readouterr()
        assert "Ambiguous" in captured.out or "ERROR" in captured.out


class TestMain:
    def test_version_flag(self, capsys):
        from converse.cli import main
        from converse import __version__
        old_argv = sys.argv
        try:
            sys.argv = ["converse", "--version"]
            main()
        except SystemExit:
            pass
        finally:
            sys.argv = old_argv
        captured = capsys.readouterr()
        assert f"converse v{__version__}" in captured.out
