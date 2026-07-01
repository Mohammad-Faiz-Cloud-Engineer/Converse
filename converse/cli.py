from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich import box

from .models import (
    Config,
    LLMConfig,
    SafetyConfig,
    LLMResponse,
    RiskLevel,
    Provider,
)
from .translator import translate, parse_response
from .executor import determine_risk_level, check_blocked, run_command

console = Console()

CONFIG_SEARCH_PATHS = [
    Path.cwd() / "converse.yaml",
    Path.cwd() / "converse.json",
    Path.home() / ".config" / "converse" / "config.yaml",
    Path.home() / ".config" / "converse" / "config.json",
    Path.home() / ".converse.yaml",
    Path.home() / ".converse.json",
]


def config_exists() -> bool:
    return any(p.exists() for p in CONFIG_SEARCH_PATHS)


def print_info(msg: str) -> None:
    console.print(f"[bold blue]INFO:[/] {msg}")


def print_success(msg: str) -> None:
    console.print(f"[bold green]OK:[/] {msg}")


def print_warning(msg: str) -> None:
    console.print(f"[bold yellow]WARN:[/] {msg}")


def print_error(msg: str) -> None:
    console.print(f"[bold red]ERROR:[/] {msg}")


def print_risk_banner(command: str, explanation: str, risk: str) -> None:
    color = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }.get(risk, "white")

    panel = Panel(
        f"[{color}]{explanation}[/]\n\n"
        f"[{color}]Command:[/] [bold white]{command}[/]\n"
        f"[{color}]Risk Level:[/] [bold {color}]{risk.upper()}[/]",
        title="[bold yellow]SAFETY CONFIRMATION REQUIRED[/]",
        border_style=color,
        box=box.HEAVY,
    )
    console.print(panel)


def print_result(response: LLMResponse) -> None:
    color = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }.get(response.risk_level.value, "white")

    panel = Panel(
        f"Command:  [bold white]{response.command}[/]\n"
        f"Task:     {response.explanation}\n"
        f"Risk:     [{color}]{response.risk_level.value.upper()}[/]"
        f"{'  [yellow](requires confirmation)[/]' if response.requires_confirmation else ''}",
        title="[bold]converse translation result[/]",
        border_style="cyan",
        box=box.ROUNDED,
    )
    console.print(panel)


def load_config(args: argparse.Namespace) -> Config:
    """Load configuration from file, CLI args, and environment."""
    config = Config()

    config_paths = list(CONFIG_SEARCH_PATHS)

    if args.config:
        config_paths.insert(0, Path(args.config))

    for cp in config_paths:
        if cp.exists():
            try:
                if cp.suffix in (".yaml", ".yml"):
                    try:
                        import yaml
                        with open(cp) as f:
                            data = yaml.safe_load(f)
                    except ImportError:
                        print_warning(
                            "PyYAML not installed. Install with: pip install pyyaml"
                        )
                        continue
                else:
                    import json
                    with open(cp) as f:
                        data = json.load(f)

                if data:
                    llm_data = data.get("llm", {})
                    if "provider" in llm_data:
                        config.llm.provider = Provider(llm_data["provider"])
                    if "model" in llm_data:
                        config.llm.model = llm_data["model"]
                    if "base_url" in llm_data:
                        config.llm.base_url = llm_data["base_url"]
                    if "api_key" in llm_data:
                        config.llm.api_key = llm_data["api_key"]
                    if "temperature" in llm_data:
                        config.llm.temperature = float(llm_data["temperature"])
                    if "max_tokens" in llm_data:
                        config.llm.max_tokens = int(llm_data["max_tokens"])
                    if "timeout" in llm_data:
                        config.llm.timeout = int(llm_data["timeout"])

                    safety_data = data.get("safety", {})
                    if "require_confirmation" in safety_data:
                        config.safety.require_confirmation = [
                            RiskLevel(r) for r in safety_data["require_confirmation"]
                        ]
                    if "blocked_commands" in safety_data:
                        config.safety.blocked_commands = list(safety_data["blocked_commands"])

                    if "auto_confirm" in data:
                        config.auto_confirm = bool(data["auto_confirm"])

                print_info(f"Loaded config from {cp}")
                break
            except Exception as e:
                print_warning(f"Failed to load config from {cp}: {e}")

    # Environment variable overrides
    env_map = {
        "CONVERSE_PROVIDER": ("llm", "provider", lambda v: Provider(v)),
        "CONVERSE_MODEL": ("llm", "model", lambda v: v),
        "CONVERSE_BASE_URL": ("llm", "base_url", lambda v: v),
        "CONVERSE_API_KEY": ("llm", "api_key", lambda v: v),
        "CONVERSE_TEMPERATURE": ("llm", "temperature", lambda v: float(v)),
        "CONVERSE_MAX_TOKENS": ("llm", "max_tokens", lambda v: int(v)),
        "CONVERSE_TIMEOUT": ("llm", "timeout", lambda v: int(v)),
        "CONVERSE_BLOCKED": ("safety", "blocked_commands", lambda v: v.split(",")),
    }

    for env_key, (section, attr, transform) in env_map.items():
        val = os.environ.get(env_key)
        if val:
            try:
                section_obj = getattr(config, section)
                setattr(section_obj, attr, transform(val))
            except Exception as e:
                print_warning(f"Failed to parse {env_key}={val}: {e}")

    # CLI argument overrides
    if args.model:
        config.llm.model = args.model
    if args.url:
        config.llm.base_url = args.url
    if args.provider:
        config.llm.provider = Provider(args.provider)
    if args.api_key:
        config.llm.api_key = args.api_key
    if args.temperature is not None:
        config.llm.temperature = args.temperature
    if args.max_tokens is not None:
        config.llm.max_tokens = args.max_tokens
    if args.timeout is not None:
        config.llm.timeout = args.timeout

    config.dry_run = args.dry_run
    if args.yes is not None:
        config.auto_confirm = args.yes
    config.no_stream = args.no_stream

    return config


def process_query(query: str, config: Config) -> None:
    """Process a single natural language query through the full pipeline."""
    if not query or not query.strip():
        return

    console.print(f"\n[bold]Query:[/] {query}")

    # Step 1: Translate with streaming
    with Live(
        Panel("[dim]Translating...[/]", title="converse", border_style="cyan"),
        console=console,
        refresh_per_second=10,
        transient=True,
    ) as live:
        collected: list[str] = []
        for token in translate(query, config.llm, stream=not config.no_stream):
            collected.append(token)
            if not config.no_stream:
                current = "".join(collected)
                display = current[-800:] if len(current) > 800 else current
                live.update(
                    Panel(
                        f"[dim]{display}[/]",
                        title="[bold]Translating...[/]",
                        border_style="cyan",
                    )
                )

    response_text = "".join(collected)

    # Step 2: Check for LLM-level errors before parsing
    if response_text.strip().startswith("Error:"):
        for line in response_text.strip().split("\n"):
            print_error(line)
        return

    # Step 3: Parse
    response = parse_response(response_text)

    if response.error:
        print_error(response.error)
        if response_text.strip():
            print_info(f"Raw response: {response_text.strip()[:500]}")
        return

    if not response.command:
        print_error("No command to execute.")
        return

    # Step 4: Enrich local risk assessment (safety net)
    local_risk = determine_risk_level(response.command)
    risk_priority = {
        RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3,
    }
    if risk_priority.get(local_risk, 0) > risk_priority.get(response.risk_level, 0):
        response.risk_level = local_risk

    if response.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        response.requires_confirmation = True

    # Step 5: Check blocked commands
    blocked = check_blocked(response.command, config.safety.blocked_commands)
    if blocked:
        print_error(blocked)
        return

    # Step 6: Display result
    print_result(response)

    if config.dry_run:
        print_info("[DRY RUN] Execution skipped.")
        return

    # Step 7: Confirmation
    needs_confirm = (
        response.requires_confirmation
        and response.risk_level in config.safety.require_confirmation
    )

    if needs_confirm and config.auto_confirm:
        print_warning("Auto-confirm enabled. Executing without confirmation prompt.")
        needs_confirm = False

    if needs_confirm:
        print_risk_banner(response.command, response.explanation, response.risk_level.value)
        try:
            confirm = input("\nProceed with execution? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            print_info("Execution cancelled.")
            return

        if confirm not in ("y", "yes"):
            print_info("Execution cancelled.")
            return

    # Step 8: Execute
    print()
    print_success(f"Executing: {response.command}")
    console.print("─" * 60)

    try:
        result = run_command(response.command)
    except Exception as e:
        print_error(f"Execution failed: {e}")
        return

    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        console.print(f"[red]{result.stderr}[/]")
    console.print("─" * 60)
    if result.returncode == 0:
        print_success(f"Completed (exit code: {result.returncode})")
    else:
        print_error(f"Failed (exit code: {result.returncode})")


def interactive_mode(config: Config) -> None:
    """Run the interactive REPL."""
    try:
        import readline
        histfile = Path.home() / ".converse_history"
        try:
            readline.read_history_file(str(histfile))
        except (FileNotFoundError, OSError):
            pass
        readline.set_history_length(500)
    except ImportError:
        readline = None

    cwd = os.getcwd()
    console.print(
        Panel(
            "Type natural language commands or 'exit' / 'quit' to leave.\n"
            "Press Ctrl+D or Ctrl+C to exit at any time.",
            title="[bold]converse - Natural Language Shell[/]",
            border_style="green",
            box=box.DOUBLE,
        )
    )

    while True:
        try:
            query = input(f"\nconverse [{cwd}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print_info("Exiting.")
            break

        if not query:
            continue

        if query.lower() in ("exit", "quit", "q"):
            print_info("Exiting.")
            break

        # Check for special commands
        if query.startswith("!"):
            raw_cmd = query[1:].strip()
            if raw_cmd:
                print_success(f"Executing raw: {raw_cmd}")
                console.print("─" * 60)
                try:
                    result = run_command(raw_cmd)
                    if result.stdout:
                        console.print(result.stdout)
                    if result.stderr:
                        console.print(f"[red]{result.stderr}[/]")
                except Exception as e:
                    print_error(f"Execution failed: {e}")
                console.print("─" * 60)
            continue

        process_query(query, config)

    if readline:
        try:
            readline.write_history_file(str(histfile))
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="converse - Natural Language Shell. Execute system commands using plain English.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  converse "create a folder named test"
  converse "show me all files in the current directory"
  converse "delete the file old_report.txt" --dry-run
  converse --interactive
  converse -m llama3 -u http://localhost:11434/v1 "list running processes"
  echo "restart my computer" | converse -n

Configuration file (searched in order):
  ./converse.yaml, ~/.config/converse/config.yaml, ~/.converse.yaml
  Same paths with .json extension.

Environment variables:
    CONVERSE_MODEL, CONVERSE_BASE_URL, CONVERSE_API_KEY, CONVERSE_PROVIDER,
    CONVERSE_TEMPERATURE, CONVERSE_MAX_TOKENS, CONVERSE_TIMEOUT, CONVERSE_BLOCKED
        """,
    )
    parser.add_argument("query", nargs="*", help="Natural language command to execute")
    parser.add_argument("-c", "--config", help="Path to configuration file")
    parser.add_argument("-m", "--model", help="LLM model name (default: llama3)")
    parser.add_argument("-u", "--url", help="LLM API base URL (default: http://localhost:11434/v1)")
    parser.add_argument("-p", "--provider", choices=[p.value for p in Provider], help="LLM provider")
    parser.add_argument("-k", "--api-key", help="API key for the LLM provider")
    parser.add_argument("-t", "--temperature", type=float, help="LLM temperature (default: 0.1)")
    parser.add_argument("--max-tokens", type=int, help="Maximum response tokens (default: 500)")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds (default: 30)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Show translation without executing")
    parser.add_argument("-y", "--yes", action="store_true", default=None, help="Auto-confirm all prompts (use with caution)")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming output")
    parser.add_argument("-i", "--interactive", action="store_true", help="Force interactive mode")
    parser.add_argument("--setup", action="store_true", help="Run the interactive setup wizard")
    parser.add_argument("--version", action="store_true", help="Show version and exit")

    args = parser.parse_args()

    if args.version:
        from . import __version__
        print(f"converse v{__version__}")
        return

    if args.setup:
        from .setup_wizard import run_setup_wizard
        try:
            run_setup_wizard()
        except (EOFError, KeyboardInterrupt):
            print()
            print_info("Setup cancelled.")
        return

    config = load_config(args)

    is_interactive = args.interactive or (not args.query and sys.stdin.isatty())

    if is_interactive and not config_exists() and not args.config:
        console.print()
        console.print("[dim]No configuration found. Starting setup wizard...[/]")
        console.print()
        from .setup_wizard import run_setup_wizard
        try:
            run_setup_wizard()
        except (EOFError, KeyboardInterrupt):
            print()
            print_info("Setup cancelled. Using default configuration.")
        config = load_config(args)

    if is_interactive:
        interactive_mode(config)
    elif args.query:
        query = " ".join(args.query)
        process_query(query, config)
    elif not sys.stdin.isatty():
        query = sys.stdin.read().strip()
        if query:
            process_query(query, config)
        else:
            print_error("No input provided.")
            parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
