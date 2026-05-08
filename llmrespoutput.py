_THINKING_PREFIX = "Thinking "
_TOOL_CALL_PREFIX = "Assembling tool call "
_SPINNER_CLEAR_WIDTH = 24


class LLMResponseOutput:
    _SPINNER = ['|', '/', '-', '\\']

    def __init__(self, cfg=None):
        self._in_reasoning = False
        self._in_tool_call = False
        self._content_on_current_line = False
        self._responsetrace = (cfg or {}).get("responsetrace", False)
        self._spinner_index = 0

    def _clear_spinner(self):
        print("\r" + " " * _SPINNER_CLEAR_WIDTH + "\r", end="", flush=True)

    def _show_spinner(self, prefix):
        print(f"\r{prefix}{self._SPINNER[self._spinner_index]}", end="", flush=True)

    def _update_spinner(self, prefix):
        self._spinner_index = (self._spinner_index + 1) % len(self._SPINNER)
        print(f"\r{prefix}{self._SPINNER[self._spinner_index]}", end="", flush=True)

    def _ensure_fresh_line(self):
        """Move to a new line if content was printed without a trailing newline."""
        if self._content_on_current_line:
            print(flush=True)
            self._content_on_current_line = False

    def _enter_spinner(self, prefix):
        self._ensure_fresh_line()
        self._show_spinner(prefix)

    def onLLMMessage(self, message):
        """Handle one LLM message state update. Pass None to signal end of stream."""
        if message is None:
            if self._in_reasoning:
                if self._responsetrace:
                    print("\n</THINKING>", flush=True)
                else:
                    self._clear_spinner()
            elif self._in_tool_call:
                self._clear_spinner()
            print()
            return

        reasoning_token = message["reasoning_content_token"]
        content_token = message["content_token"]
        tool_call_token = message["tool_call_token"]

        if reasoning_token:
            if self._in_tool_call:
                self._clear_spinner()
                self._in_tool_call = False
            if not self._in_reasoning:
                self._in_reasoning = True
                if self._responsetrace:
                    self._ensure_fresh_line()
                    print("<THINKING>", flush=True)
                    print(reasoning_token, end="", flush=True)
                else:
                    self._enter_spinner(_THINKING_PREFIX)
            else:
                if self._responsetrace:
                    print(reasoning_token, end="", flush=True)
                else:
                    self._update_spinner(_THINKING_PREFIX)

        if content_token:
            if self._in_reasoning:
                if self._responsetrace:
                    print("\n</THINKING>", flush=True)
                else:
                    self._clear_spinner()
                self._in_reasoning = False
            elif self._in_tool_call:
                self._clear_spinner()
                self._in_tool_call = False
            print(content_token, end="", flush=True)
            self._content_on_current_line = True

        if not reasoning_token and not content_token and tool_call_token:
            if self._in_reasoning:
                if self._responsetrace:
                    print("\n</THINKING>", flush=True)
                else:
                    self._clear_spinner()
                self._in_reasoning = False
            if not self._in_tool_call:
                self._in_tool_call = True
                self._enter_spinner(_TOOL_CALL_PREFIX)
            else:
                self._update_spinner(_TOOL_CALL_PREFIX)
