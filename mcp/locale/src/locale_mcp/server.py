import json
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from locale_mcp import get_locale, pronunciation_profile, vocabulary_overrides

server = Server("locale")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_locale",
            description="Get locale information and dialect overrides",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {"type": "string", "description": "Locale code (e.g. 'es_MX', 'fr_CA')"},
                    "language": {"type": "string", "description": "Language code"},
                },
                "required": ["locale", "language"],
            },
        ),
        Tool(
            name="vocabulary_overrides",
            description="Get regional vocabulary substitutions for given words",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {"type": "string", "description": "Locale code"},
                    "language": {"type": "string", "description": "Language code"},
                    "words": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of words to check",
                    },
                },
                "required": ["locale", "language"],
            },
        ),
        Tool(
            name="pronunciation_profile",
            description="Get pronunciation characteristics for a locale",
            inputSchema={
                "type": "object",
                "properties": {
                    "locale": {"type": "string", "description": "Locale code"},
                    "language": {"type": "string", "description": "Language code"},
                },
                "required": ["locale", "language"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result: Any
    match name:
        case "get_locale":
            result = get_locale(**arguments)
        case "vocabulary_overrides":
            result = vocabulary_overrides(**arguments)
        case "pronunciation_profile":
            result = pronunciation_profile(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="locale",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
