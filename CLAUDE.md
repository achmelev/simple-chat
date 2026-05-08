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

**`llmrespoutput.py`** — `LLMResponseOutput` class; streams LLM output to the terminal token-by-token, handling `<THINKING>` / `</THINKING>` wrapping for reasoning content. Call `onLLMMessage(message)` per chunk and `onLLMMessage(None)` to finalize.

**Conversation loop** (`chat.py`):
1. Collect user input (multi-line, terminated by empty line)
2. Stream LLM response token-by-token via OpenAI SDK
3. Reconstruct the full message from delta chunks (`reconstruct_chat_completion`)
4. If `finish_reason == tool_calls`: execute tools, append results, continue loop
5. If `finish_reason == stop/length`: wait for next user input

**Tool system** (`tools/`):
- `base.py` — abstract `Tool` class; subclasses implement `name()`, `description()`, `parameters()`, `execute(arguments)`
- `registry.py` — `ToolRegistry` manages lifecycle (init/shutdown) and converts tools to OpenAI function format
- `python_exec_tool.py` — executes Python code in a temporary venv (isolated per session, pip-installable, 60s timeout)

## Configuration

All configs are YAML. Required fields: `llm_url`, `api_key`, `model`, `system_prompt`. Optional: `tools` (list), `reasoning_effort` ("low"/"medium"/"high"), `reasoning_field` (default: `"reasoning_content"`), `use_finish_reason`, `ssl_verify` (default: `true` — set to `false` to disable SSL certificate verification, e.g. for local endpoints with self-signed certs), `responsetrace` (default: `false` — set to `true` to print full reasoning content wrapped in `<THINKING>`/`</THINKING>`; when `false`, reasoning is shown as an animated "Thinking |" spinner).

The repo ships several ready-made configs for different providers and use cases (OpenAI, Anthropic, DeepInfra, Java coding agent). Copy one and adjust for a new provider. The active `config.yaml` is gitignored.

## Adding a New Tool

1. Create a file in `tools/` subclassing `Tool` from `tools/base.py`
2. Implement `name()`, `description()`, `parameters()` (OpenAI JSON schema), and `execute(arguments)`
3. Register the tool in `tools/registry.py` and enable it via the `tools:` list in config

## Dockerfile

The `Dockerfile` copies every source file individually into `/opt/simplechat/`. **Any time a source file is added or removed, the corresponding `COPY` line must be added or removed in the Dockerfile as well.** Currently copied files:

- `requirements.txt`, `chat.py`, `llmrespoutput.py`
- `tools/__init__.py`, `tools/base.py`, `tools/registry.py`
- `tools/python_exec_tool.py`
- `tools/command_line_tool.py`, `tools/configurable_command_tool.py`
- `tools/write_file_tool.py`, `tools/edit_file_tool.py`
