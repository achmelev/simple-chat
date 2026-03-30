from typing import List, Dict
from .base import Tool

class ToolRegistry:
    def __init__(self, tools: List[Tool]):
        self.tools = {tool.name(): tool for tool in tools}

    def get_openai_tools(self):
        return [tool.to_openai_tool() for tool in self.tools.values()]

    def execute(self, name: str, arguments: Dict):
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name].execute(arguments)
    
    def format_call(self, name: str, arguments: Dict, result: str):
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name].format_call(arguments=arguments, result=result)