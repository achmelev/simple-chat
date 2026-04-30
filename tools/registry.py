from typing import List, Dict
from .base import Tool
from .configurable_command_tool import ConfigurableCommandLineTool

class ToolRegistry:
    def __init__(self, all_tools, tool_names, command_tool_configs=None):
        if command_tool_configs:
            for cfg in command_tool_configs:
                all_tools = list(all_tools) + [ConfigurableCommandLineTool(
                    binary=cfg["binary"],
                    description=cfg["description"],
                    name=cfg.get("name")
                )]
        tools_to_install = [];
        if tool_names:
            for tool in all_tools:
              name = tool.name()
              if name in tool_names:
                try:
                    result = tool.set_up()
                    if result is not None:
                        print(result)
                    tools_to_install.append(tool)
                except Exception as e:
                    print(f"Tool setup failed: {tool.name()} -> {e}")
        self.tools = {tool.name(): tool for tool in tools_to_install}
        if (len(self.tools) == 0):
            print("NO TOOLS INSTALLED")
        else:
            print("INSTALLED TOOLS: ", end="")
            for tool_name in self.tools:
                print(tool_name+" ")
            print() 


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
    
    def shut_down(self):
        for tool in self.tools.values():
            try:
                result = tool.shut_down()
                if result is not None:
                    print(result)
            except Exception as e:
                print(f"Tool shutdown failed: {tool.name()} -> {e}")

    def reset(self):
        for tool in self.tools.values():
            try:
                result = tool.shut_down()
                if result is not None:
                    print(result)
            except Exception as e:
                print(f"Tool shutdown failed: {tool.name()} -> {e}")  
            try:
                result = tool.set_up()
                if result is not None:
                    print(result)
            except Exception as e:
                print(f"Tool setup failed: {tool.name()} -> {e}")

