import json

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from conversation import evaluate_response, generate_scenario, suggest_followup

server = Server("conversation")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_scenario",
            description="Generate a roleplay conversation scenario",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Language code"},
                    "level": {"type": "string", "description": "CEFR level"},
                    "topic": {"type": "string", "description": "Optional topic filter"},
                },
                "required": ["language", "level"],
            },
        ),
        Tool(
            name="evaluate_response",
            description="Evaluate a learner's conversational turn",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {"type": "integer", "description": "Scenario ID"},
                    "user_turn": {"type": "string", "description": "The learner's response text"},
                },
                "required": ["scenario_id", "user_turn"],
            },
        ),
        Tool(
            name="suggest_followup",
            description="Suggest a follow-up turn in a conversation",
            inputSchema={
                "type": "object",
                "properties": {
                    "scenario_id": {"type": "integer", "description": "Scenario ID"},
                    "conversation_history": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Previous turns in the conversation",
                    },
                },
                "required": ["scenario_id", "conversation_history"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    match name:
        case "generate_scenario":
            result = generate_scenario(**arguments)
        case "evaluate_response":
            result = evaluate_response(**arguments)
        case "suggest_followup":
            result = suggest_followup(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="conversation",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
