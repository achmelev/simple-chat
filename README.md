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
