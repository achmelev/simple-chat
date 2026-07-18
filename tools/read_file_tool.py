import os
from typing import Dict, Any
from tools.base import Tool


class ReadFileTool(Tool):

    def name(self) -> str:
        return "read_file"

    def description(self) -> str:
        return "Reads a file and returns its text content."

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["path"]
        }

    def short_format_call(self, arguments) -> str:
        return f"Reading file {arguments.get('path', '?')}"

    def execute(self, arguments: Dict[str, Any]) -> str:
        path = arguments.get("path")

        if not path:
            return "ERROR: 'path' argument is required"
        if not os.path.isfile(path):
            return f"ERROR: file not found: {path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"ERROR: {e}"
