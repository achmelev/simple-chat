class LLMResponseOutput:
    def __init__(self):
        self._in_reasoning = False

    def onLLMMessage(self, message):
        """Handle one LLM message state update. Pass None to signal end of stream."""
        if message is None:
            if self._in_reasoning:
                print("\n</THINKING>", flush=True)
            print()
            return
        if self._in_reasoning:
            if message["reasoning_content_token"]:
                print(message["reasoning_content_token"], end="", flush=True)
            if message["content_token"]:
                print("\n</THINKING>", flush=True)
                self._in_reasoning = False
                print(message["content_token"], end="", flush=True)
        else:
            if message["content_token"]:
                print(message["content_token"], end="", flush=True)
            if message["reasoning_content_token"]:
                print("<THINKING>", flush=True)
                self._in_reasoning = True
                print(message["reasoning_content_token"], end="", flush=True)
