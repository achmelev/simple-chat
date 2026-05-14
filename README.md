# 🧠 Simple CLI Chat Tool

A lightweight Python-based command-line chat tool for interacting with
Large Language Models (LLMs) via the OpenAI-compatible API.\
It supports **streaming responses**, **tool execution**, and
**configurable providers**.

It also ships an **MCP server** (`mcpsrv.py`) that exposes the same
configured tools to any MCP-compatible harness via SSE.

------------------------------------------------------------------------

## 📦 Prerequisites

-   Python 3.10+
-   API key for an OpenAI-compatible provider (not required for the MCP server)

Required packages: openai\>=1.0.0, PyYAML\>=6.0, mcp\>=1.0.0, uvicorn\>=0.30.0

------------------------------------------------------------------------

## ⚙️ Setup

``` bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
pip install -r requirements.txt
```

(Optional)

``` bash
python -m venv venv
source venv/bin/activate
```

------------------------------------------------------------------------

## 🧩 Configuration

Create a YAML config file and pass it with `--config`. See
[CONFIGURATION.md](CONFIGURATION.md) for a full reference of all keys
and subkeys.

------------------------------------------------------------------------

## 🚀 Usage

### Chat

``` bash
python chat.py --config path/to/config.yaml
```

#### Commands

-   /quit → Exit
-   /reset → Reset conversation

### MCP Server

``` bash
python mcpsrv.py --config path/to/config.yaml
```

Starts an HTTP SSE server (default port 9090) that exposes the tools
defined in the config to any MCP-compatible client. The MCP server uses
only the `tools`, `command_tools`, `tool_timeout`, `target`, `trace`,
and `mcp` config keys — no LLM connection keys are required.

------------------------------------------------------------------------

## ✨ Features

-   Streaming responses
-   Tool execution
-   Configurable LLM backend
-   Multi-turn chat
-   MCP SSE server for tool exposure to external harnesses

------------------------------------------------------------------------

## ⚠️ Notes

Python execution tool runs locally. Use with caution.
