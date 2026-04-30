import os
from tools.command_line_tool import CommandLineTool


class ConfigurableCommandLineTool(CommandLineTool):
    """A command line tool fully configured from data (e.g. YAML config)."""

    def __init__(self, binary: str, description: str, name: str = None):
        self._binary = binary
        self._description = description
        self._name = name or os.path.basename(binary)

    def set_up(self) -> str:
        return f"{self._name} ({self._binary}) initialized"

    def shut_down(self) -> str:
        return f"{self._name} shut down"

    def binary_path(self) -> str:
        return self._binary

    def description(self) -> str:
        return self._description

    def name(self) -> str:
        return self._name
