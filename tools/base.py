from abc import ABC, abstractmethod
from typing import Dict, Any
import json

class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (used by LLM)"""
        pass

    @abstractmethod
    def description(self) -> str:
        """Human-readable description"""
        pass

    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for arguments"""
        pass

    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str:
        """Run the tool locally"""
        pass

    def pretty_xml_simple(self, xml_string: str) -> str:
        indent = 0
        indent_str = "    "
        result = []

        for line in xml_string.splitlines():
            if not line:
                continue

            # If it's a closing tag, decrease indent first
            if line.startswith("</"):
                indent -= 1

            result.append(f"{indent_str * indent}{line}")

            # If it's an opening tag (but not self-closing or inline), increase indent
            if line.startswith("<") and not line.startswith("</") and not line.endswith("/>"):
                # avoid increasing for tags like <tag>content</tag>
                if not ("</" in line):
                    indent += 1

        return "\n".join(result)
    
    def create_tool_call_string(self,input, output):
        return self.pretty_xml_simple(f"<toolcall>\n<input>\n{input}\n</input>\n<output>\n{output}\n</output>\n</toolcall>")

    def format_call(self, arguments, result):
        input=json.dumps(arguments, indent=4)
        return self.create_tool_call_string(input, result)
        

    def to_openai_tool(self) -> Dict[str, Any]:
        """Convert to OpenAI tool format"""
        return {
            "type": "function",
            "function": {
                "name": self.name(),
                "description": self.description(),
                "parameters": self.parameters(),
            }
        }
   