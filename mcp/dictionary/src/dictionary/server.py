import json
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from dictionary import get_conjugation, get_examples, lookup_word

server = Server("dictionary")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="lookup_word",
            description="Look up a word's translation and metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "The word to look up"},
                    "language": {"type": "string", "description": "Language code"},
                    "profile_id": {"type": "integer", "description": "Optional profile ID for personalized results"},
                },
                "required": ["word", "language"],
            },
        ),
        Tool(
            name="get_examples",
            description="Get example sentences for a word",
            inputSchema={
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "The word"},
                    "language": {"type": "string", "description": "Language code"},
                    "limit": {"type": "integer", "description": "Max examples (default 5)"},
                },
                "required": ["word", "language"],
            },
        ),
        Tool(
            name="get_conjugation",
            description="Get conjugation information for a verb",
            inputSchema={
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "The verb to conjugate"},
                    "language": {"type": "string", "description": "Language code"},
                },
                "required": ["word", "language"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result: Any
    match name:
        case "lookup_word":
            result = lookup_word(**arguments)
        case "get_examples":
            result = get_examples(**arguments)
        case "get_conjugation":
            result = get_conjugation(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dictionary",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
