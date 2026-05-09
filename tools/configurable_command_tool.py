import os
from tools.command_line_tool import CommandLineTool


class ConfigurableCommandLineTool(CommandLineTool):
    """A command line tool fully configured from data (e.g. YAML config)."""

    def __init__(self, binary: str, description: str, name: str = None):
        self._binary = binary
        self._description = description
        self._name = name or os.path.basename(binary)

    def binary_path(self) -> str:
        return self._binary

    def description(self) -> str:
        return self._description

    def name(self) -> str:
        return self._name

    def short_format_call(self, arguments, result) -> str:
        binary = os.path.basename(self._binary)
        args = arguments.get("arguments", [])
        working_dir = arguments.get("working_directory", ".")

        if args:
            args_str = " ".join(str(a) for a in args)
            cmd = f'"{binary} {args_str}"'
        else:
            cmd = binary

        cwd = os.getcwd()
        abs_working_dir = os.path.abspath(working_dir)

        if abs_working_dir == cwd:
            return f"Executing {cmd}"

        rel = os.path.relpath(abs_working_dir, cwd)
        display_dir = rel if not rel.startswith("..") else working_dir

        return f"Executing {cmd} in {display_dir}"
