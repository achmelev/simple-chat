import math
import time
import httpx

from llm.base import LLMClient
from llm.openai_client import trim_to_none, validate_and_set_unique_field
from llmrespoutput import LLMResponseOutput

try:
    from openai import OpenAI
except ImportError as e:
    raise ImportError(
        "Required package 'openai' is not installed. Install with 'pip install -r requirements.txt'."
    ) from e


class OpenAILegacyCompletionsClient(LLMClient):
    """LLMClient implementation for the OpenAI legacy (text-in/text-out) Completions API.

    Since the Completions API has no notion of chat roles or tool calls, the message
    history is flattened into a single prompt string (message contents concatenated
    in order) and the response always comes back as a plain assistant message with
    no reasoning content and no tool calls.
    """

    def _build_prompt(self, messages):
        return "\n".join(msg.get("content") or "" for msg in messages)

    def _collect_logprobs(self, logprobs, collected):
        if not logprobs:
            return
        tokens = logprobs.tokens or []
        token_logprobs = logprobs.token_logprobs or []
        top_logprobs = logprobs.top_logprobs or []
        for i, token in enumerate(tokens):
            logprob = token_logprobs[i] if i < len(token_logprobs) else None
            alternatives = top_logprobs[i] if i < len(top_logprobs) else None
            collected.append((token, logprob, alternatives))

    def _print_logprobs(self, collected):
        if not collected:
            return
        print("\n--- Token probabilities ---")
        for token, logprob, alternatives in collected:
            prob_str = f"{math.exp(logprob):.4f}" if logprob is not None else "n/a"
            line = f"[prob] {token!r}: {prob_str}"
            if alternatives:
                ranked = sorted(alternatives.items(), key=lambda kv: kv[1], reverse=True)
                alt_str = ", ".join(
                    f"{'*' if alt_token == token else ''}{alt_token!r}: {math.exp(alt_logprob):.4f}"
                    for alt_token, alt_logprob in ranked
                )
                line += f"  [{alt_str}]"
            print(line)
        print("--- End of token probabilities ---")

    def _reconstruct_completion(self, message, chunk, cfg, collected_logprobs=None):
        validate_and_set_unique_field(message=message, name="id", value=chunk.id)

        if not chunk.choices:
            return False
        if len(chunk.choices) != 1:
            return False
        choice = chunk.choices[0]

        text_token = trim_to_none(choice.text)
        message["content_token"] = text_token
        message["reasoning_content_token"] = None
        message["tool_call_token"] = False

        if text_token:
            message["content"] += text_token

        if collected_logprobs is not None:
            self._collect_logprobs(choice.logprobs, collected_logprobs)

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
            "role": "assistant",
            "content": "",
            "reasoning_content": "",
            "tool_calls": [],
            "function_call": None,
            "finish_reason": None,
            "tool_call_token": False,
            "error_message": None,
            "timed_out": False,
        }

        prompt = self._build_prompt(messages)

        # The Completions API has no "tools" or "reasoning_effort" parameter.
        extra = {}
        if "temperature" in cfg:
            extra["temperature"] = cfg.get("temperature")
        if "top_p" in cfg:
            extra["top_p"] = cfg.get("top_p")
        if "max_completion_tokens" in cfg:
            extra["max_tokens"] = cfg.get("max_completion_tokens")
        if "extra_headers" in cfg:
            extra["extra_headers"] = cfg.get("extra_headers")
        if "extra_query" in cfg:
            extra["extra_query"] = cfg.get("extra_query")
        if "extra_body" in cfg:
            extra["extra_body"] = cfg.get("extra_body")
        if "echo" in cfg:
            extra["echo"] = cfg.get("echo")
        logprobs_n = cfg.get("logprobs")
        if logprobs_n:
            # Backward-compat: `logprobs: true` (old boolean-only config) means "top 1".
            logprobs_n = 1 if isinstance(logprobs_n, bool) else int(logprobs_n)
            extra["logprobs"] = logprobs_n

        response = client.completions.create(
            model=cfg.get("model"),
            prompt=prompt,
            stream=True,
            n=1,
            **extra
        )

        output = LLMResponseOutput(cfg)
        collected_logprobs = [] if logprobs_n else None

        for chunk in response:
            if chunk.id is None:
                message["error_message"] = getattr(chunk, "error_message", None)
                return message
            if not self._reconstruct_completion(message=message, chunk=chunk, cfg=cfg, collected_logprobs=collected_logprobs):
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

        if collected_logprobs is not None:
            self._print_logprobs(collected_logprobs)

        return message
