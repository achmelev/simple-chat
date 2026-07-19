# Configuration Reference

SimpleChat is configured via a YAML file passed with `--config`. This document describes every supported key.

---

## Required keys

| Key | Type | Description |
|-----|------|-------------|
| `system_prompt` | string | System prompt sent as the first message in every conversation |

The connection keys `llm_url`, `api_key`, and `model` must also be provided, either in the config file or via environment variables — see [Environment variables](#environment-variables).

---

## LLM behaviour

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_type` | string | `"chat_completions"` | Which OpenAI-compatible API to call: `"chat_completions"` (the `/chat/completions` endpoint, with roles, tool calling, and reasoning) or `"legacy_completions"` (the plain text-in/text-out `/completions` endpoint — no tool calling or reasoning support). |
| `reasoning_effort` | string | _(omit)_ | Reasoning budget passed to the model: `"low"`, `"medium"`, or `"high"`. Omit for models that do not support it. Ignored by `"legacy_completions"`. |
| `temperature` | number | _(omit)_ | Sampling temperature passed to the model. Omit to use the provider's default. |
| `top_p` | number | _(omit)_ | Nucleus sampling probability mass passed to the model. Omit to use the provider's default. |
| `max_completion_tokens` | integer | _(omit)_ | Maximum number of completion tokens to generate. With `"chat_completions"`, sent as both `max_completion_tokens` and the legacy `max_tokens`, for compatibility with providers that only recognize one or the other; with `"legacy_completions"`, sent as `max_tokens` only. |
| `echo` | boolean | _(omit)_ | `"legacy_completions"` only. When `true`, the API echoes the prompt back before the generated continuation. Note: the echoed prompt is not stripped out, so it becomes part of the stored assistant message and gets fed back into the prompt on the next turn. |
| `logprobs` | boolean | `false` | `"legacy_completions"` only. When `true`, requests log probabilities (`logprobs=1`) from the API and prints each token's log probability to the terminal as it streams in. |
| `extra_headers` | map | _(omit)_ | Additional HTTP headers passed through to the API request. |
| `extra_query` | map | _(omit)_ | Additional query string parameters passed through to the API request. |
| `extra_body` | map | _(omit)_ | Additional fields merged into the JSON request body. |
| `reasoning_field` | string | `"reasoning_content"` | Name of the field in the streaming delta that carries reasoning/thinking tokens. Change only if your provider uses a non-standard field name. Ignored by `"legacy_completions"`. |
| `use_finish_reason` | boolean | `true` | When `true`, the finish reason from the API response is used to detect tool calls and end-of-turn. Set to `false` for providers that omit or misreport `finish_reason`. |
| `ssl_verify` | boolean | `true` | Set to `false` to disable SSL certificate verification. Useful for local endpoints with self-signed certificates. |

---

## Tools

### `tools`

A list of tool names to enable for the session. Only listed tools are installed and offered to the model. This list covers both built-in tools and any command-line tools defined under `command_tools`. A warning is printed for any name that does not match a known tool.

Note: with `api_type: legacy_completions` the model is never told about enabled tools (the `/completions` endpoint has no `tools` parameter), so it cannot emit tool calls even if tools are listed here.

```yaml
tools:
  - execute_python
  - write_file
  - edit_file
  - read_file
  - mvn           # a command tool defined under command_tools
```

Built-in tool names:

| Name | Description |
|------|-------------|
| `execute_python` | Executes Python code in an isolated venv; supports installing packages |
| `write_file` | Writes text to a file (creates or overwrites) |
| `edit_file` | Edits a file by exact-string replacement |
| `read_file` | Reads a file and returns its text content |

### `command_tools`

Exposes arbitrary executables as tools without writing any Python code. Each entry in the list defines a tool whose name must then appear in `tools` to be activated.

```yaml
command_tools:
  - binary: /usr/bin/mvn
    description: "Runs Maven build commands"
    name: maven        # optional — defaults to the binary's filename
  - binary: /usr/bin/git
    description: "Runs git commands in a given directory"
```

| Subkey | Required | Description |
|--------|----------|-------------|
| `binary` | yes | Absolute path to the executable |
| `description` | yes | Description shown to the model |
| `name` | no | Tool name; defaults to the binary's filename |

Each command tool accepts `working_directory` (string) and `arguments` (list of strings) from the model.

### `tool_timeout`

```yaml
tool_timeout: 300
```

Timeout in seconds applied to all tool subprocesses (`execute_python`, command tools). Default: `300`.

---

## Output target

### `target`

Controls how files are written by `write_file` and `edit_file`.

```yaml
target:
  newline: windows    # or: unix, auto
```

| Subkey | Values | Default | Description |
|--------|--------|---------|-------------|
| `newline` | `windows`, `unix`, `auto` | `auto` | Line ending style for written files. `windows` → `\r\n`, `unix` → `\n`, `auto` → platform default |

---

## Tracing and debugging

### `trace`

Controls diagnostic output. All subkeys default to `false`.

```yaml
trace:
  thinking: false
  toolcall: false
  llmoutput: false
```

| Subkey | Default | Description |
|--------|---------|-------------|
| `thinking` | `false` | Print full reasoning content wrapped in `<THINKING>`/`</THINKING>`. When `false`, reasoning is shown as an animated spinner instead. |
| `toolcall` | `false` | Print the XML-formatted tool call input and output after each tool execution. |
| `llmoutput` | `false` | Write a `llmtrace<timestamp>.txt` file that logs every LLM output state change in detail. |

---

## MCP server

### `mcp`

Controls the MCP (Model Context Protocol) server started by `mcp.py`. All subkeys are optional.

```yaml
mcp:
  http_port: 9090
```

| Subkey | Type | Default | Description |
|--------|------|---------|-------------|
| `http_port` | integer | `9090` | TCP port the MCP SSE HTTP server listens on |

The MCP server reads the same config file as `chat.py` but only uses `tools`, `command_tools`, `tool_timeout`, `target`, `trace`, and `mcp`. LLM connection keys (`llm_url`, `api_key`, `model`, `system_prompt`) are ignored.

Run with:
```bash
python mcpsrv.py --config path/to/config.yaml
# or inside Docker:
simplemcp --config path/to/config.yaml
```

The server exposes a single Streamable HTTP endpoint at `POST http://host:<http_port>/mcp`. Clients must send `Accept: application/json, text/event-stream`.

---

## Environment variables

The three connection keys can be set as environment variables. Values in the config file take precedence over environment variables.

| Config key | Environment variable |
|------------|----------------------|
| `llm_url` | `SC_LLM_URL` |
| `api_key` | `SC_API_KEY` |
| `model` | `SC_MODEL` |

---

## Full example

```yaml
llm_url: "https://api.openai.com/v1"
api_key: "YOUR_API_KEY"
model: "YOUR_MODEL"
system_prompt: |
  You are a helpful assistant.

tools:
  - execute_python
  - write_file
  - edit_file
  - read_file
  - mvn

command_tools:
  - binary: /usr/bin/mvn
    description: "Runs Maven build commands (compile, test, package, ...)"
    name: mvn

reasoning_effort: "medium"
tool_timeout: 300
ssl_verify: true

target:
  newline: unix

trace:
  thinking: false
  toolcall: false
  llmoutput: false
```
