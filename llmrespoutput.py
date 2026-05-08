class LLMResponseOutput:
    _SPINNER = ['|', '/', '-', '\\']

    def __init__(self, cfg=None):
        self._in_reasoning = False
        self._responsetrace = (cfg or {}).get("responsetrace", False)
        self._spinner_index = 0

    def _advance_spinner(self):
        self._spinner_index = (self._spinner_index + 1) % len(self._SPINNER)
        print(f"\rThinking {self._SPINNER[self._spinner_index]}", end="", flush=True)

    def _clear_spinner(self):
        print("\r" + " " * 12 + "\r", end="", flush=True)

    def onLLMMessage(self, message):
        """Handle one LLM message state update. Pass None to signal end of stream."""
        if message is None:
            if self._in_reasoning:
                if self._responsetrace:
                    print("\n</THINKING>", flush=True)
                else:
                    self._clear_spinner()
            print()
            return

        if self._in_reasoning:
            if message["reasoning_content_token"]:
                if self._responsetrace:
                    print(message["reasoning_content_token"], end="", flush=True)
                else:
                    self._advance_spinner()
            if message["content_token"]:
                if self._responsetrace:
                    print("\n</THINKING>", flush=True)
                else:
                    self._clear_spinner()
                self._in_reasoning = False
                print(message["content_token"], end="", flush=True)
        else:
            if message["content_token"]:
                print(message["content_token"], end="", flush=True)
            if message["reasoning_content_token"]:
                self._in_reasoning = True
                if self._responsetrace:
                    print("<THINKING>", flush=True)
                    print(message["reasoning_content_token"], end="", flush=True)
                else:
                    print(f"Thinking {self._SPINNER[self._spinner_index]}", end="", flush=True)
