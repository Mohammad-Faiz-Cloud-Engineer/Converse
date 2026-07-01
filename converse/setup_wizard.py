from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich import box

from .models import Config, LLMConfig, SafetyConfig, Provider

console = Console()

HAS_TERMIOS = True
try:
    import termios
    import tty
except ImportError:
    HAS_TERMIOS = False


def _interactive_select(options: list[str], prompt: str = "Select an option:") -> str:
    n = len(options)
    if n == 0:
        return ""
    if n == 1:
        console.print(f"{prompt} {options[0]}")
        return options[0]

    if not HAS_TERMIOS:
        return _numbered_select(options, prompt)

    selected = 0
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        sys.stdout.write("\033[?25l")
        sys.stdout.write(f"{prompt}\n")

        def render():
            for i, opt in enumerate(options):
                prefix = ">" if i == selected else " "
                sys.stdout.write(f"\r{prefix} {opt}\033[K\n")
            sys.stdout.flush()

        render()

        while True:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = ch + sys.stdin.read(2)
                if seq == "\x1b[A":
                    selected = (selected - 1) % n
                elif seq == "\x1b[B":
                    selected = (selected + 1) % n
                sys.stdout.write(f"\033[{n}A\r")
                render()
            elif ch in ("\r", "\n"):
                break
            elif ch in ("\x03", "\x04"):
                raise KeyboardInterrupt
    finally:
        sys.stdout.write("\033[?25h")
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    sys.stdout.write(f"\033[{n + 1}A\r\033[J")
    sys.stdout.write(f"{prompt} {options[selected]}\n")
    sys.stdout.flush()

    return options[selected]


def _numbered_select(options: list[str], prompt: str = "Select an option:") -> str:
    console.print(prompt)
    for i, opt in enumerate(options):
        console.print(f"  [{i + 1}] {opt}")
    while True:
        try:
            choice = input(f"\nEnter number (1-{len(options)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                console.print(f"{prompt} {options[idx]}")
                return options[idx]
        except (ValueError, IndexError):
            pass
        except (EOFError, KeyboardInterrupt):
            print()
            raise


def _save_config(config: Config) -> Path:
    config_dir = Path.home() / ".config" / "converse"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"

    data = {
        "llm": {
            "provider": config.llm.provider.value,
            "model": config.llm.model,
            "base_url": config.llm.base_url,
            "api_key": config.llm.api_key,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
            "timeout": config.llm.timeout,
        },
        "safety": {
            "require_confirmation": [r.value for r in config.safety.require_confirmation],
            "blocked_commands": config.safety.blocked_commands,
        },
        "auto_confirm": config.auto_confirm,
    }

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)

    return config_path


def _prompt(label: str, default: str = "") -> str:
    val = input(f"{label} [{default}]: ").strip() if default else input(f"{label}: ").strip()
    return val if val else default


def run_setup_wizard() -> Config:
    console.print()
    console.print(
        Panel(
            "Welcome to [bold]converse[/] - Natural Language Shell!\n\n"
            "Let's get you set up with an LLM provider.\n"
            "Use arrow keys to navigate, Enter to select.",
            title="[bold]Setup Wizard[/]",
            border_style="green",
            box=box.DOUBLE,
        )
    )
    console.print()

    provider_options = [
        ("ollama", "Ollama (local)"),
        ("lmstudio", "LM Studio (local)"),
        ("openai", "OpenAI (cloud)"),
        ("custom", "Custom (OpenAI-compatible endpoint)"),
    ]

    labels = [label for _, label in provider_options]
    selected_label = _interactive_select(labels, prompt="Select your LLM provider:")
    provider_key = next(key for key, label in provider_options if label == selected_label)
    provider = Provider(provider_key)

    console.print()
    llm_config = LLMConfig(provider=provider)

    if provider == Provider.OLLAMA:
        url = _prompt("Ollama base URL", default=llm_config.base_url)
        model = _prompt("Model name", default=llm_config.model)
        llm_config.base_url = url
        llm_config.model = model

    elif provider == Provider.LMSTUDIO:
        url = _prompt("LM Studio base URL", default="http://localhost:1234/v1")
        model = _prompt("Model name (optional)", default="")
        llm_config.base_url = url
        if model:
            llm_config.model = model

    elif provider == Provider.OPENAI:
        api_key = _prompt("OpenAI API key")
        model = _prompt("Model", default="gpt-4o")
        llm_config.api_key = api_key
        llm_config.model = model
        llm_config.base_url = "https://api.openai.com/v1"

    elif provider == Provider.CUSTOM:
        url = _prompt("API base URL")
        if not url:
            console.print("[yellow]Warning:[/] No URL provided. Using default: http://localhost:11434/v1")
            console.print("[yellow]You can change it later in the config file.[/]")
        else:
            llm_config.base_url = url
        api_key = _prompt("API key (optional)", default="")
        model = _prompt("Model name (optional)", default="")
        llm_config.api_key = api_key
        if model:
            llm_config.model = model

    console.print()
    safety_config = SafetyConfig()

    auto_confirm_options = [
        "No - require confirmation for dangerous commands",
        "Yes - auto-confirm all (use with caution)",
    ]
    auto_confirm_label = _interactive_select(
        auto_confirm_options,
        prompt="Auto-confirm dangerous commands?",
    )
    auto_confirm = auto_confirm_label.startswith("Yes")

    config = Config(llm=llm_config, safety=safety_config, auto_confirm=auto_confirm)
    config_path = _save_config(config)

    console.print()
    console.print(
        Panel(
            f"[bold green]Setup complete![/]\n\n"
            f"  Provider:     {provider.value}\n"
            f"  Model:        {llm_config.model}\n"
            f"  Base URL:     {llm_config.base_url}\n"
            f"  Auto-confirm: {'Yes' if auto_confirm else 'No'}\n\n"
            f"Configuration saved to: [bold]{config_path}[/]",
            title="[bold]Success[/]",
            border_style="green",
        )
    )
    console.print()
    return config
