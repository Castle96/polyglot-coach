import json
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from review import get_due_words, record_review, schedule_review

server = Server("review")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_due_words",
            description="Get words due for review (spaced repetition)",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "limit": {"type": "integer", "description": "Max words (default 20)"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="schedule_review",
            description="Schedule a word for spaced repetition review",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "word": {"type": "string", "description": "Word to review"},
                    "language": {"type": "string", "description": "Language code"},
                },
                "required": ["profile_id", "word", "language"],
            },
        ),
        Tool(
            name="record_review",
            description="Record a review result and update the schedule",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer", "description": "Review item ID"},
                    "quality": {
                        "type": "integer",
                        "description": "Recall quality 0-5 (0=complete blackout, 5=perfect)",
                    },
                },
                "required": ["item_id", "quality"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result: Any
    match name:
        case "get_due_words":
            result = get_due_words(**arguments)
        case "schedule_review":
            result = schedule_review(**arguments)
        case "record_review":
            result = record_review(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="review",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
