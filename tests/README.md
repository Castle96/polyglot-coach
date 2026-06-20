# Testing Strategy

Polyglot Coach uses `pytest` for Python MCP services.
Integration tests should cover interactions between applications, MCP services, and local model adapters.

## Running Tests

Run the full Python test suite from the repository root with:

```bash
pytest
```

JavaScript and TypeScript tests should be added alongside their respective apps as those components are implemented.
