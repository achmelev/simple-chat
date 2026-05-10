from dataclasses import dataclass, field
from typing import List, Optional
from commands.base import Command


@dataclass
class CommandInput:
    name: str
    args: List[str] = field(default_factory=list)


class CommandRegistry:

    def __init__(self, commands: List[Command]):
        self._commands = {cmd.name(): cmd for cmd in commands}

    def execute(self, command_input: CommandInput) -> Optional[str]:
        """Execute a parsed command. Returns a message to display, or None."""
        if command_input.name not in self._commands:
            return f"Unknown command: /{command_input.name}"
        return self._commands[command_input.name].execute(command_input.args)
