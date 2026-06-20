import json
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from grammar import explain_rule, generate_exercise, grade_exercise, lookup_rule

server = Server("grammar")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="lookup_rule",
            description="Look up a grammar rule by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Grammar rule identifier"},
                    "language": {"type": "string", "description": "Language code"},
                },
                "required": ["rule_id", "language"],
            },
        ),
        Tool(
            name="explain_rule",
            description="Get explanations for grammar rules by category and level",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Language code"},
                    "category": {"type": "string", "description": "Grammar category (e.g. 'verbs', 'nouns')"},
                    "level": {"type": "string", "description": "CEFR level"},
                },
                "required": ["language", "category", "level"],
            },
        ),
        Tool(
            name="generate_exercise",
            description="Generate practice exercises for a grammar rule",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Language code"},
                    "rule_id": {"type": "string", "description": "Grammar rule identifier"},
                    "count": {"type": "integer", "description": "Number of exercises (default 3)"},
                },
                "required": ["language", "rule_id"],
            },
        ),
        Tool(
            name="grade_exercise",
            description="Evaluate a learner's answer to a grammar exercise",
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_id": {"type": "string", "description": "Grammar rule identifier"},
                    "language": {"type": "string", "description": "Language code"},
                    "user_answer": {"type": "string", "description": "The learner's answer"},
                },
                "required": ["rule_id", "language", "user_answer"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result: Any
    match name:
        case "lookup_rule":
            result = lookup_rule(**arguments)
        case "explain_rule":
            result = explain_rule(**arguments)
        case "generate_exercise":
            result = generate_exercise(**arguments)
        case "grade_exercise":
            result = grade_exercise(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="grammar",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
