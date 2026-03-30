import subprocess
import tempfile
import sys
import json
from typing import Dict, Any
from tools.base import Tool


class PythonExecTool(Tool):

    def name(self) -> str:
        return "execute_python"

    def description(self) -> str:
        return (
            "Executes a Python script and returns stdout/stderr. "
            "Use this for calculations, data processing, or running Python code."
            "Note: your environment doesn't have any external libraries, so use only python-own"
        )

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute"
                }
            },
            "required": ["code"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        code = arguments.get("code", "")

        if not code:
            return "ERROR: 'code' argument is required"

        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            # Run Python in subprocess
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=60  # ⏱️ important safeguard
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            output = {
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode
            }

            return json.dumps(output, indent=2)

        except subprocess.TimeoutExpired:
            return "ERROR: Execution timed out"

        except Exception as e:
            return f"ERROR: {e}"

    def format_call(self, arguments, result):
        code = arguments.get("code", "")
        return self.create_tool_call_string(code, result)