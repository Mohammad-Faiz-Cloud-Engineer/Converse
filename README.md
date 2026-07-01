# Converse

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-BSD--2--Clause-blue" alt="License"></a>
  <a href="https://github.com/Akshay-Cloud-Engineer/converse/actions"><img src="https://img.shields.io/github/actions/workflow/status/Akshay-Cloud-Engineer/converse/ci.yml?branch=main&label=CI" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue" alt="Python">
  <img src="https://img.shields.io/badge/tests-152-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/lines%20of%20code-1569-brightgreen" alt="Lines of Code">
</p>

Tell converse what you want in plain English and it figures out the shell command, shows you what it's going to run, and executes it.

```bash
converse "show me all files including hidden ones"
converse "find all Python files modified in the last week"
converse "create a folder named project and move everything there"
```

Works with local LLMs (Ollama, LM Studio) or any OpenAI-compatible API. Commands stream back in real time so you can see the translation as the model generates it.

## How it works

You type a sentence. converse sends it to the language model along with your current directory and operating system, so the model has context for paths and platform-specific commands. The model replies with structured JSON containing the shell command, an explanation, and a risk level. converse runs its own safety checks on top. Pattern matching catches destructive operations even if the model underestimates the risk. If everything looks good and you confirm (when needed), it runs the command.

## Features

- **Multiple providers** - Ollama, LM Studio, OpenAI, or any custom endpoint
- **Streaming** - see the command being built character by character
- **Two-layer safety** - LLM risk assessment + local pattern matching; the stricter wins
- **Confirmation prompts** - high-risk commands ask before executing
- **Risk levels** - Low, Medium, High, Critical with configurable thresholds
- **Blocked commands** - blacklist specific commands so they can never run
- **Dry-run mode** - preview without executing (`--dry-run` / `-n`)
- **Interactive REPL** - keep asking without restarting (`converse` with no query)
- **Raw shell passthrough** - `!command` in the REPL skips the LLM entirely
- **Direct execution** - `--exec` / `-x` runs a raw command directly from the CLI, no LLM involved
- **Configurable** - YAML, JSON, environment variables, or CLI flags
- **Setup wizard** - guided configuration with `--setup` (never auto-runs)
- **Cross-platform** - Windows, Linux, macOS

## Installation

### Option 1: pip install (global)

Install directly from GitHub (no clone needed):

```bash
pip install git+https://github.com/Akshay-Cloud-Engineer/converse.git
```

After this, `converse` should be on your PATH. If it isn't, use the module form:

```bash
# Windows
python -m converse "query"

# Linux / macOS
python3 -m converse "query"
```

### Option 2: pip install (local / editable)

Clone the repo and install for development:

```bash
git clone https://github.com/Akshay-Cloud-Engineer/converse.git
cd converse
pip install -e .
```

Editable mode (`-e`) means changes to the source code take effect immediately without reinstalling. Use this if you plan to modify the code.

### Option 3: git clone without pip

Clone and run directly through `python -m`:

```bash
git clone https://github.com/Akshay-Cloud-Engineer/converse.git
cd converse
```

Then install the dependencies and use the module form:

**Windows (PowerShell / cmd):**
```bash
pip install httpx rich
python -m converse "list all files"
python -m converse --setup
```

**Linux / macOS:**
```bash
pip3 install httpx rich
python3 -m converse "list all files"
python3 -m converse --setup
```

### Option 4: Manual dependency install

If you cloned the repo and want to run `python -m converse` without a full pip install, just install the runtime dependencies directly:

```bash
pip install rich httpx
```

Now run via the module form:

```bash
# Windows
python -m converse "query"

# Linux / macOS
python3 -m converse "query"
```

### Optional dependencies

```bash
# YAML config support (without it, only JSON configs are loaded)
pip install pyyaml

# Development (tests)
pip install pytest
```

## Quick start

### 1. Get an LLM running

The easiest way is with Ollama:

```bash
ollama pull llama3.2
ollama serve
```

Or use any OpenAI-compatible provider: LM Studio, OpenAI, or a custom endpoint.

### 2. Run the setup wizard

```bash
converse --setup
```

If `converse` isn't on PATH:

```bash
# Windows
python -m converse --setup

# Linux / macOS
python3 -m converse --setup
```

The wizard walks you through provider selection, API details, and safety preferences, then saves the config to `~/.config/converse/config.json`.

The setup wizard only runs when invoked with `--setup`. It never runs automatically.

### 3. Use it

Single command:

```bash
converse "show me disk usage"
converse "find all large files over 100MB"
```

Interactive REPL (type multiple commands in a session):

```bash
converse
```

Without arguments, converse drops into interactive mode. Type natural language queries, `!raw_command` to run shell commands directly, or `exit` / `quit` to leave.

Dry run: see what would run without actually executing:

```bash
converse "delete temporary files" --dry-run
```

Direct execution (bypass the LLM entirely):

```bash
converse -x "ls -la"
converse -x "docker ps"
converse -x "cat /etc/os-release"
```

---

## Safety

Every command passes through two layers of risk assessment:

1. **LLM assessment** - the model classifies risk as Low, Medium, High, or Critical
2. **Local pattern matching** - converse scans the command for dangerous patterns and can override the model's assessment to a higher level

The stricter assessment wins.

**Low** - `ls`, `pwd`, `echo`, `cat`, `grep`, `find`, `df`, `ps`, `git status`, read-only operations. No confirmation needed.

**Medium** - `mkdir`, `touch`, `cp`, `mv`, `curl`, `wget`, `pip install`, package updates, non-destructive operations. Shown without confirmation.

**High** - `rm`, `rm -rf`, `kill`, `chmod`, `chown`, `git reset --hard`, `git push --force`, operations that modify or destroy data. Confirmation required by default.

**Critical** - `reboot`, `shutdown`, `dd`, `mkfs`, `fdisk`, `apt remove`, system-altering commands. Confirmation required, warning styled prominently.

You can configure which levels prompt for confirmation through `require_confirmation` in your config file. Use `--yes` to skip all prompts (careful with this one).

---

## Configuration

converse looks for config files in this order:

1. `./converse.yaml` or `./converse.json` (project directory)
2. `~/.config/converse/config.yaml` or `~/.config/converse/config.json`
3. `~/.converse.yaml` or `~/.converse.json`

The setup wizard saves to `~/.config/converse/config.json`.

### Example config

```yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434/v1
  temperature: 0.1
  max_tokens: 500
  timeout: 30

safety:
  require_confirmation:
    - high
    - critical
  blocked_commands: []
```

### Environment variables

Environment variables override file settings. They take the `CONVERSE_` prefix:

```bash
export CONVERSE_MODEL=gpt-4o
export CONVERSE_BASE_URL=https://api.openai.com/v1
export CONVERSE_API_KEY=sk-...
export CONVERSE_TIMEOUT=60
export CONVERSE_BLOCKED="rm,reboot,shutdown"
```

### CLI flags

CLI flags override everything: config file and environment variables both:

```bash
converse "list running services" -m llama3.2 -u http://localhost:11434/v1 -p ollama -n
```

Full flag reference:

| Flag | Description |
|------|-------------|
| `-m`, `--model` | Model name (default: `llama3`) |
| `-u`, `--url` | API base URL |
| `-p`, `--provider` | Provider: `ollama`, `lmstudio`, `openai`, `custom` |
| `-k`, `--api-key` | API key |
| `-t`, `--temperature` | Temperature (default: `0.1`) |
| `--max-tokens` | Max response tokens (default: `500`) |
| `--timeout` | Request timeout in seconds (default: `30`) |
| `-x`, `--exec` | Execute a raw shell command directly, bypassing the LLM |
| `-n`, `--dry-run` | Preview without executing |
| `-y`, `--yes` | Auto-confirm all prompts |
| `--no-stream` | Disable streaming output |
| `-i`, `--interactive` | Force interactive mode |
| `-c`, `--config` | Path to config file |
| `--setup` | Run the setup wizard |
| `--version` | Show version and exit |

---

## Interactive mode tips

Run `converse` with no arguments to enter the REPL.

- Type a sentence to translate and execute
- `!command` runs a raw shell command directly, bypassing the LLM
- Outside the REPL, use `-x "command"` for the same effect
- `exit`, `quit`, or `q` to leave
- Ctrl+D or Ctrl+C also exit

Command history is saved to `~/.converse_history` and persists across sessions.

---

## Supported providers

| Provider | Default base URL | Notes |
|----------|-----------------|-------|
| Ollama | `http://localhost:11434/v1` | Default. Run `ollama serve` first. |
| LM Studio | `http://localhost:1234/v1` | Enable the local API server in settings. |
| OpenAI | `https://api.openai.com/v1` | Requires an API key. |
| Custom | user-defined | Any OpenAI-compatible endpoint. |

---

## Platform notes

| | Windows | Linux / macOS |
|--|---------|---------------|
| **Run** | `python -m converse "query"` | `python3 -m converse "query"` |
| **Run (installed)** | `converse "query"` | `converse "query"` |
| **Setup** | `python -m converse --setup` | `python3 -m converse --setup` |
| **Interactive** | `python -m converse` | `python3 -m converse` |
| **Install deps** | `pip install httpx rich` | `pip3 install httpx rich` |

After `pip install` (global or editable), the `converse` command is registered system-wide. On Windows, this requires the Python Scripts directory (`%APPDATA%\Python\Scripts` or equivalent) to be on your PATH, which the Python installer adds by default. On Linux/macOS, it goes into your environment's `bin` directory which is typically already on PATH.

---

## Project structure

```text
converse/
  cli.py            CLI argument parsing, interactive REPL, main flow
  setup_wizard.py   Interactive setup wizard with arrow-key provider selection
  models.py         Data structures for config, risk levels, and LLM responses
  prompt.py         System prompt that instructs the LLM to output JSON
  llm.py            HTTP client for streaming and non-streaming LLM API calls
  translator.py     Builds context-aware messages and parses LLM JSON responses
  executor.py       Pattern-based risk detection and subprocess execution
  __init__.py       Package init with version
  __main__.py       Entry point for `python -m converse`
```

---

## License

BSD 2-Clause. See [LICENSE](LICENSE).
