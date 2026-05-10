import sys
from typing import List
from commands.base import Command


class QuitCommand(Command):

    def __init__(self, tool_registry):
        self._tool_registry = tool_registry

    def name(self) -> str:
        return "quit"

    def short_description(self) -> str:
        return "Exit the chat session"

    def description(self) -> str:
        return "Shuts down all tools and exits the chat session."

    def execute(self, arguments: List[str]) -> str:
        self._tool_registry.shut_down()
        print("Exiting chat.")
        sys.exit(0)
