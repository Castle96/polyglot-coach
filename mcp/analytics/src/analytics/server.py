import json

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from analytics import get_engagement_overview, get_learning_summary, get_retention_report

server = Server("analytics")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_learning_summary",
            description="Get a summary of the learner's overall progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="get_retention_report",
            description="Get a retention report based on spaced repetition data",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="get_engagement_overview",
            description="Get an overview of learner engagement over the last 30 days",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                },
                "required": ["profile_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    match name:
        case "get_learning_summary":
            result = get_learning_summary(**arguments)
        case "get_retention_report":
            result = get_retention_report(**arguments)
        case "get_engagement_overview":
            result = get_engagement_overview(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="analytics",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
