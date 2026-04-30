# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

SimpleChat is a command-line tool for interactive multi-turn conversations with LLMs via OpenAI-compatible APIs. It supports streaming responses, tool calling (Python code execution, time/location queries), and is configurable per provider/use-case via YAML files.

## Running

```bash
pip install -r requirements.txt
python chat.py --config path/to/config.yaml
```

Interactive commands during a session: `/quit`, `/reset`.

## Architecture

**Entry point:** `chat.py` — loads config, initializes `ToolRegistry`, runs the conversation loop.

**Conversation loop** (`chat.py`):
1. Collect user input (multi-line, terminated by empty line)
2. Stream LLM response token-by-token via OpenAI SDK
3. Reconstruct the full message from delta chunks (`reconstruct_chat_completion`)
4. If `finish_reason == tool_calls`: execute tools, append results, continue loop
5. If `finish_reason == stop/length`: wait for next user input

**Tool system** (`tools/`):
- `base.py` — abstract `Tool` class; subclasses implement `name()`, `description()`, `parameters()`, `execute(arguments)`
- `registry.py` — `ToolRegistry` manages lifecycle (init/shutdown) and converts tools to OpenAI function format
- `time_tool.py` — returns current time at a given location (geopy + timezonefinder, with in-memory cache)
- `python_exec_tool.py` — executes Python code in a temporary venv (isolated per session, pip-installable, 60s timeout)

## Configuration

All configs are YAML. Required fields: `llm_url`, `api_key`, `model`, `system_prompt`. Optional: `tools` (list), `reasoning_effort` ("low"/"medium"/"high"), `reasoning_field` (default: `"reasoning_content"`), `use_finish_reason`.

The repo ships several ready-made configs for different providers and use cases (OpenAI, Anthropic, DeepInfra, Java coding agent). Copy one and adjust for a new provider. The active `config.yaml` is gitignored.

## Adding a New Tool

1. Create a file in `tools/` subclassing `Tool` from `tools/base.py`
2. Implement `name()`, `description()`, `parameters()` (OpenAI JSON schema), and `execute(arguments)`
3. Register the tool in `tools/registry.py` and enable it via the `tools:` list in config
