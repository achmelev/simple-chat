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
from tools.time_tool import TimeTool
from tools.python_exec_tool import PythonExecTool
from tools.registry import ToolRegistry
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

    The configuration must contain ``llm_url``, ``api_key`` and ``system_prompt``.
    ``model`` is optional – if omitted ``gpt-3.5-turbo`` is used.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    required = ["llm_url", "api_key", "system_prompt"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    # Provide a default model if not specified in the config.
    cfg.setdefault("model", "gpt-3.5-turbo")
    return cfg

def trim_to_none(value):
    if value is None:
        return None
    if len(value) == 0:
        return None
    return value


def get_user_input():
    """Read multiline user input terminated by an empty line.

    The function prints a prompt ("You: ") and then reads from stdin until a
    blank line is entered. The collected lines are joined with newlines.
    """
    print("You (finish with empty line. Print exit, if you want out):", flush=True)
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            # End of input stream (e.g., piped file). Return what we have.
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
        raise ResponseValidationError("Expected unique value for "+name+" but got at least two different values")

        

def reconstruct_chat_completion(message, chunk):

     # -- Id ---
    validate_and_set_unique_field(message=message, name="id", value=chunk.id)

    if not chunk.choices:
       raise ResponseValidationError("Got not choices in a chunk") 
    
    if (len(chunk.choices) != 1):
        raise ResponseValidationError("Got "+len(chunk.choices)+" choices in a chunk")
    
    choice = chunk.choices[0]

    if not choice.delta:
        raise ResponseValidationError("Got no delta in a chunk choice")
    delta = choice.delta

   

    # ---- role ----
    validate_and_set_unique_field(message=message, name="role", value=delta.role)

    content_token = trim_to_none(delta.content)
    reasoning_content_token = trim_to_none(delta.reasoning_content)
    message["content_token"] = content_token
    message["reasoning_content_token"] = reasoning_content_token


    # ---- content ----
    if content_token:
        message["content"] += content_token
        

    # ---- reasoning content ----
    if reasoning_content_token:
        message["reasoning_content"] += reasoning_content_token
        

    # ---- function_call (legacy style) ----
    if delta.function_call:
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
    validate_and_set_unique_field(message=message, name="finish_reason", value=choice.finish_reason)

    return message

def stream_chat(messages, cfg, tool_registry):
    
    # Initialise the OpenAI client with the provided base URL and API key.
    client = OpenAI(
        base_url=cfg["llm_url"].rstrip("/"),
        api_key=cfg["api_key"],
    )

    #Initialize recostructed message
    message = {
        "id": None,
        "role": None,
        "content": "",
        "reasoning_content": "",
        "tool_calls": [],
        "function_call": None,
        "finish_reason": None
    }

    # Request a streaming response using the new SDK syntax.
    response = client.chat.completions.create(
        model=cfg.get("model"),
        messages=messages,
        tools=tool_registry.get_openai_tools(),
        stream=True,
        n=1,
        reasoning_effort=cfg.get("reasoning_effort","medium"), 
    )
    

    in_reasoning = False

    for chunk in response:
        reconstruct_chat_completion(message=message, chunk=chunk)
        #print(str(message["reasoning_content_token"])+":"+str(message["content_token"]))
        if (in_reasoning):
            if message["reasoning_content_token"]:
                print(message["reasoning_content_token"], end="", flush=True)
            if message["content_token"]: 
                print("\n</think>", flush=True)
                in_reasoning = False
                print(message["content_token"], end="", flush=True)
        else:
            if message["content_token"]: 
                print(message["content_token"], end="", flush=True)
            if message["reasoning_content_token"]:
                print("<think>", flush=True)
                in_reasoning = True
                print(message["reasoning_content_token"], end="", flush=True)    

    # Ensure newline after completion.
    print()

    return message

def validate_message(message):
    if not message["id"]:
        raise ResponseValidationError("Got no id in the response")
    if not message["role"]:
        raise ResponseValidationError("Got no id in the response")
    if not message["finish_reason"]:
        raise ResponseValidationError("Got no finish reason in the response")
    if not (message["finish_reason"] == 'stop' 
            or message["finish_reason"] == 'length' 
            or message["finish_reason"] == 'content_filter'
            or message["finish_reason"] == 'function_call'
            or message["finish_reason"] == 'tool_calls'):
        raise ResponseValidationError("Unknown finish reason in the response: "+message["finish_reason"])
    
        
     
def append_message_to_conversation(conversation, message):
    conversation.append({
        "role": message["role"],
        "content": message["content"],
        "reasoning_content": message["reasoning_content"],
        "tool_calls": message["tool_calls"],
        "function_call": message["function_call"],
    })


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

    # Initialise the conversation with the system prompt.
    conversation = [{"role": "system", "content": cfg["system_prompt"]}]

    #Tools initializing
    all_tools = [TimeTool(), PythonExecTool()]
    tool_names = cfg.get("tools", None)
    tool_registry = ToolRegistry(all_tools=all_tools, tool_names=tool_names) 


    user_conversation = True
    while True:
        if user_conversation: 
            user_msg = get_user_input()
            if user_msg.strip().lower() in {"exit", "quit", "/quit"}:
                print("Exiting chat.")
                tool_registry.shut_down()
                break
            if not user_msg:
                # Empty input – just continue prompting.
                continue
            conversation.append({"role": "user", "content": user_msg})
        # Stream assistant response.
        gotError = False
        try:
            message = stream_chat(conversation, cfg, tool_registry=tool_registry)
            validate_message(message=message)
        except Exception as e:
            gotError = True
            print("Got an ERROR communicating with LLM: ", type(e).__name__, ":", e)
            print("The response has been discarded. Try your message again!")
        if not gotError:    
            if (message["finish_reason"] == 'stop' or message["finish_reason"] == 'length'):
                append_message_to_conversation(conversation=conversation, message=message)
                user_conversation = True
            elif(message["finish_reason"] == 'content_filter'):
                print("The input has been rejected due to content filter. The response has been discarded")
                user_conversation =  True
            elif (message["finish_reason"] == 'function_call'):
                print("Function calls not supported yet. The response has been discarded")
                user_conversation =  True
            elif (message["finish_reason"] == 'tool_calls'):
                user_conversation =  False
                append_message_to_conversation(conversation, message)
                for tool_call in message["tool_calls"]:
                    name = tool_call["function"]["name"]
                    args_str = tool_call["function"]["arguments"]

                    try:
                        args = json.loads(args_str) if args_str else {}
                    except json.JSONDecodeError:
                        args = {}

                    print(f"\n[Executing tool: {name}]")

                    try:
                        result = tool_registry.execute(name, args)
                    except Exception as e:
                        result = f"ERROR: {e}"
                    
                    try:
                        callString = tool_registry.format_call(name, args,result)
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
