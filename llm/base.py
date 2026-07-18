from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ResponseValidationError(Exception):
    pass


class LLMClient(ABC):

    @abstractmethod
    def stream_chat(self, messages: List[Dict], cfg: Dict[str, Any], tool_registry,
                     time_limit_seconds: Optional[float] = None, start_time: Optional[float] = None,
                     session_storage: Optional[Dict] = None) -> Dict[str, Any]:
        """Stream a chat completion and return the reconstructed message dict.

        The returned dict must contain at least: id, role, content, reasoning_content,
        tool_calls, function_call, finish_reason, tool_call_token, error_message, timed_out.
        """
        pass
