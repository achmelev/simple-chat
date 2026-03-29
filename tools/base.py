from abc import ABC, abstractmethod
from typing import Dict, Any

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
   