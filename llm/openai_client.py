import time
import httpx

from llm.base import LLMClient, ResponseValidationError
from llmrespoutput import LLMResponseOutput

try:
    from openai import OpenAI
except ImportError as e:
    raise ImportError(
        "Required package 'openai' is not installed. Install with 'pip install -r requirements.txt'."
    ) from e


def trim_to_none(value):
    if value is None:
        return None
    if len(value) == 0:
        return None
    return value


def validate_and_set_unique_field(message, name, value):
    if value and not message[name]:
        message[name] = value
    elif value and message[name] and message[name] == value:
        pass
    elif not value:
        pass
    else:
        raise ResponseValidationError("Expected unique value for "+name+" but got at least two different values: ", message[name], "!=", value)


class OpenAIChatClient(LLMClient):

    _known_delta_attributes = ["content", "function_call", "refusal", "role", "tool_calls", "reasoning_content"]

    def _check_unknown_delta_unknown_attributes(self, delta):
        for attr in vars(delta):
            if attr not in self._known_delta_attributes:
                print("WARN: Model returns unknown message attribute "+attr)
                self._known_delta_attributes.append(attr)

    def _resolve_reasoning_token(self, delta, content_token, cfg, session_storage):
        global_field = cfg.get("reasoning_field", "reasoning_content")

        if session_storage is None:
            return trim_to_none(getattr(delta, global_field, None))

        if "reasoning_field" in session_storage:
            return trim_to_none(getattr(delta, session_storage["reasoning_field"], None))

        # Key not yet set — always try the global setting first
        value = trim_to_none(getattr(delta, global_field, None))
        if value is not None:
            session_storage["reasoning_field"] = global_field
            return value

        # Global setting produced nothing; if content is also absent, search for any
        # field whose name starts with "reasoning" (up to 10 attempts total)
        if content_token is None:
            attempts = session_storage.get("reasoning_field_attempts", 0)
            if attempts < 10:
                session_storage["reasoning_field_attempts"] = attempts + 1
                for attr in vars(delta):
                    if attr.startswith("reasoning"):
                        val = trim_to_none(getattr(delta, attr, None))
                        if val is not None:
                            session_storage["reasoning_field"] = attr
                            return val

        return None

    def _reconstruct_chat_completion(self, message, chunk, cfg, session_storage=None):

        # -- Id ---
        validate_and_set_unique_field(message=message, name="id", value=chunk.id)

        if not chunk.choices:
            return False

        if len(chunk.choices) != 1:
            return False

        choice = chunk.choices[0]

        if not choice.delta:
            raise ResponseValidationError("Got no delta in a chunk choice")
        delta = choice.delta

        self._check_unknown_delta_unknown_attributes(delta=delta)

        # ---- role ----
        validate_and_set_unique_field(message=message, name="role", value=delta.role)

        content_token = trim_to_none(delta.content) if hasattr(delta, "content") else None
        reasoning_content_token = self._resolve_reasoning_token(delta, content_token, cfg, session_storage)
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
        if cfg.get("use_finish_reason", True):
            validate_and_set_unique_field(message=message, name="finish_reason", value=choice.finish_reason)
        else:
            if choice.finish_reason:
                message["finish_reason"] = choice.finish_reason

        return True

    def stream_chat(self, messages, cfg, tool_registry, time_limit_seconds=None, start_time=None, session_storage=None):

        # Initialise the OpenAI client with the provided base URL and API key.
        ssl_verify = cfg.get("ssl_verify", True)
        client = OpenAI(
            base_url=cfg["llm_url"].rstrip("/"),
            api_key=cfg["api_key"],
            http_client=httpx.Client(verify=ssl_verify),
        )

        # Initialize reconstructed message
        message = {
            "id": None,
            "role": None,
            "content": "",
            "reasoning_content": "",
            "tool_calls": [],
            "function_call": None,
            "finish_reason": None,
            "tool_call_token": False,
            "error_message": None,
            "timed_out": False,
        }

        # Request a streaming response using the new SDK syntax.
        openai_tools = tool_registry.get_openai_tools()
        extra = {"tools": openai_tools} if openai_tools else {}
        if "reasoning_effort" in cfg:
            extra["reasoning_effort"] = cfg.get("reasoning_effort")
        if "temperature" in cfg:
            extra["temperature"] = cfg.get("temperature")
        if "top_p" in cfg:
            extra["top_p"] = cfg.get("top_p")
        if "max_completion_tokens" in cfg:
            extra["max_tokens"] = cfg.get("max_completion_tokens")
            extra["max_completion_tokens"] = cfg.get("max_completion_tokens")
        if "extra_headers" in cfg:
            extra["extra_headers"] = cfg.get("extra_headers")
        if "extra_query" in cfg:
            extra["extra_query"] = cfg.get("extra_query")
        if "extra_body" in cfg:
            extra["extra_body"] = cfg.get("extra_body")
        response = client.chat.completions.create(
            model=cfg.get("model"),
            messages=messages,
            stream=True,
            n=1,
            **extra
        )

        output = LLMResponseOutput(cfg)

        for chunk in response:
            if chunk.id is None:
                message["error_message"] = getattr(chunk, "error_message", None)
                return message
            if not self._reconstruct_chat_completion(message=message, chunk=chunk, cfg=cfg, session_storage=session_storage):
                continue
            output.onLLMMessage(message)

            if time_limit_seconds is not None and start_time is not None:
                if time.time() - start_time >= time_limit_seconds:
                    message["timed_out"] = True
                    try:
                        response.close()
                    except Exception:
                        pass
                    break

        output.onLLMMessage(None)

        return message
