import os
from typing import Dict, Any
from tools.base import Tool


class EditFileTool(Tool):

    def name(self) -> str:
        return "editfile"

    def description(self) -> str:
        return (
            "Edits a file by replacing an exact string with a new string. "
            "Use this for targeted edits: replacing, inserting, or deleting lines. "
            "For insertions or deletions, include enough surrounding lines in "
            "old_string to make the match unique. "
            "Pass all strings literally — do NOT escape characters like < and >."
        )

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": (
                        "The exact text to find and replace. "
                        "Must match the file content character-for-character, including indentation and line endings. "
                        "Include enough surrounding context lines to make the match unique in the file."
                    )
                },
                "new_string": {
                    "type": "string",
                    "description": (
                        "The text to replace old_string with. "
                        "To delete lines, omit them here while keeping any context lines from old_string. "
                        "To insert lines, include the anchor lines from old_string plus the new lines."
                    )
                }
            },
            "required": ["path", "old_string", "new_string"]
        }

    def short_format_call(self, arguments, result) -> str:
        return f"Editing file {arguments.get('path', '?')}"

    def execute(self, arguments: Dict[str, Any]) -> str:
        path = arguments.get("path")
        old_string = arguments.get("old_string")
        new_string = arguments.get("new_string")

        if not path:
            return "ERROR: 'path' argument is required"
        if old_string is None:
            return "ERROR: 'old_string' argument is required"
        if new_string is None:
            return "ERROR: 'new_string' argument is required"
        if not os.path.isfile(path):
            return f"ERROR: file not found: {path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"ERROR: could not read file: {e}"

        count = content.count(old_string)
        if count == 0:
            return "ERROR: old_string not found in file — check indentation and whitespace"
        if count > 1:
            return f"ERROR: old_string matches {count} times — add more surrounding context to make it unique"

        new_content = content.replace(old_string, new_string, 1)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            return f"ERROR: could not write file: {e}"

        return f"OK: edit applied to {path}"
