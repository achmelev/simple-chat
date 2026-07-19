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
import traceback
from tools.python_exec_tool import PythonExecTool
from tools.write_file_tool import WriteFileTool
from tools.read_file_tool import ReadFileTool
from tools.edit_file_tool import EditFileTool
from tools.registry import ToolRegistry
from llm.base import ResponseValidationError
from llm.factory import create_llm_client
from commands.quit_command import QuitCommand
from commands.reset_command import ResetCommand
from commands.help_command import HelpCommand
from commands.prompt_command import PromptCommand
from commands.model_command import ModelCommand
from commands.conversation_command import ConversationCommand
from commands.benchmark_command import BenchmarkCommand
from commands.registry import CommandRegistry, CommandInput
from commands.base import CommandResult
# Load YAML configuration. The PyYAML package is required.
try:
    import yaml
except ImportError:
    print("Required package 'PyYAML' is not installed. Install with 'pip install -r requirements.txt'.")
    sys.exit(1)
import os


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
    # If the last message is already from the assistant, merge rather than append a new entry.
    if (conversation and conversation[-1]["role"] == "assistant"
            and to_append["role"] == "assistant" and to_append.get("content")):
        conversation[-1]["content"] += to_append["content"]
    else:
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

    print("LLM Provider URL = "+cfg.get("llm_url")+", LLM Model = "+cfg.get("model")+", API Type = "+cfg.get("api_type", "chat_completions"))

    # Initialise the conversation with the system prompt.
    conversation = [{"role": "system", "content": cfg["system_prompt"]}]
    session_storage = {}

    #Tools initializing
    all_tools = [PythonExecTool(), WriteFileTool(cfg.get("target")), EditFileTool(cfg.get("target")), ReadFileTool()]
    tool_names = cfg.get("tools", None)
    tool_registry = ToolRegistry(all_tools=all_tools, tool_names=tool_names, command_tool_configs=cfg.get("command_tools"), tool_timeout=cfg.get("tool_timeout", 300))

    llm_client = create_llm_client(cfg)

    command_registry = CommandRegistry([
        QuitCommand(tool_registry),
        ResetCommand(conversation, tool_registry, cfg["system_prompt"], session_storage),
        PromptCommand(),
        ModelCommand(cfg),
        ConversationCommand(conversation, tool_registry),
        BenchmarkCommand(
            conversation=conversation,
            tool_registry=tool_registry,
            cfg=cfg,
            system_prompt=cfg["system_prompt"],
            stream_chat_fn=llm_client.stream_chat,
            validate_message_fn=validate_message,
            append_message_fn=append_message_to_conversation,
            session_storage=session_storage,
        ),
    ])
    command_registry.add(HelpCommand(command_registry))

    # In legacy_completions mode there is no chat memory: each turn is sent to the
    # API on its own, with no system message, so the conversation is reset to just
    # the new user input before every call.
    single_turn_mode = cfg.get("api_type") == "legacy_completions"

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
                        if single_turn_mode:
                            conversation.clear()
                        conversation.append({"role": "user", "content": result.user_message})
                    elif not result.send_to_llm:
                        continue
                else:
                    if result is not None:
                        print(result)
                    continue
            elif not user_input:
                # Empty input – just continue prompting.
                continue
            else:
                if single_turn_mode:
                    conversation.clear()
                conversation.append({"role": "user", "content": user_input})
        # Stream assistant response.
        gotError = False
        try:
            message = llm_client.stream_chat(conversation, cfg, tool_registry=tool_registry, session_storage=session_storage)
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

                    print(tool_registry.short_format_call(name, args))
                    
                    try:
                        result = tool_registry.execute(name, args)
                    except Exception as e:
                        result = f"ERROR: {e}"

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
