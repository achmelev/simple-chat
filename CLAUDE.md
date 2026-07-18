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
2. Stream the LLM response via an `LLMClient` (see below), which returns a reconstructed message dict
3. If `finish_reason == tool_calls`: execute tools, append results, continue loop
4. If `finish_reason == stop/length`: wait for next user input

**LLM client** (`llm/`):
- `base.py` — abstract `LLMClient` class with a single method, `stream_chat(messages, cfg, tool_registry, time_limit_seconds=None, start_time=None, session_storage=None)`, returning a reconstructed message dict (`id`, `role`, `content`, `reasoning_content`, `tool_calls`, `function_call`, `finish_reason`, `tool_call_token`, `error_message`, `timed_out`); also defines `ResponseValidationError`
- `openai_client.py` — `OpenAIChatClient`, the only implementation today; builds the OpenAI SDK request (including all optional sampling/extra parameters from config), streams the response, and reconstructs the message from delta chunks token-by-token
- To support a different provider API, implement `LLMClient` in a new module and swap the `OpenAIChatClient()` instantiation in `chat.py`'s `main()`

**Tool system** (`tools/`):
- `base.py` — abstract `Tool` class; subclasses implement `name()`, `description()`, `parameters()`, `execute(arguments)`
- `registry.py` — `ToolRegistry` manages lifecycle (init/shutdown) and converts tools to OpenAI function format
- `python_exec_tool.py` — executes Python code in a temporary venv (isolated per session, pip-installable, 60s timeout)

**Command system** (`commands/`):
- `base.py` — abstract `Command` class; subclasses implement `name()`, `short_description()`, `description()`, `execute(arguments)`
- `registry.py` — `CommandRegistry` parses `/name arg1 arg2 ...` input and dispatches to the matching command
- `quit_command.py` — shuts down tools and exits the process
- `reset_command.py` — clears conversation history and reinitializes tools

## Configuration

All configs are YAML. Required fields: `llm_url`, `api_key`, `model`, `system_prompt`. Optional: `tools` (list), `reasoning_effort` ("low"/"medium"/"high"), `reasoning_field` (default: `"reasoning_content"`), `use_finish_reason`, `ssl_verify` (default: `true` — set to `false` to disable SSL certificate verification, e.g. for local endpoints with self-signed certs), `tool_timeout` (default: `300` seconds — subprocess timeout for all tool executions), `trace` (optional map with subkeys):
- `trace.thinking` (default: `false`) — print full reasoning content wrapped in `<THINKING>`/`</THINKING>`; when `false`, reasoning is shown as an animated spinner
- `trace.toolcall` (default: `false`) — print the XML-formatted tool call input/output after each tool execution
- `trace.llmoutput` (default: `false`) — write a detailed `llmtrace<timestamp>.txt` file tracing all LLM output state changes

The repo ships several ready-made configs for different providers and use cases (OpenAI, Anthropic, DeepInfra, Java coding agent). Copy one and adjust for a new provider. The active `config.yaml` is gitignored.

**Any time a configuration key is added, removed, or changed, `CONFIGURATION.md` must be updated accordingly.**

## Adding a New Tool

1. Create a file in `tools/` subclassing `Tool` from `tools/base.py`
2. Implement `name()`, `description()`, `parameters()` (OpenAI JSON schema), and `execute(arguments)`
3. Register the tool in `tools/registry.py` and enable it via the `tools:` list in config

## Dockerfile

The `Dockerfile` copies every source file individually into `/opt/simplechat/`. **Any time a Python source file is added or removed anywhere in the project, the corresponding `COPY` line must be added or removed in the Dockerfile as well.**
