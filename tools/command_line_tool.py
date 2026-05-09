import subprocess
import json
import os
from abc import abstractmethod
from typing import Dict, Any
from tools.base import Tool


class CommandLineTool(Tool):
    """Base class for tools that run a fixed binary with configurable args and working directory."""

    @abstractmethod
    def binary_path(self) -> str:
        """Absolute or resolvable path to the executable."""
        pass

    def name(self) -> str:
        return os.path.basename(self.binary_path())

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "working_directory": {
                    "type": "string",
                    "description": "Directory in which to run the command"
                },
                "arguments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command-line arguments to pass to the binary"
                }
            },
            "required": ["working_directory", "arguments"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        working_directory = arguments.get("working_directory", ".")
        args = arguments.get("arguments", [])

        try:
            result = subprocess.run(
                [self.binary_path()] + args,
                cwd=working_directory,
                capture_output=True,
                text=True,
                timeout=self._timeout
            )
            output = {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            output = {"error": "Execution timed out"}
        except FileNotFoundError:
            output = {"error": f"Binary not found: {self.binary_path()}"}
        except Exception as e:
            output = {"error": str(e)}

        return json.dumps(output, indent=2)
