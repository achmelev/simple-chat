import subprocess
import tempfile
import sys
import json
import os
import shutil
from typing import Dict, Any, List
from tools.base import Tool


class PythonExecTool(Tool):

    def __init__(self):
        self.workdir = None
        self.venv_path = None
        self.python_exec = None

    def name(self) -> str:
        return "execute_python"

    def description(self) -> str:
        return (
            "Executes Python code in an isolated environment. "
            "Supports installing external libraries via 'libs'."
        )

    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "libs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of Python packages to install (e.g. ['numpy', 'pandas'])"
                }
            },
            "required": []
        }

    # 🔧 Setup environment
    def set_up(self) -> str:
        self.workdir = tempfile.mkdtemp(dir=".", prefix="pyexec_")

        self.venv_path = os.path.join(self.workdir, "venv")

        # Create venv
        subprocess.run([sys.executable, "-m", "venv", self.venv_path], check=True)

        # Determine python path inside venv
        if os.name == "nt":
            self.python_exec = os.path.join(self.venv_path, "Scripts", "python.exe")
        else:
            self.python_exec = os.path.join(self.venv_path, "bin", "python")

        # Upgrade pip
        subprocess.run(
            [self.python_exec, "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("DONE")
        return f"PythonExecTool initialized in {self.workdir}"

    # 🧹 Cleanup (optional)
    def shut_down(self) -> str:
        if self.workdir and os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)
        return "PythonExecTool cleaned up"

    def install_libs(self, libs: List[str]) -> str:
        try:
            result = subprocess.run(
                [self.python_exec, "-m", "pip", "install"] + libs,
                capture_output=True,
                text=True
            )
            return json.dumps({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }, indent=2)
        except Exception as e:
            return f"ERROR installing libs: {e}"

    def execute(self, arguments: Dict[str, Any]) -> str:
        code = arguments.get("code")
        libs = arguments.get("libs", [])

        if not self.python_exec:
            return "ERROR: Tool not initialized. Call set_up() first."

        output = {}

        # 📦 Install libraries if requested
        if libs:
            output["install"] = json.loads(self.install_libs(libs))

            # install-only mode
            if not code:
                return json.dumps(output, indent=2)

        # 🧾 Execute code if provided
        if code:
            try:
                script_path = os.path.join(self.workdir, "script.py")

                with open(script_path, "w") as f:
                    f.write(code)

                result = subprocess.run(
                    [self.python_exec, script_path],
                    cwd=self.workdir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                output["execution"] = {
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                    "returncode": result.returncode
                }

            except subprocess.TimeoutExpired:
                output["execution"] = {"error": "Execution timed out"}

            except Exception as e:
                output["execution"] = {"error": str(e)}

        if not output:
            return "ERROR: Provide 'code' and/or 'libs'"

        return json.dumps(output, indent=2)

    def format_call(self, arguments, result):
        code = arguments.get("code", "")
        libs = arguments.get("libs", [])
        combined = f"# libs: {libs}\n{code}"
        return self.create_tool_call_string(combined, result)