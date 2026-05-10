from typing import List, Optional
from commands.base import Command


class HelpCommand(Command):

    def __init__(self, registry):
        self._registry = registry

    def name(self) -> str:
        return "help"

    def short_description(self) -> str:
        return "List available commands or show help for a specific command"

    def description(self) -> str:
        return (
            "Usage: /help [command]\n"
            "  Without arguments: lists all available commands with short descriptions.\n"
            "  With a command name: prints the full description of that command."
        )

    def execute(self, arguments: List[str]) -> Optional[str]:
        if not arguments:
            lines = [f"  /{cmd.name():<14}{cmd.short_description()}" for cmd in self._registry.all_commands()]
            return "\n".join(lines)
        cmd_name = arguments[0].lstrip("/")
        cmd = self._registry.find(cmd_name)
        if cmd is None:
            return f"Unknown command: /{cmd_name}"
        return cmd.description()
