import os
from typing import Dict, Any
from tools.base import Tool


class WriteFileTool(Tool):

    def __init__(self, target_cfg=None):
        newline_setting = (target_cfg or {}).get("newline", "auto")
        if newline_setting == "windows":
            self._newline = "\r\n"
        elif newline_setting == "unix":
            self._newline = "\n"
        else:
            self._newline = None  # platform default

    def name(self) -> str:
        return "write_file"

    def description(self) -> str:
        return "Writes text to a file, creating it if it does not exist and overwriting it if it does."

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "text": {
                    "type": "string",
                    "description": "Text content to write to the file. Pass characters literally — do NOT escape them in some way (e.g. use < and >, not &lt; and &gt;)."
                }
            },
            "required": ["path", "text"]
        }

    def short_format_call(self, arguments, result) -> str:
        return f"Writing file {arguments.get('path', '?')}"

    def execute(self, arguments: Dict[str, Any]) -> str:
        path = arguments.get("path")
        text = arguments.get("text")

        if not path:
            return "ERROR: 'path' argument is required"
        if text is None:
            return "ERROR: 'text' argument is required"

        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline=self._newline) as f:
                f.write(text)
            return f"OK: wrote {len(text)} characters to {path}"
        except Exception as e:
            return f"ERROR: {e}"
