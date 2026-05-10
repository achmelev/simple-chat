from typing import List
from commands.base import Command


class ResetCommand(Command):

    def __init__(self, conversation: list, tool_registry, system_prompt: str):
        self._conversation = conversation
        self._tool_registry = tool_registry
        self._system_prompt = system_prompt

    def name(self) -> str:
        return "reset"

    def short_description(self) -> str:
        return "Reset the conversation and reinitialize all tools"

    def description(self) -> str:
        return "Clears the conversation history and reinitializes all tools, starting a fresh session."

    def execute(self, arguments: List[str]) -> str:
        self._conversation.clear()
        self._conversation.append({"role": "system", "content": self._system_prompt})
        self._tool_registry.reset()
        return "Conversation reset."
