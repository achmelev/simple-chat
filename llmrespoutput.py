import datetime

_THINKING_PREFIX = "Thinking "
_TOOL_CALL_PREFIX = "Assembling tool call "


class LLMResponseOutput:
    _SPINNER = ['|', '/', '-', '\\']

    def __init__(self, cfg=None):
        self._state = None  # None | "thinking" | "speaking" | "tooling"
        self._responsetrace = (cfg or {}).get("responsetrace", False)
        self._spinner_index = 0
        self._cursor_at_line_start = True
        self._trace_file = None
        if (cfg or {}).get("llmtrace", False):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self._trace_file = open(f"llmtrace{ts}.txt", "w", encoding="utf-8")

    def _trace(self, msg):
        if self._trace_file:
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")
            self._trace_file.write(f"[{ts}] {msg}\n")
            self._trace_file.flush()

    def _newline(self):
        """Print a newline only if the cursor is not already at the start of a line."""
        if not self._cursor_at_line_start:
            self._trace("NEWLINE printed")
            print(flush=True)
            self._cursor_at_line_start = True
        else:
            self._trace("NEWLINE suppressed")

    def _show_spinner(self, prefix):
        print(f"\r{prefix}{self._SPINNER[self._spinner_index]}", end="", flush=True)
        self._cursor_at_line_start = False

    def _update_spinner(self, prefix):
        self._spinner_index = (self._spinner_index + 1) % len(self._SPINNER)
        print(f"\r{prefix}{self._SPINNER[self._spinner_index]}", end="", flush=True)
        self._cursor_at_line_start = False

    def _leave_state(self):
        """Close the current state with a line break. No-op when state is None."""
        self._trace(f"LEAVE {self._state} | cursor_at_line_start={self._cursor_at_line_start}")
        if self._state == "thinking" and self._responsetrace:
            self._newline()
            print("</THINKING>", flush=True)
            self._cursor_at_line_start = True
        elif self._state is not None:
            self._newline()
        self._state = None

    def _enter_thinking(self):
        self._state = "thinking"
        self._trace(f"ENTER thinking | cursor_at_line_start={self._cursor_at_line_start}")
        if self._responsetrace:
            print("<THINKING>", flush=True)
            self._cursor_at_line_start = True
        else:
            self._show_spinner(_THINKING_PREFIX)

    def _enter_speaking(self):
        self._state = "speaking"
        self._trace(f"ENTER speaking | cursor_at_line_start={self._cursor_at_line_start}")

    def _enter_tooling(self):
        self._state = "tooling"
        self._trace(f"ENTER tooling | cursor_at_line_start={self._cursor_at_line_start}")
        self._show_spinner(_TOOL_CALL_PREFIX)

    def onLLMMessage(self, message):
        """Handle one LLM message state update. Pass None to signal end of stream."""
        if message is None:
            self._trace("END OF STREAM")
            if self._state is not None:
                self._leave_state()
            if self._trace_file:
                self._trace_file.close()
                self._trace_file = None
            return

        reasoning_token = message["reasoning_content_token"]
        content_token = message["content_token"]
        tool_call_token = message["tool_call_token"]

        if reasoning_token:
            just_entered = self._state != "thinking"
            if just_entered:
                self._leave_state()
                self._enter_thinking()
            if self._responsetrace:
                print(reasoning_token, end='', flush=True)
                self._cursor_at_line_start = reasoning_token.endswith('\n')
            elif not just_entered:
                self._update_spinner(_THINKING_PREFIX)

        if content_token:
            if self._state != "speaking":
                self._leave_state()
                self._enter_speaking()
            print(content_token, end='', flush=True)
            self._cursor_at_line_start = content_token.endswith('\n')

        if not reasoning_token and not content_token and tool_call_token:
            just_entered = self._state != "tooling"
            if just_entered:
                self._leave_state()
                self._enter_tooling()
            else:
                self._update_spinner(_TOOL_CALL_PREFIX)
