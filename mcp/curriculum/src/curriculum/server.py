import json
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from curriculum import get_lesson, get_scenario, get_topic

server = Server("curriculum")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_lesson",
            description="Retrieve scenarios for a given language and CEFR level",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Language code (e.g. 'es', 'fr')"},
                    "level": {"type": "string", "description": "CEFR level (A1-C1)"},
                },
                "required": ["language", "level"],
            },
        ),
        Tool(
            name="get_topic",
            description="List available topics for a language",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Language code"},
                    "level": {"type": "string", "description": "Optional CEFR level filter"},
                },
                "required": ["language"],
            },
        ),
        Tool(
            name="get_scenario",
            description="Get full details for a specific scenario",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {"type": "integer", "description": "Scenario ID"},
                },
                "required": ["scenario_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result: Any
    match name:
        case "get_lesson":
            result = get_lesson(**arguments)
        case "get_topic":
            result = get_topic(**arguments)
        case "get_scenario":
            result = get_scenario(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="curriculum",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
