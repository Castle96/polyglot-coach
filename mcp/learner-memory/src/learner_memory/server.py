import json
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import ServerCapabilities, TextContent, Tool

from learner_memory import delete_session, export_anki_deck, export_vocabulary_csv, export_vocabulary_json, get_profile, get_progress, list_sessions, load_session, record_mistake, save_session, update_profile

server = Server("learner-memory")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_profile",
            description="Retrieve a learner's profile by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Learner's display name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="update_profile",
            description="Update a learner's profile fields",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "name": {"type": "string", "description": "New display name"},
                    "native_language": {"type": "string", "description": "Native language code (e.g. 'en')"},
                    "target_language": {"type": "string", "description": "Target language code (e.g. 'es')"},
                    "locale": {"type": "string", "description": "Locale code (e.g. 'es_MX')"},
                    "proficiency_level": {"type": "string", "description": "CEFR level (A1-C1)"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="record_mistake",
            description="Record a learner mistake for analysis and review",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "category": {"type": "string", "description": "Mistake category (e.g. 'grammar', 'vocabulary', 'pronunciation')"},
                    "user_input": {"type": "string", "description": "What the learner said or wrote"},
                    "correction": {"type": "string", "description": "The correct form"},
                    "explanation": {"type": "string", "description": "Explanation of the mistake"},
                    "context": {"type": "string", "description": "Conversational context"},
                },
                "required": ["profile_id", "category", "user_input", "correction"],
            },
        ),
        Tool(
            name="get_progress",
            description="Retrieve progress records for a learner",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "event_type": {"type": "string", "description": "Filter by event type (optional)"},
                    "limit": {"type": "integer", "description": "Max records to return (default 50)"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="save_session",
            description="Save a learner's conversation session state",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "title": {"type": "string", "description": "Session title"},
                    "language": {"type": "string", "description": "Language code (e.g. 'es', 'ja')"},
                    "state": {"type": "string", "description": "JSON string of conversation state"},
                    "session_id": {"type": "integer", "description": "Existing session ID to update (optional)"},
                },
                "required": ["profile_id", "title", "language", "state"],
            },
        ),
        Tool(
            name="list_sessions",
            description="List saved sessions for a learner, with optional fuzzy search",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "language": {"type": "string", "description": "Filter by language (optional)"},
                    "query": {"type": "string", "description": "Fuzzy search query for session titles"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="load_session",
            description="Load a saved session by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Session ID to load"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="delete_session",
            description="Delete a saved session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Session ID to delete"},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="export_vocabulary_json",
            description="Export vocabulary as JSON",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="export_vocabulary_csv",
            description="Export vocabulary as CSV",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                },
                "required": ["profile_id"],
            },
        ),
        Tool(
            name="export_anki_deck",
            description="Export vocabulary as Anki deck (tab-separated)",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {"type": "integer", "description": "Profile ID"},
                    "language": {"type": "string", "description": "Filter by language (optional)"},
                },
                "required": ["profile_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    result: Any
    match name:
        case "get_profile":
            result = get_profile(arguments["name"])
        case "update_profile":
            result = update_profile(**arguments)
        case "record_mistake":
            result = record_mistake(**arguments)
        case "get_progress":
            result = get_progress(**arguments)
        case "save_session":
            result = save_session(**arguments)
        case "list_sessions":
            result = list_sessions(**arguments)
        case "load_session":
            result = load_session(**arguments)
        case "delete_session":
            result = delete_session(**arguments)
        case "export_vocabulary_json":
            result = export_vocabulary_json(**arguments)
        case "export_vocabulary_csv":
            result = export_vocabulary_csv(**arguments)
        case "export_anki_deck":
            result = export_anki_deck(**arguments)
        case _:
            raise ValueError(f"Unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="learner-memory",
                server_version="0.1.0",
                capabilities=ServerCapabilities(),
            ),
        )
