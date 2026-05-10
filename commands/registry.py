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

    def add(self, command: Command) -> None:
        self._commands[command.name()] = command

    def all_commands(self) -> List[Command]:
        return list(self._commands.values())

    def find(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def execute(self, command_input: CommandInput) -> Optional[str]:
        """Execute a parsed command. Returns a message to display, or None."""
        if command_input.name not in self._commands:
            return f"Unknown command: /{command_input.name}"
        return self._commands[command_input.name].execute(command_input.args)
