# API Layer

The planned API layer provides a local bridge between user-facing applications,
MCP services, and on-device model runtimes.

## Responsibilities

- Accept requests from desktop and web applications
- Coordinate calls to MCP services
- Manage access to local model inference endpoints
- Return structured responses suitable for tutoring workflows

## Communication Model

Apps will communicate with the API layer for orchestration while the API delegates
educational logic to MCP services and offline model integrations.
