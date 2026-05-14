"""MCP server that exposes SimpleChat tools via the Model Context Protocol.

Uses the Streamable HTTP transport (stateless mode) so tool calls are accepted
without a prior initialize/notifications-initialized handshake.

Usage:
    python mcpsrv.py --config path/to/config.yaml

Reads the same config format as chat.py but only uses:
    tools, command_tools, tool_timeout, target, trace, mcp
"""

import sys
import os
import argparse
import contextlib

try:
    import yaml
except ImportError:
    print("Required package 'PyYAML' is not installed. Install with 'pip install -r requirements.txt'.")
    sys.exit(1)

from tools.python_exec_tool import PythonExecTool
from tools.write_file_tool import WriteFileTool
from tools.edit_file_tool import EditFileTool
from tools.registry import ToolRegistry


def load_config(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_tool_registry(cfg):
    all_tools = [
        PythonExecTool(),
        WriteFileTool(cfg.get("target")),
        EditFileTool(cfg.get("target")),
    ]
    return ToolRegistry(
        all_tools=all_tools,
        tool_names=cfg.get("tools"),
        command_tool_configs=cfg.get("command_tools"),
        tool_timeout=cfg.get("tool_timeout", 300),
    )


def main():
    parser = argparse.ArgumentParser(description="MCP server exposing SimpleChat tools over HTTP")
    parser.add_argument("--config", required=True, help="Path to YAML configuration file")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except Exception as exc:
        print(f"Failed to load config: {exc}")
        sys.exit(1)

    port = cfg.get("mcp", {}).get("http_port", 9090)
    print(f"MCP server port = {port}")

    tool_registry = build_tool_registry(cfg)

    try:
        from mcp.server import Server
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        import mcp.types as types
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn
    except ImportError as e:
        print(f"Required packages missing: {e}. Install with 'pip install -r requirements.txt'.")
        sys.exit(1)

    server = Server("simplechat-tools")

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(
                name=tool.name(),
                description=tool.description(),
                inputSchema=tool.parameters(),
            )
            for tool in tool_registry.tools.values()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        trace_toolcall = cfg.get("trace", {}).get("toolcall", False)
        args = arguments or {}
        if trace_toolcall:
            print(tool_registry.short_format_call(name, args))
        result = tool_registry.execute(name, args)
        if trace_toolcall:
            try:
                print(f"\n{tool_registry.format_call(name, args, result)}\n")
            except Exception:
                pass
        return [types.TextContent(type="text", text=result)]

    session_manager = StreamableHTTPSessionManager(app=server, stateless=True)

    @contextlib.asynccontextmanager
    async def lifespan(app):
        async with session_manager.run():
            yield

    class _MCPApp:
        async def __call__(self, scope, receive, send):
            await session_manager.handle_request(scope, receive, send)

    starlette_app = Starlette(
        lifespan=lifespan,
        routes=[
            Route("/mcp", endpoint=_MCPApp()),
        ],
    )

    print(f"Starting MCP server on http://0.0.0.0:{port}/mcp")
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
