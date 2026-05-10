"""Simple command line chat tool using OpenAI API with streaming output.

Usage:
    python chat.py --config path/to/config.yaml

The config file must be a YAML file with the following keys:
    llm_url:      # Base URL of the LLM provider (e.g., https://api.openai.com/v1)
    api_key:      # API key for authentication
    system_prompt:# System prompt to send as the first message

The tool reads user input (supporting multi-line input terminated by an empty line),
sent to the LLM using the OpenAI chat completion endpoint in streaming mode.
Both the assistant's content and any tool calls are printed token‑by‑token.
After the response completes, the prompt appears again.
"""

import argparse
import sys
import json
import httpx
import traceback
from tools.python_exec_tool import PythonExecTool
from tools.write_file_tool import WriteFileTool
from tools.edit_file_tool import EditFileTool
from tools.registry import ToolRegistry
from llmrespoutput import LLMResponseOutput
from commands.quit_command import QuitCommand
from commands.reset_command import ResetCommand
from commands.help_command import HelpCommand
from commands.prompt_command import PromptCommand
from commands.model_command import ModelCommand
from commands.registry import CommandRegistry, CommandInput
from commands.base import CommandResult
# Load YAML configuration. The PyYAML package is required.
try:
    import yaml
except ImportError:
    print("Required package 'PyYAML' is not installed. Install with 'pip install -r requirements.txt'.")
    sys.exit(1)
import os
from typing import List, Dict, Any


class ResponseValidationError(Exception):
    pass

# The OpenAI library (>=1.0.0) provides a client class. We import lazily so the
# script can be imported without side effects.
try:
    from openai import OpenAI
except ImportError as e:
    print("Required package 'openai' is not installed. Install with 'pip install -r requirements.txt'.")
    sys.exit(1)


def load_config(path):
    """Load YAML configuration.

    The configuration must contain ``llm_url``, ``api_key``,  ``system_prompt`` and ``model``.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    env_fallbacks = {
        "llm_url": "SC_LLM_URL",
        "api_key": "SC_API_KEY",
        "model":   "SC_MODEL",
    }
    for key, env_var in env_fallbacks.items():
        if key not in cfg and env_var in os.environ:
            cfg[key] = os.environ[env_var]
    required = ["llm_url", "api_key", "system_prompt", "model"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    return cfg

def trim_to_none(value):
    if value is None:
        return None
    if len(value) == 0:
        return None
    return value


def get_user_input():
    """Read user input. If the first line is a command (/name args...), return a CommandInput immediately.
    Otherwise collect lines until a blank line and return the joined string."""
    print("You (finish with empty line. Type /quit to exit, /help for available commands):", flush=True)
    try:
        first_line = input()
    except EOFError:
        return ""

    stripped = first_line.strip()
    if stripped.startswith("/"):
        parts = stripped[1:].split()
        if parts:
            return CommandInput(name=parts[0].lower(), args=parts[1:])

    if first_line == "":
        return ""

    lines = [first_line]
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)

def validate_and_set_unique_field(message, name, value):
    if value and not message[name]:
        message[name] = value
    elif value and message[name] and message[name] == value:
        pass
    elif not value:
        pass
    else:
        raise ResponseValidationError("Expected unique value for "+name+" but got at least two different values: ", message[name], "!=", value)

        

known_delta_attributes = ["content", "function_call", "refusal","role","tool_calls", "reasoning_content"]

def check_unknown_delta_unknown_attributes(delta):
    for attr in vars(delta):
        if not attr in known_delta_attributes:
            print("WARN: Model returns unknown message attribute "+attr)
            known_delta_attributes.append(attr) 

def reconstruct_chat_completion(message, chunk, cfg):

    
     # -- Id ---
    validate_and_set_unique_field(message=message, name="id", value=chunk.id)

    if not chunk.choices:
       return False
    
    if (len(chunk.choices) != 1):
       return False
    
    choice = chunk.choices[0]

    if not choice.delta:
        raise ResponseValidationError("Got no delta in a chunk choice")
    delta = choice.delta

    check_unknown_delta_unknown_attributes(delta=delta)

    reasoning_field = cfg.get("reasoning_field", "reasoning_content")

    # ---- role ----
    validate_and_set_unique_field(message=message, name="role", value=delta.role)

    if hasattr(delta, "content"):
        content_token = trim_to_none(delta.content)
    else:
        content_token = None
    if hasattr(delta, reasoning_field):
        reasoning_content_token = trim_to_none(getattr(delta, reasoning_field))
    else:
        reasoning_content_token = None    
    message["content_token"] = content_token
    message["reasoning_content_token"] = reasoning_content_token
    message["tool_call_token"] = False


    # ---- content ----
    if content_token:
        message["content"] += content_token
        

    # ---- reasoning content ----
    if reasoning_content_token:
        message["reasoning_content"] += reasoning_content_token
        

    # ---- function_call (legacy style) ----
    if delta.function_call:
        message["tool_call_token"] = True
        if message["function_call"] is None:
            message["function_call"] = {
                "name": "",
                "arguments": ""
            }

        if delta.function_call.name:
            message["function_call"]["name"] += delta.function_call.name

        if delta.function_call.arguments:
            message["function_call"]["arguments"] += delta.function_call.arguments

    # ---- tool_calls (new style, streamed in pieces) ----
    if delta.tool_calls:
        message["tool_call_token"] = True
        for tool_delta in delta.tool_calls:
            index = tool_delta.index

            # Ensure list is large enough
            while len(message["tool_calls"]) <= index:
                message["tool_calls"].append({
                    "id": "",
                    "type": "function",
                    "function": {
                        "name": "",
                        "arguments": ""
                    }
                })
            tool = message["tool_calls"][index]
            # ID
            if tool_delta.id:
                tool["id"] += tool_delta.id

            # Function name / args
            if tool_delta.function:
                if tool_delta.function.name:
                    tool["function"]["name"] += tool_delta.function.name

                if tool_delta.function.arguments:
                    tool["function"]["arguments"] += tool_delta.function.arguments

    # ---- finish reason ----
    if (cfg.get("use_finish_reason", True)):
        validate_and_set_unique_field(message=message, name="finish_reason", value=choice.finish_reason)
    else:
       if  choice.finish_reason:
          message["finish_reason"] =  choice.finish_reason  

    return True

def stream_chat(messages, cfg, tool_registry):

    # Initialise the OpenAI client with the provided base URL and API key.
    ssl_verify = cfg.get("ssl_verify", True)
    client = OpenAI(
        base_url=cfg["llm_url"].rstrip("/"),
        api_key=cfg["api_key"],
        http_client=httpx.Client(verify=ssl_verify),
    )

    #Initialize recostructed message
    message = {
        "id": None,
        "role": None,
        "content": "",
        "reasoning_content": "",
        "tool_calls": [],
        "function_call": None,
        "finish_reason": None,
        "tool_call_token": False,
        "error_message": None
    }

    # Request a streaming response using the new SDK syntax.
    if ("reasoning_effort" in cfg):
        response = client.chat.completions.create(
            model=cfg.get("model"),
            messages=messages,
            tools=tool_registry.get_openai_tools(),
            stream=True,
            n=1,
            reasoning_effort=cfg.get("reasoning_effort")
        )
    else:
       response = client.chat.completions.create(
            model=cfg.get("model"),
            messages=messages,
            tools=tool_registry.get_openai_tools(),
            stream=True,
            n=1
        )

    output = LLMResponseOutput(cfg)

    for chunk in response:
        if chunk.id is None:
            message["error_message"] = getattr(chunk, "error_message", None)
            return message
        if not reconstruct_chat_completion(message=message, chunk=chunk, cfg=cfg):
            continue
        output.onLLMMessage(message)

    output.onLLMMessage(None)

    return message

def validate_message(message, cfg):
    if not message["id"]:
        if message.get("error_message"):
            raise ResponseValidationError(message["error_message"])
        raise ResponseValidationError("Got no id in the response")
    if not message["role"]:
        raise ResponseValidationError("Got no id in the response")
    if (cfg.get("use_finish_reason", True)):
        if not message["finish_reason"]:
            raise ResponseValidationError("Got no finish reason in the response")
        if not (message["finish_reason"] == 'stop' 
                or message["finish_reason"] == 'length' 
                or message["finish_reason"] == 'content_filter'
                or message["finish_reason"] == 'function_call'
                or message["finish_reason"] == 'tool_calls'):
            raise ResponseValidationError("Unknown finish reason in the response: "+message["finish_reason"])
    
        
     
def append_message_to_conversation(conversation, message):
    to_append = {}
    to_append["role"] =  message["role"]
    to_append["content"] =  message["content"]
    if message["reasoning_content"]:
        to_append["reasoning_content"] =  message["reasoning_content"]
    if message["function_call"]:
        to_append["function_call"] =  message["function_call"]
    if message["tool_calls"]:
        if (len(message["tool_calls"])>0):
            to_append["tool_calls"] = message["tool_calls"]
    conversation.append(to_append)        



def main() -> None:
    parser = argparse.ArgumentParser(description="Simple CLI chat with LLM")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to YAML configuration file",
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except Exception as exc:
        print(f"Failed to load config: {exc}")
        sys.exit(1)

    print("LLM Provider URL = "+cfg.get("llm_url")+", LLM Model = "+cfg.get("model"))    

    # Initialise the conversation with the system prompt.
    conversation = [{"role": "system", "content": cfg["system_prompt"]}]

    #Tools initializing
    all_tools = [PythonExecTool(), WriteFileTool(cfg.get("target")), EditFileTool(cfg.get("target"))]
    tool_names = cfg.get("tools", None)
    tool_registry = ToolRegistry(all_tools=all_tools, tool_names=tool_names, command_tool_configs=cfg.get("command_tools"), tool_timeout=cfg.get("tool_timeout", 300))

    command_registry = CommandRegistry([
        QuitCommand(tool_registry),
        ResetCommand(conversation, tool_registry, cfg["system_prompt"]),
        PromptCommand(),
        ModelCommand(cfg),
    ])
    command_registry.add(HelpCommand(command_registry))

    user_conversation = True
    while True:
        if user_conversation:
            user_input = get_user_input()
            if isinstance(user_input, CommandInput):
                result = command_registry.execute(user_input)
                if isinstance(result, CommandResult):
                    if result.output:
                        print(result.output)
                    if result.user_message:
                        conversation.append({"role": "user", "content": result.user_message})
                    else:
                        continue
                else:
                    if result is not None:
                        print(result)
                    continue
            elif not user_input:
                # Empty input – just continue prompting.
                continue
            else:
                conversation.append({"role": "user", "content": user_input})
        # Stream assistant response.
        gotError = False
        try:
            message = stream_chat(conversation, cfg, tool_registry=tool_registry)
            validate_message(message=message, cfg=cfg)
        except Exception as e:
            gotError = True
            print("Got an ERROR communicating with LLM: ", type(e).__name__, ":", e)
            traceback.print_exc()
            print("The response has been discarded. Try your message again!")
        if not gotError:    
            if cfg.get("use_finish_reason", True):
                if (message["finish_reason"] == 'stop' or message["finish_reason"] == 'length'):
                    user_conversation = True
                    discard_answer = False
                elif(message["finish_reason"] == 'content_filter'):
                    print("The input has been rejected due to content filter. The response has been discarded")
                    user_conversation =  True 
                    discard_answer = True
                elif (message["finish_reason"] == 'function_call'):
                    print("Legacy function calls not supported yet. The response has been discarded")
                    user_conversation =  True  
                    discard_answer = True 
                elif (message["finish_reason"] == 'tool_calls'):
                    user_conversation =  False
                    discard_answer = False
            else: #Heuristic
                if "tool_calls" in message:
                    if (len(message["tool_calls"]) > 0):
                        user_conversation =  False
                        discard_answer = False
                    else:
                        user_conversation =  True
                        discard_answer = False
                else:
                    user_conversation = True
                    discard_answer = False

            if not discard_answer:
                append_message_to_conversation(conversation, message)

            if not  user_conversation: #Tool Calls
                for tool_call in message["tool_calls"]:
                    name = tool_call["function"]["name"]
                    args_str = tool_call["function"]["arguments"]

                    try:
                        args = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        args = {}

                    try:
                        result = tool_registry.execute(name, args)
                    except Exception as e:
                        result = f"ERROR: {e}"

                    print(tool_registry.short_format_call(name, args, result))
                   
                    if cfg.get("trace", {}).get("toolcall", False):
                        try:
                            callString = tool_registry.format_call(name, args, result)
                            print(f"\n{callString}\n")
                        except Exception as e:
                            print(f"\nERROR: {e}")
                     
                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    })

                    

                        
if __name__ == "__main__":
    main()
