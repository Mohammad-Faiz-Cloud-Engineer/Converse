# converse

<p align="center">
  <a href="https://github.com/yourusername/converse/actions/workflows/ci.yml"><img src="https://github.com/yourusername/converse/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-152-brightgreen" alt="Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/code%20lines-1639-blue" alt="Lines of Code"></a>
  <br>
  <img src="https://img.shields.io/badge/dependencies-2-orange" alt="Dependencies">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

> **Natural Language Shell**

converse turns plain English into shell commands. Tell it what you want and it figures out the rest.

```bash
converse "show me all files including hidden ones"
converse "create a folder named project and move everything there"
converse "find all Python files that were changed in the last week"
```

It works with local LLMs running on your machine through Ollama or LM Studio, and with any OpenAI compatible API. Commands stream back as they are generated so you see the translation happening in real time.

## How it works

You write a sentence. converse sends it to a language model along with your current directory and operating system. The model returns a structured JSON response containing the exact shell command to run, an explanation of what it does, and a risk assessment. converse checks this assessment against its own local safety rules, asks for confirmation on dangerous operations, and then executes the command.

This means you get the flexibility of natural language with the guardrails of a safety first design.

## Features

- Supports Ollama, LM Studio, and any OpenAI compatible endpoint
- Streaming responses show you the translation as it happens
- Automatic risk detection flags destructive commands like reboots, file deletions, or system changes
- Confirmation prompts stop you from accidentally running high risk operations
- Local pattern matching acts as a backup safety net even if the model gets the risk level wrong
- Context awareness sends your current directory and OS so the model resolves paths correctly
- Interactive REPL mode with command history for chaining multiple queries
- Dry run mode lets you preview the command before execution
- Configuration through YAML files, JSON files, environment variables, or CLI flags
- Raw shell passthrough in interactive mode with the `!` prefix

## Quick start

### Install

```bash
pip install converse
```

Or install from source:

```bash
git clone https://github.com/yourusername/converse.git
cd converse
pip install -e .
```

### Run an LLM

You need a running LLM server. The easiest way is with Ollama:

```bash
ollama pull llama3.2
ollama serve
```

Or point it at any OpenAI compatible API:

```bash
converse "list all running processes" --url https://api.openai.com/v1 --model gpt-4o --api-key $OPENAI_API_KEY
```

### Use it

Single command mode:

```bash
converse "create a folder named test"
```

Interactive mode:

```bash
converse --interactive
```

Dry run to preview without executing:

```bash
converse "delete everything in downloads" --dry-run
```

## Safety

Safety is built into the core of converse. Every command goes through two layers of risk assessment. The LLM classifies the risk in its response, and converse also runs its own pattern matching on the command itself. The more conservative result wins.

Commands are categorized into four risk levels.

**Low** Includes things like ls, pwd, echo, cat, grep, and other read only operations. These run automatically without prompting.

**Medium** Includes mkdir, touch, cp, mv, curl, and other non destructive operations. The command is shown but no confirmation is needed.

**High** Includes rm, kill, chmod, chown, git reset hard, and other operations that modify or destroy data. Confirmation is required.

**Critical** Includes reboot, shutdown, dd, mkfs, apt remove, and other system altering commands. Confirmation is required and the warning is styled prominently.

You can adjust which risk levels require confirmation in your configuration file, or bypass all prompts with the `--yes` flag (use this carefully).

## Configuration

converse looks for configuration files in this order:

1. `./converse.yaml` or `./converse.json` (current directory)
2. `~/.config/converse/config.yaml` or `~/.config/converse/config.json`
3. `~/.converse.yaml` or `~/.converse.json`

Example YAML:

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

Environment variables override file settings. They use the `CONVERSE_` prefix. For example:

```bash
export CONVERSE_MODEL=gpt-4o
export CONVERSE_BASE_URL=https://api.openai.com/v1
export CONVERSE_API_KEY=sk-...
```

CLI flags take priority over everything:

```bash
converse "list running services" -m llama3.2 -u http://localhost:11434/v1 -p ollama
```

## Interactive mode tips

Run `converse --interactive` or just `converse` with no arguments to enter the REPL.

Special commands inside the REPL:

- Type any natural language sentence to translate and execute it
- Use `!command` to run a raw shell command directly, bypassing the LLM
- Type `exit`, `quit`, or `q` to leave
- Ctrl+D or Ctrl+C also exit

Command history is saved to `~/.converse_history` and persists across sessions.

## Supported providers

| Provider | base_url | Notes |
| -------- | -------- | ----- |
| Ollama | `http://localhost:11434/v1` | Default. Run `ollama serve` first. |
| LM Studio | `http://localhost:1234/v1` | Enable the local API server in settings. |
| OpenAI | `https://api.openai.com/v1` | Requires an API key. |
| Custom | Any OpenAI compatible endpoint | Works with any server that follows the OpenAI chat completions format. |

## Project structure

```text
converse/
  cli.py         CLI argument parsing, interactive REPL, main flow
  models.py      Data structures for config, risk levels, and LLM responses
  prompt.py      System prompt that instructs the LLM to output JSON
  llm.py         HTTP client for streaming and non streaming LLM API calls
  translator.py  Builds context aware messages and parses LLM JSON responses
  executor.py    Pattern based risk detection and subprocess execution
```

## License

MIT
