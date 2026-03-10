# ksef2-mcp

`ksef2-mcp` is a thin MCP adapter for hosted KSeF automation built on top of the `ksef2` SDK.

## Architecture goals

- Keep MCP handlers thin and task-oriented.
- Centralize workflow logic in reusable application services.
- Use stable product DTOs at the adapter boundary.
- Resolve request context (user, workspace, capabilities, correlation id) before service execution.

## Project layout

- `src/ksef2_mcp/server.py` - MCP tool registration and adapter glue.
- `src/ksef2_mcp/application.py` - service layer workflows reused by all adapters.
- `src/ksef2_mcp/contracts.py` - request context and input DTO contracts.
- `src/ksef2_mcp/domain.py` - stable domain response models shared by adapters.
- `src/ksef2_mcp/providers.py` - provider interfaces and in-memory defaults.

## Development

```bash
uv sync --dev
uv run pytest
uv run basedpyright
```

## Run MCP server

```bash
uv run python -m ksef2_mcp.main
```
