# 🧠 Simple CLI Chat Tool

A lightweight Python-based command-line chat tool for interacting with
Large Language Models (LLMs) via the OpenAI-compatible API.\
It supports **streaming responses**, **tool execution**, and
**configurable providers**.

------------------------------------------------------------------------

## 📦 Prerequisites

-   Python 3.9+
-   API key for an OpenAI-compatible provider

Required packages: - openai\>=1.0.0 - PyYAML\>=6.0 - geopy\>=2.4.1 -
timezonefinder\>=8.2.1

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

Create a YAML config file:

``` yaml
llm_url: "https://api.openai.com/v1"
api_key: "YOUR_API_KEY"
system_prompt: "You are a helpful assistant."
model: "YOUR_MODEL"

tools:
  - execute_python

reasoning_effort: "medium"
```

### Command-line tools

Arbitrary executables can be exposed as tools without writing any code.
Add a `command_tools` list to the config — each entry requires `binary`
and `description`; `name` is optional and defaults to the binary's
filename.

``` yaml
command_tools:
  - binary: /usr/bin/mvn
    description: "Runs Maven build commands (e.g. compile, test, package)"
    name: maven          # optional — defaults to "mvn"
  - binary: /usr/bin/git
    description: "Runs git commands in a given directory"

tools:
  - maven
  - git
  - execute_python
```

Each tool accepts two arguments from the LLM: `working_directory` and
`arguments` (a list of strings passed directly to the binary).

### Environment variables

`llm_url`, `api_key`, and `model` can be set via environment variables
instead of (or as defaults for) the config file. Values in the config
file take precedence.

| Config key | Environment variable |
|------------|----------------------|
| `llm_url`  | `SC_LLM_URL`         |
| `api_key`  | `SC_API_KEY`         |
| `model`    | `SC_MODEL`           |

The included `set-provider.sh` script sets all three at once by provider
id:

``` bash
source set-provider.sh openai      # or: deepinfra, anthropic
python chat.py --config config.yaml
```

The script can be sourced repeatedly to switch providers within the same
shell session.

------------------------------------------------------------------------

## 🚀 Usage

``` bash
python chat.py --config path/to/config.yaml
```

### Commands

-   /quit → Exit
-   /reset → Reset conversation

------------------------------------------------------------------------

## ✨ Features

-   Streaming responses
-   Tool execution
-   Configurable LLM backend
-   Multi-turn chat

------------------------------------------------------------------------

## ⚠️ Notes

Python execution tool runs locally. Use with caution.
